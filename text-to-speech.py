import pyttsx3
from gtts import gTTS
import os
import playsound


def text_to_speech1(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Vitesse de la voix
    engine.setProperty('volume', 1)  # Volume max
    voices = engine.getProperty('voices')
    engine.setProperty('voice', voices[0].id)  # Choisir la voix (0 = homme, 1 = femme selon config)
    engine.say(text)
    engine.runAndWait()

# text = "Yifan caca pipi prout"
# text_to_speech1(text)


def text_to_speech2(text, lang="fr"):
    tts = gTTS(text=text, lang=lang)
    filename = "speech.mp3"
    tts.save(filename)
    playsound.playsound(filename)
    os.remove(filename)  # Supprime le fichier après lecture

text = "Bonjour, ceci est un test de synthèse vocale en Python."
text_to_speech2(text)