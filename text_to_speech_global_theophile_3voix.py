import pyttsx3
from gtts import gTTS
import os
import pygame


def list_voices():
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    print("=== Voix disponibles ===")
    for i, voice in enumerate(voices):
        print(f"{i} : {voice.name} - {voice.id}")
    print("========================")


def text_to_speech_pyttsx3(text, voice_id=0, rate=150, volume=1):
    engine = pyttsx3.init()
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[voice_id].id)
    engine.setProperty('rate', rate)
    engine.setProperty('volume', volume)
    engine.say(text)
    engine.runAndWait()


def text_to_speech_gtts(text, lang="fr"):
    tts = gTTS(text=text, lang=lang, slow=False)
    filename = "temp_speech.mp3"
    tts.save(filename)

    pygame.mixer.init()
    pygame.mixer.music.load(filename)
    pygame.mixer.music.play()

    while pygame.mixer.music.get_busy():
        continue

    os.remove(filename)


# ================================
# Exemple d'utilisation
# ================================

text = "Ceci est un test, la meilleure voix est la deuxième."

print("Choisissez le moteur de synthèse :")
print("1 - pyttsx3 (Offline, voix système)")
print("2 - gTTS (Google, plus naturel mais online)")

choice = input("Votre choix : ")

if choice == "1":
    list_voices()
    voice_id = int(input("Entrez le numéro de la voix que vous voulez utiliser : "))
    text_to_speech_pyttsx3(text, voice_id)
elif choice == "2":
    text_to_speech_gtts(text)
else:
    print("Choix invalide.")