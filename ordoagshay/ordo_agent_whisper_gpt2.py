import os, sys
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(__file__,'..','..')
    )
)

import datetime
from typing import List
from pydantic import BaseModel
from common.ai.API_client import API_Client
from common.ai.model.BaseAIModel import Message
from common.ai.audio_controller.audio_controller import AUDIO_Controller

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas


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
        self.API_KEY = os.getenv("API_KEY")
        self.client = API_Client()
        self.audio_ctrl = AUDIO_Controller(device_index=1)  # Ou mets None si tu ne spécifies pas de micro
        self.medecin_info = "Dr Jean Martin"
        
       

    def parler(self, texte: str):
        print(f"🗣️ {texte}")
        try:
            audio_path = self.client.tts(texte)
            self.audio_ctrl.play(audio_path)
        except Exception as e:
            print(f"❌ Erreur synthèse vocale : {e}")

    def enregistrer_audio(self, duree=15):
        self.parler("Vous pouvez parler maintenant.")
        print("🎙️ Enregistrement en cours...")
        return self.audio_ctrl.listen()

    def transcrire_audio(self, audio_path: str) -> str:
        self.parler("Transcription en cours...")
        try:
            message = self.client.stt(audio_path)
            print(f"📝 Transcription : {message.content}")
            return message.content
        except Exception as e:
            print(f"❌ Erreur transcription : {e}")
            return ""

    def extraire_infos(self, texte: str) -> PatientInfo:
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

        response = self.client.basic([Message(role="user", content=prompt)])
        import json

        try:
            content_dict = json.loads(response.content)
            return PatientInfo(**content_dict)
        except Exception as e:
            print(f"❌ Erreur parsing JSON : {e}")
            raise

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
        if not texte:
            self.parler("Je n'ai pas compris. Veuillez réessayer.")
            return None
        info = self.extraire_infos(texte)
        fichier = self.generer_ordonnance(info)
        self.parler("Ordonnance générée avec succès.")
        return fichier

if __name__ == "__main__":
    agent = OrdoAgent()
    output = agent.lancer()
    if output:
        print(f"✅ Fichier généré : {output}")
