from __future__ import annotations
import os, sys, tempfile, time, re, difflib, unicodedata
from datetime import datetime, timedelta, time as dtime

import speech_recognition as sr
import openai
from gtts import gTTS
from playsound import playsound

from planning_json import Planning, Appoint

LANGUAGE = "fr"
TOL_MINUTES = 15
DAYS_FR = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]
EXIT_WORDS = {"quit", "exit", "stop"}
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "***REMOVED-OPENAI-KEY-1***")

TIME_RE = re.compile(r"\b((?:midi|minuit)|([01]?\d|2[0-3])\s*(?:h|heures?|:|,)\s*([0-5]\d)?)\b", re.I)
DAY_RE  = re.compile(r"\b(lundi|mardi|mercredi|jeudi|vendredi|samedi|dimanche)\b", re.I)

def speak(text: str) -> None:
    # Crée un fichier temporaire dans le dossier courant pour éviter les problèmes de chemin
    temp_path = os.path.join(os.getcwd(), "temp_tts.mp3")
    tts = gTTS(text=text, lang=LANGUAGE)
    tts.save(temp_path)
    try:
        playsound(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

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
    with open(path, "rb") as audio_file:
        client = openai.OpenAI(api_key=OPENAI_API_KEY)
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=LANGUAGE
        )
    return transcript.text.strip()

def normalize(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt).encode("ascii", "ignore").decode()
    txt = re.sub(r"[^a-z0-9 ]", " ", txt.lower())
    return " ".join(txt.split())

def parse_phrase(text: str):
    txt = text.lower()
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

    for tok in re.findall(r"[\w-]+", txt):
        match = difflib.get_close_matches(tok, DAYS_FR, n=1, cutoff=0.5)
        if match:
            return DAYS_FR.index(match[0]), dtime(hour, minute)
    return None, None

def should_exit(text: str) -> bool:
    norm = normalize(text)
    return "au revoir" in norm or "aurevoir" in norm or any(cmd in norm for cmd in EXIT_WORDS)

def main():
    planning = Planning.load(2025, directory=os.path.dirname(__file__))
    print("✅ Assistant vocal prêt. Dites 'au revoir' pour arrêter.")

    while True:
        speak("Bonjour, comment puis-je vous aider ?")
        wav = record_microphone()
        try:
            speech = transcribe(wav)
        finally:
            os.remove(wav)
        print("📝 Vous :", speech)

        if should_exit(speech):
            speak("Au revoir !")
            break

        if not any(word in normalize(speech) for word in ["rendez", "rdv", "rendezvous", "prendre un rendez"]):
            speak("Veuillez indiquer que vous souhaitez prendre un rendez-vous.")
            continue

        speak("Très bien, quel jour et quelle heure vous conviendraient ?")
        wav = record_microphone()
        try:
            when = transcribe(wav)
        finally:
            os.remove(wav)
        print("📝 Jour/Heure :", when)

        if should_exit(when):
            speak("Au revoir !")
            break

        weekday, t = parse_phrase(when)
        if weekday is None or t is None:
            speak("Je n'ai pas compris le jour ou l'heure. Veuillez répéter.")
            continue

        found = planning.find_slot(weekday, t)
        time_str = f"{t.hour:02d}h{t.minute:02d}"

        if not found:
            speak(f"Désolé, {DAYS_FR[weekday]} à {time_str} n'est pas disponible.")
            continue

        speak(f"{DAYS_FR[weekday]} à {time_str} est disponible. Quel est votre nom ?")
        wav = record_microphone()
        try:
            name = transcribe(wav)
        finally:
            os.remove(wav)
        print("📝 Nom :", name)

        if should_exit(name):
            speak("Au revoir !")
            break

        planning.book_slot(found, name)
        speak(f"Merci {name}, votre rendez-vous est confirmé pour {DAYS_FR[weekday]} à {time_str}.")

if __name__ == "__main__":
    main()