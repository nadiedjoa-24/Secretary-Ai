"""
speech_to_speech_appointment_checker.py — v10 stable

• Agenda hebdo (lundi-dimanche) depuis availability.xlsx
• Whisper FR → détection robuste jour + heure (fuzzy + nombres écrits)
• « au revoir » (ou quit / exit / stop) arrête la boucle où qu’il soit
"""

from __future__ import annotations
import os, sys, locale, shutil, subprocess, tempfile, time, re, difflib, unicodedata
from datetime import datetime, timedelta, date, time as dtime

import numpy as np
import pandas as pd
import speech_recognition as sr
import whisper
from gtts import gTTS

# ---------- CONFIG -----------------------------------------------------------
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
EXCEL_PATH  = os.path.join(SCRIPT_DIR, "availability.xlsx")
FFMPEG_DIR  = os.getenv("FFMPEG_DIR", r"C:\ffmpeg\bin")           # ajuste si besoin
LANGUAGE    = "fr"
TOL_MINUTES = 15                                                  # tolérance horaire

# ---------- Locale FR --------------------------------------------------------
for loc in ("fr_FR.UTF-8", "French_France"):
    try:
        locale.setlocale(locale.LC_TIME, loc)
        break
    except locale.Error:
        continue

# ---------- ffmpeg / ffplay --------------------------------------------------
FFMPEG_EXE = os.path.join(FFMPEG_DIR, "ffmpeg.exe") if FFMPEG_DIR else None
if not (FFMPEG_EXE and os.path.isfile(FFMPEG_EXE)):
    FFMPEG_EXE = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
if not FFMPEG_EXE:
    raise RuntimeError("ffmpeg.exe introuvable – installe FFmpeg ou règle FFMPEG_DIR.")

FFPLAY_EXE = os.path.join(os.path.dirname(FFMPEG_EXE), "ffplay.exe")
if not os.path.isfile(FFPLAY_EXE):
    FFPLAY_EXE = shutil.which("ffplay") or shutil.which("ffplay.exe")

os.environ["PATH"] += os.pathsep + os.path.dirname(FFMPEG_EXE)

# ---------- Patch Whisper ----------------------------------------------------
from whisper.audio import N_SAMPLES, SAMPLE_RATE
import whisper.audio as wa

def _wav_to_np(file: str, sr: int = SAMPLE_RATE):
    cmd = [FFMPEG_EXE, "-nostdin", "-threads", "0", "-i", file,
           "-f", "s16le", "-ac", "1", "-acodec", "pcm_s16le",
           "-ar", str(sr), "-"]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    audio = np.frombuffer(out, np.int16).astype(np.float32) / 32768.0
    return np.pad(audio, (0, max(0, N_SAMPLES - len(audio))))[:N_SAMPLES]

wa.load_audio = _wav_to_np

# ---------- Constantes planning ---------------------------------------------
DAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
AVAIL_SET = {"", "libre", "l", "free", "dispo"}
DAY_RE  = re.compile(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b", re.I)
TIME_RE = re.compile(r"\b((?:midi|minuit)|([01]?\d|2[0-3])\s*(?:h|heures?|:|,)\s*([0-5]\d)?)\b", re.I)
EXIT_WORDS = {"quit", "exit", "stop"}

# nombres écrits → chiffres (0-23)
FR_NUM = {
    "zéro":0,"zero":0,"une":1,"un":1,"deux":2,"trois":3,"quatre":4,"cinq":5,"six":6,
    "sept":7,"huit":8,"neuf":9,"dix":10,"onze":11,"douze":12,"treize":13,"quatorze":14,
    "quinze":15,"seize":16,"dix-sept":17,"dix sept":17,"dix-huit":18,"dix huit":18,
    "dix-neuf":19,"dix neuf":19,"vingt":20,"vingt-et-un":21,"vingt et un":21,
    "vingt-deux":22,"vingt deux":22,"vingt-trois":23,"vingt trois":23
}

# ---------- Helpers ----------------------------------------------------------
def words_to_numbers(txt: str) -> str:
    for word, num in FR_NUM.items():
        txt = re.sub(rf"\b{word}\b", str(num), txt)
    return txt

def normalize(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-z0-9 ]", " ", txt.lower())
    return " ".join(txt.split())

def closest_weekday(token: str) -> int | None:
    match = difflib.get_close_matches(token.lower(), DAYS_FR, n=1, cutoff=0.45)
    return DAYS_FR.index(match[0]) if match else None

# ---------- Audio I/O --------------------------------------------------------
def speak(text: str) -> None:
    tts = gTTS(text=text, lang=LANGUAGE)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as fp:
        tts.save(fp.name)
        path = fp.name
    try:
        if FFPLAY_EXE:
            subprocess.run([FFPLAY_EXE, "-nodisp", "-autoexit", path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            if sys.platform.startswith("win"):
                os.startfile(path)
            else:
                subprocess.run(["open" if sys.platform.startswith("darwin") else "xdg-open", path])
            time.sleep(1.0)
    finally:
        time.sleep(0.3)
        try:
            os.remove(path)
        except OSError:
            pass

def record_microphone() -> str:
    rec = sr.Recognizer()
    with sr.Microphone() as src:
        rec.adjust_for_ambient_noise(src, duration=1.0)
        print("🎙️  Parlez… (dites 'au revoir' pour quitter)")
        audio = rec.listen(src)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as fp:
        fp.write(audio.get_wav_data())
        return fp.name

def transcribe(path: str) -> str:
    model = whisper.load_model("base")           # passe à "small" si besoin
    result = model.transcribe(path, language=LANGUAGE,
                              temperature=[0, 0.2, 0.4])
    return result["text"].strip()

# ---------- Charger planning -------------------------------------------------
def _parse_slot_time(label: str) -> dtime | None:
    s = re.sub(r"[hH,]", ":", label.split("-")[0]).strip()
    if re.match(r"^\d{1,2}:$", s):
        s += "00"
    try:
        return datetime.strptime(s, "%H:%M").time()
    except ValueError:
        return None

def load_schedule(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, header=None, engine="openpyxl")
    day_row = next((i for i in range(min(10, len(df)))
                    if all(str(x).lower() in DAYS_FR for x in df.iloc[i, 3:10])), None)
    if day_row is None:
        raise ValueError("Impossible de détecter la ligne des jours.")

    days = df.iloc[day_row, 3:10].astype(str).tolist()
    rows = []
    for r in range(day_row + 1, len(df)):
        label = str(df.iat[r, 2])
        if label.lower() == "nan":
            continue
        slot_time = _parse_slot_time(label)
        if not slot_time:
            continue
        for c, day in enumerate(days, start=3):
            if c >= df.shape[1]:
                break
            txt = "" if pd.isna(df.iat[r, c]) else str(df.iat[r, c]).strip()
            rows.append({
                "weekday": DAYS_FR.index(day.lower()),
                "start": slot_time,
                "available": txt.lower() in AVAIL_SET
            })
    return pd.DataFrame(rows)

def is_available(df: pd.DataFrame, w: int, t: dtime) -> bool:
    def near(a):
        return abs(datetime.combine(date.min, a) - datetime.combine(date.min, t)) \
               <= timedelta(minutes=TOL_MINUTES)
    sub = df[(df.weekday == w) & (df.start.apply(near))]
    return False if sub.empty else bool(sub.iloc[0].available)

# ---------- Parsing phrase ---------------------------------------------------
def parse_phrase(text: str):
    txt = words_to_numbers(text.lower())

    h_match = TIME_RE.search(txt)
    if not h_match:
        return None, None
    if h_match.group(1) == "midi":
        hour, minute = 12, 0
    elif h_match.group(1) == "minuit":
        hour, minute = 0, 0
    else:
        parts = re.sub("[^0-9]", ":", h_match.group(1)).split(":")
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 and parts[1] else 0

    d_match = DAY_RE.search(txt)
    if d_match:
        weekday = DAYS_FR.index(d_match.group(1).lower())
        return weekday, dtime(hour, minute)

    for tok in re.findall(r"[\\w-]+", txt):
        wk = closest_weekday(tok)
        if wk is not None:
            return wk, dtime(hour, minute)
    return None, None

def should_exit(text: str) -> bool:
    norm = normalize(text)
    return "au revoir" in norm or "aurevoir" in norm or any(cmd in norm for cmd in EXIT_WORDS)

# ---------- Boucle principale -----------------------------------------------
def main():
    try:
        agenda = load_schedule(EXCEL_PATH)
    except Exception as exc:
        print("❌", exc)
        sys.exit(1)

    print("✅ Agenda chargé. Dites 'au revoir' pour arrêter.")

    while True:
        wav = record_microphone()
        try:
            speech = transcribe(wav)
        finally:
            os.remove(wav)

        print("📝 Vous :", speech, flush=True)

        if should_exit(speech):
            speak("Au revoir !")
            break

        weekday, t = parse_phrase(speech)
        if weekday is None:
            speak("Je n'ai pas saisi le jour ou l'heure. Pouvez-vous répéter ?")
            continue

        time_str = f"{t.hour:02d}h{t.minute:02d}" if t.minute else f"{t.hour}h"
        reply = (
            f"Oui, {DAYS_FR[weekday]} à {time_str} est disponible."
            if is_available(agenda, weekday, t)
            else f"Désolé, {DAYS_FR[weekday]} à {time_str} n'est pas disponible."
        )
        print("🤖", reply, flush=True)
        speak(reply)

if __name__ == "__main__":
    main()
