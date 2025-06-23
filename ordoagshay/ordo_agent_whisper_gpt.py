import os
import io
import datetime
import sounddevice as sd
import scipy.io.wavfile as wav
from openai import OpenAI
from dotenv import load_dotenv
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from pydantic import BaseModel
from typing import List
import pyttsx3

load_dotenv()

class MedicamentInfo(BaseModel):
    nom: str
    quantite: str
    duree: str

class PatientInfo(BaseModel):
    patient: str
    medecin: str
    medicaments: List[MedicamentInfo]

class OrdoAgent:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API Key OpenAI manquante.")
        self.client = OpenAI(api_key=self.api_key)
        self.medecin_info = "Dr Jean Martin"
        self.voix = pyttsx3.init()
        self.voix.setProperty('rate', 150)

    def parler(self, texte: str):
        print(f"🗣️ {texte}")
        self.voix.say(texte)
        self.voix.runAndWait()

    def enregistrer_audio(self, duree=15, fs=44100):
        self.parler("Vous pouvez parler maintenant.")
        print("🎙️ Enregistrement en cours...")
        audio = sd.rec(int(duree * fs), samplerate=fs, channels=1)
        sd.wait()
        buffer = io.BytesIO()
        wav.write(buffer, fs, audio)
        buffer.seek(0)
        return buffer

    def transcrire_audio(self, audio_buffer):
        self.parler("Transcription en cours...")
        transcription = self.client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_buffer,
            response_format="text",
            language="fr"
        )
        print(f"📝 Transcription : {transcription}")
        return transcription

    def extraire_infos(self, texte):
        self.parler("Analyse des données médicales...")
        prompt = (
            "Tu es un assistant médical. À partir de la description suivante :\n"
            f"{texte}\n\n"
            "Extrait les informations au format JSON suivant :\n"
            """{
  "patient": "Nom du patient",
  "medecin": "Nom du médecin",
  "medicaments": [
    {
      "nom": "Nom du médicament",
      "quantite": "Quantité",
      "duree": "Durée"
    }
  ]
}"""
        )
        reponse = self.client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            response_format="json"
        )
        return PatientInfo(**reponse.model_dump()["choices"][0]["message"]["content"])

    def generer_ordonnance(self, informations: PatientInfo):
        dossier = os.path.abspath("public/ordonnances")
        os.makedirs(dossier, exist_ok=True)

        fichier_nom = f"ordonnance_{informations.patient.replace(' ', '_')}.pdf"
        chemin_fichier = os.path.join(dossier, fichier_nom)

        c = canvas.Canvas(chemin_fichier, pagesize=A4)
        largeur, hauteur = A4

        centre_info = [
            "Centre Médical Saint Jean",
            "23 rue des Lilas, Yerres 91330",
            "Tél : 01 23 45 67 89",
            "Dentiste, Médecine Générale, Kinésithérapeute"
        ]

        x_position = 330
        y_position = 800
        for i, line in enumerate(centre_info):
            c.drawString(x_position, y_position - i * 15, line)

        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, hauteur - 50, "ORDONNANCE MÉDICALE")

        c.setFont("Helvetica", 12)
        date_ajd = datetime.date.today().strftime("%d/%m/%Y")
        c.drawString(50, hauteur - 80, f"Date : {date_ajd}")
        c.drawString(50, hauteur - 100, f"Médecin : {informations.medecin}")
        c.drawString(50, hauteur - 120, f"Patient : {informations.patient}")

        c.setFont("Helvetica-Bold", 15)
        c.drawString(50, hauteur - 220, "Médicaments prescrits :")
        c.setFont("Helvetica", 12)
        y_position = hauteur - 250

        for med in informations.medicaments:
            c.drawString(50, y_position, f"- {med.nom} : {med.quantite} pendant {med.duree}")
            y_position -= 20

        c.drawString(350, y_position - 50, "Signature du médecin : ___________")
        c.save()

        print(f"📄 Ordonnance générée : {chemin_fichier}")
        return chemin_fichier

    def lancer(self):
        audio = self.enregistrer_audio()
        texte = self.transcrire_audio(audio)
        info = self.extraire_infos(texte)
        fichier = self.generer_ordonnance(info)
        self.parler("Ordonnance générée avec succès.")
        return fichier

if __name__ == "__main__":
    agent = OrdoAgent()
    output = agent.lancer()
    print(f"✅ Fichier généré : {output}")
