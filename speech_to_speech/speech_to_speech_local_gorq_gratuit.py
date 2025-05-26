import whisper
import os
import tempfile
from gtts import gTTS
import subprocess
from openai import OpenAI

# ========== AJOUT AU PATH POUR FFMPEG ==========
ffmpeg_dir = r"C:\Users\theop\Documents\Telecom_Paris\Artishow\git_artishow\secretaryai\ffmpeg\bin"
os.environ["PATH"] += os.pathsep + ffmpeg_dir
ffmpeg_exe = os.path.join(ffmpeg_dir, "ffmpeg.exe")
ffplay_exe = os.path.join(ffmpeg_dir, "ffplay.exe")

# ========== CONFIGURATION GROQ ==========
groq_client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

# ✅ Fichier à traiter
default_audio_file = "C:/Users/theop/Documents/Telecom_Paris/Artishow/git_artishow/secretaryai/bonjour_destination_juillet.mp3"

# ========== PATCH DE whisper.audio.load_audio ==========
import whisper.audio as wa
from whisper.audio import N_SAMPLES, SAMPLE_RATE
import numpy as np
import io
import torch

def load_audio_custom(file: str, sr: int = SAMPLE_RATE):
    cmd = [
        ffmpeg_exe,
        "-nostdin",
        "-threads", "0",
        "-i", file,
        "-f", "s16le",
        "-ac", "1",
        "-acodec", "pcm_s16le",
        "-ar", str(sr),
        "-"
    ]
    out = subprocess.run(cmd, capture_output=True, check=True).stdout
    audio = np.frombuffer(out, np.int16).flatten().astype(np.float32) / 32768.0
    if audio.shape[0] < N_SAMPLES:
        audio = np.pad(audio, (0, N_SAMPLES - audio.shape[0]))
    else:
        audio = audio[:N_SAMPLES]
    return audio

wa.load_audio = load_audio_custom

# ========== TRANSCRIPTION ==========
def transcribe_audio_local(file_path):
    print("📝 Transcription locale avec Whisper...")

    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"❌ Fichier audio introuvable : {file_path}")
    print(f"✅ Fichier trouvé : {file_path}")

    model = whisper.load_model("base")
    result = model.transcribe(file_path, language="fr")
    return result["text"]

# ========== TRAITEMENT IA ==========
def process_with_ai(question):
    print("🧠 Traitement de la question avec Groq...")
    response = groq_client.chat.completions.create(
        model="llama3-8b-8192",
        messages=[
            {"role": "system", "content": "Tu es un assistant utile, bienveillant, et francophone."},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content

# ========== SYNTHÈSE VOCALE ==========
def speak(text):
    tts = gTTS(text=text, lang="fr")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio_path = temp_audio.name
        tts.save(temp_audio_path)

    print("🗣️ Réponse vocale en cours...")
    try:
        subprocess.run([ffplay_exe, "-nodisp", "-autoexit", temp_audio_path], check=True)
    finally:
        os.remove(temp_audio_path)

# ========== MAIN ==========
def main(audio_file):
    print("🎧 Traitement du fichier :", audio_file)
    question = transcribe_audio_local(audio_file)
    print("🧾 Texte reconnu :", question)
    answer = process_with_ai(question)
    print("🤖 Réponse :", answer)
    speak(answer)

if __name__ == "__main__":
    main(default_audio_file)
