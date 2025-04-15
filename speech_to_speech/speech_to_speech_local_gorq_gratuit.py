import whisper
import os
import tempfile
from gtts import gTTS
import playsound
import argparse
from openai import OpenAI

# ========== CONFIGURATION ENVIRONNEMENT ========== 
os.environ["FFMPEG_BINARY"] = r"C:\Users\theop\Documents\Telecom_Paris\Artishow\git_secretary_ai\git_clone\ffmpeg\bin\ffmpeg.exe"

# ========== CONFIGURATION GROQ ========== 
groq_client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

# ========== CHEMIN D'ACCÈS AU FICHIER AUDIO PAR DÉFAUT ==========
default_audio_file = "C:/Users/theop/Documents/Telecom_Paris/Artishow/git_secretary_ai/git_clone/bonjour_destination_juillet.mp3"

# ========== ÉTAPE 1 : Transcription locale ==========
def transcribe_audio_local(file_path):
    print("📝 Transcription locale avec Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(file_path, language="fr")
    return result["text"]

# ========== ÉTAPE 2 : Traitement par l'IA ==========
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

# ========== ÉTAPE 3 : Lecture vocale ==========
def speak(text):
    from gtts import gTTS
    import tempfile
    import subprocess

    tts = gTTS(text=text, lang="fr")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio_path = temp_audio.name
        tts.save(temp_audio_path)

    print("🗣️ Réponse vocale en cours...")

    # 🔊 Lecture avec ffplay
    ffplay_path = r"C:\Users\theop\Documents\Telecom_Paris\Artishow\git_secretary_ai\git_clone\ffmpeg\bin\ffplay.exe"
    try:
        subprocess.run([ffplay_path, "-nodisp", "-autoexit", temp_audio_path], check=True)
    finally:
        os.remove(temp_audio_path)


# ========== MAIN ==========
def main(audio_file):
    print("🎧 Traitement du fichier :", audio_file)

    # 1. Transcrire l'audio
    question = transcribe_audio_local(audio_file)
    print("🧾 Texte reconnu :", question)

    # 2. Répondre à la question avec Groq
    answer = process_with_ai(question)
    print("🤖 Réponse :", answer)

    # 3. Lire la réponse à haute voix
    speak(answer)

if __name__ == "__main__":
    main(default_audio_file)