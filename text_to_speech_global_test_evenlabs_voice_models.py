import requests
import pygame
import time

# Mets ici ta clé API ElevenLabs
API_KEY = "sk_1aeadb0b746e18b811764e47e3ecd35dbd059347d37126ed"

# ID de la voix choisie (exemple : Mbappé ou autre)
VOICE_ID = "EXm8E7ZmYXa9aWqW4a8B"  # Change par l'ID de la voix souhaitée

def generate_and_play(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": API_KEY,
        "Content-Type": "application/json"
    }
    data = {
        "text": text,
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75
        }
    }

    print("Génération de la voix...")
    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 200:
        with open("output.mp3", "wb") as f:
            f.write(response.content)

        print("Lecture audio...")
        pygame.mixer.init()
        pygame.mixer.music.load("output.mp3")
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.5)
    else:
        print("Erreur :", response.status_code, response.text)

# Exemple d'utilisation
texte = input("Écris ton message à faire dire par Mbappé : ")
generate_and_play(texte)