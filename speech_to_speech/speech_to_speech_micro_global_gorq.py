import whisper
import os
import tempfile
from gtts import gTTS
import subprocess
import speech_recognition as sr
from openai import OpenAI

# ========== CONFIGURATION ENVIRONNEMENT ========== 
os.environ["FFMPEG_BINARY"] = r"C:\Users\theop\Documents\Telecom_Paris\Artishow\git_secretary_ai\git_clone\ffmpeg\bin\ffmpeg.exe"

# ========== CONFIGURATION GROQ ========== 
groq_client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

# ========== FONCTION : Transcription via Whisper local ========== 
def transcribe_audio_local(file_path):
    print("📝 Transcription locale avec Whisper...")
    model = whisper.load_model("base")
    result = model.transcribe(file_path, language="fr")
    return result["text"]

# ========== FONCTION : Traitement IA ========== 
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

# ========== FONCTION : Parler avec gTTS ========== 
def speak(text):
    tts = gTTS(text=text, lang="fr")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        temp_audio_path = temp_audio.name
        tts.save(temp_audio_path)

    print("🗣️ Réponse vocale en cours (vitesse augmentée)...")

    ffplay_path = r"C:\Users\theop\Documents\Telecom_Paris\Artishow\git_secretary_ai\git_clone\ffmpeg\bin\ffplay.exe"
    try:
        # Ajouter un filtre audio pour augmenter la vitesse (atempo = 1.0 est normal)
        subprocess.run([
            ffplay_path,
            "-nodisp",
            "-autoexit",
            "-af", "atempo=1.35",  # ↖️ ici tu peux régler la vitesse (1.0 = normal)
            temp_audio_path
        ], check=True)
    finally:
        os.remove(temp_audio_path)


# ========== FONCTION : Enregistrer l'audio du micro ========== 
def record_audio():
    print("🎙️ Parle maintenant (enregistrement en cours)...")
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        recognizer.adjust_for_ambient_noise(source)
        audio = recognizer.listen(source)
        print("📤 Audio capturé, traitement en cours...")

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
        temp_audio_path = temp_audio.name
        with open(temp_audio_path, "wb") as f:
            f.write(audio.get_wav_data())
    return temp_audio_path

# ========== MAIN INTERACTIF ========== 
def main_loop():
    while True:
        try:
            # 1. Enregistrer l'audio du micro
            audio_path = record_audio()

            # 2. Transcrire
            question = transcribe_audio_local(audio_path)
            print("🧾 Texte reconnu :", question)
            os.remove(audio_path)

            if question.strip().lower() in ["quitte", "exit", "stop", "au revoir"]:
                print("👋 Fin de la session.")
                break

            # 3. Répondre via Groq
            answer = process_with_ai(question)
            print("🤖 Réponse :", answer)

            # 4. Parler la réponse
            speak(answer)

        except Exception as e:
            print("❌ Une erreur est survenue :", e)

if __name__ == "__main__":
    main_loop()
