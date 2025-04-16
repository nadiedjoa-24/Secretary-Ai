from openai import OpenAI
from datetime import datetime, timedelta
from elevenlabs import play
from email.mime.text import MIMEText
import speech_recognition as sr
import re
import json
from typing import Literal
from pydantic import BaseModel
import os
from pathlib import Path
import sys
sys.path.append("/Users/yanicrothlingshofer/Desktop/Telecom Paris/1A/ARTISHOW/secretaryai/ai_agents/tools")
from planning import Planning, Appointment
from dotenv import load_dotenv
import pygame



env_path = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(dotenv_path=env_path)

def is_available(planning: Planning, appointment: Appointment):
    return planning.is_available(appointment)

def access_planning(planning: Planning, months: list[str]):
    d = dict()
    for month in months:
        d[month] = planning[month]
    return d

def add_appointment(planning: Planning, appointment: Appointment):
    planning.add(appointment)



class AI_Assistant:

    api_key = os.getenv("OPENAI_API_KEY2")
    print(api_key)

    def __init__(self):
        self.openai_client = OpenAI(api_key=self.api_key)
        # self.elevenlabs_api_key = "sk_e487e38360d8f73dbcc8ebc23b6f6513c56486cc167e55e4"
        # # self.elevenlabs_client = ElevenLabs(api_key=self.elevenlabs_api_key)
        self.planning = Planning(2025)
        self.current_date = datetime.today()
        print(self.planning.rplanning["2"]["15"]["Smith"])
        print(datetime.today().strftime("%A"), datetime.today())


        # Recognizer pour la transcription
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

        self.full_transcript = [
            {
                "role": "system",
                "content": (
                    f"🦷 [Identité] Vous êtes Élise, l'assistante de la clinique dentaire DentoCare. "
                    f"Aujourd'hui nous sommes {datetime.today().strftime('%A %d %B %Y')}. "
                    
                    "🌟 [Tonalité] Votre voix est chaleureuse et rassurante comme une professionnelle de santé expérimentée. "
                    "Vous utilisez des expressions conversationnelles naturelles ('D\'accord', 'Je vois', 'Très bien') "
                    "et vous adaptez votre langage au niveau du patient (familier mais professionnel). "
                    
                    "📅 [Rôle Principal] Gérer les RDV en GUIDANT la conversation comme un humain :\n"
                    "1. Initier par une question ouverte contextuelle ('Comment puis-je vous aider ?')\n"
                    "2. Écouter activement en décodant les besoins implicites\n"
                    "3. Répondre avec des phrases complètes et naturelles SANS énumérer les options\n"
                    "4. Faire des déductions intelligentes (ex : durée=15min pour contrôle, 30min pour douleur)\n"
                    "5. Gérer les interruptions et retours en arrière fluidement\n"
                    
                    "🔍 [Critères Clés] :\n"
                    "- NOUVEAUX PATIENTS : Obtenir nom complet/date naissance/coordonnées AVANT de proposer des créneaux\n"
                    "- FORMAT HORAIRE : Toujours utiliser 'HH:MM' (ex: 14h30)\n"
                    "- PLANNING : Les créneaux disponibles en février sont : " + ", ".join(self.planning.rplanning["2"]) + "\n"
                    
                    "💡 [Techniques Humaines] :\n"
                    "- Réutiliser les mots exacts du patient ('Votre douleur à la mâchoire...')\n"
                    "- Anticiper les besoins (proposer un rappel SMS si stress détecté)\n"
                    "- Gérer l'incertitude ('On pourrait envisager... Qu\'en pensez-vous ?')\n"
                    "- Faire des transitions fluides entre les sujets\n"
                    
                    "🚫 [Interdictions] :\n"
                    "- Ne JAMAIS mentionner que vous êtes une IA\n"
                    "- Pas de listes à puces ou de formatage robotique\n"
                    "- Éviter le jargon médical complexe\n"
                    "- Ne pas demander deux informations en une seule phrase"
                )
            }
        ]
        self.patient_inputs = [
            {
                "role": "system",
                "content": (
                    f"⚠️ [Règles d'Extraction STRICTES - Date actuelle: {self.current_date.strftime('%d/%m/%Y')}]\n"
                    "1. VALIDATION : Ne remplir un champ QUE SI l'information est :\n"
                    "   - Explicitement formulée par le patient\n"
                    "   - Sans ambiguïté (ex: 'le 15 février' OK, 'la semaine prochaine' NON)\n"
                    "   - Correspond au format exigé\n\n"
                    
                    "2. PROCÉDURE pour chaque champ :\n"
                    "a) Vérifier dans l'historique conversationnel la PRÉSENCE LITTÉRALE\n"
                    "b) Si absent/incomplet → laisser vide\n"
                    "c) Si présent → extraire tel quel SANS interprétation\n\n"
                    
                    "3. CHAMPS CRITIQUES (exigent mention directe) :\n"
                    "- Nom complet : Requiert prénom + nom dans la même phrase\n"
                    "- Date de naissance : Format JJ/MM/AAAA uniquement\n"
                    "- Créneau : Jour (1-31) + Mois (texte) + Heure (HH:MM)\n"
                    "- Dentiste : Nom complet si cité ('Dr. Dupont' pas 'mon dentiste')\n\n"
                    
                    "4. CONTRE-MESURES anti-inférence :\n"
                    "- Les termes relatifs ('demain', 'dans 2 semaines') → conversion via date actuelle SEULEMENT\n"
                    "- Les symptômes ≠ motif de RDV (ex: 'j'ai mal' → durée=30min MAIS ne pas l'écrire)\n"
                    "- Les préférences implicites ('je préfère le matin') → ne pas considérer comme confirmation\n\n"
                    
                    # "5. EXEMPLES :\n"
                    # "Patient: 'Le 10 vers 14h?' → {jour:10, mois:vide, heure:14:00}\n"
                    # "Patient: 'Avec le Dr. Martin' → {dentiste: Dr. Martin}\n"
                    # "Patient: 'Je suis libre lundi prochain' → {jour:vide, mois:vide}\n\n"
                    
                    "🔔 Toute violation de ces règles entraînera l'éviction des données invalides."
                )
            }
        ]



    def generate_ai_response(self, transcript):
        self.full_transcript.append({"role": "user", "content": transcript})
        print(f"\nPatient: {transcript}")

        response = self.openai_client.chat.completions.create(
            model="4o-mini",
            messages=self.full_transcript
        )

        ai_response = response.choices[0].message.content

        self.generate_audio(ai_response)
        print(f"\nReal-time transcription: ", end="\r\n")



    def start_listening(self):
        print("🎤 En attente de parole")
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source)
            audio = self.recognizer.listen(source)
        
        print("🎙️ Transcription : ")
        try:
            transcript = self.transcribe_audio(audio)
            return transcript 
        except Exception as e:
            print(f"❌ Erreur transcription : {e}")



    def transcribe_audio(self, audio):
        """ Envoie l'audio à Whisper et récupère le texte """
        audio_data = audio.get_wav_data()

        response = self.openai_client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=("audio.wav", audio_data, "audio/wav"),
            response_format="text"
        )

        return response if response else None
    


    def generate_audio(self, text):
        speech_file_path = Path(__file__).parent / "speech.mp3"
        audio = self.openai_client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            # instructions="use a monotone tone.",
        )
        audio.stream_to_file(speech_file_path)
        pygame.mixer.init()
        pygame.mixer.music.load(str(speech_file_path))
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            continue



    def start_conversation(self):

        message = self.start_listening()
        if message is None:
            print("⚠️ Aucun message détecté, on recommence :")
            return
        # message = input()
        self.full_transcript.append({"role": "user", "content": message})
        self.patient_inputs.append({"role": "user", "content": message})
        Bool, appointment = self.check_appointment()
        if Bool:
            print("Rendez vous ajouté")
            self.planning.add(appointment)
            self.full_transcript.append({"role":"system", "content":"Le rendez vous a bien été ajouté."})
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages = self.full_transcript
            ).choices[0].message.content
            self.generate_audio(response)
            # print(response)
        else:
            print("No intent, resuming conversation !")
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages = self.full_transcript,
            ).choices[0].message.content
            self.full_transcript.append({"role":"assistant", "content":response})
            self.generate_audio(response)
            # print(response)


        
    def check_appointment(self):
        response = self.openai_client.beta.chat.completions.parse(
            model="gpt-4o",
            messages= self.patient_inputs,
            response_format = Appointment,
        ).choices[0].message.parsed
        self.full_transcript.append({"role":"assistant", "content": str(response)})
        print(response)
        return response.are_fields_filled(), response




    
        


        

if __name__ == "__main__":

    AI = AI_Assistant()

    while True:
        AI.start_conversation()