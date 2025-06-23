import os, sys
sys.path.insert(
    0,
    os.path.abspath(
        os.path.join(__file__, '..','..')
    )
)
from common.ai.API_client import API_Client
from common.ai.audio_controller.audio_controller import AUDIO_Controller
from common.ai.model.BaseAIModel import Message
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from typing import List
from pydantic import BaseModel
import json



class MedicamentInfo(BaseModel):
    nom: str
    quantite: str
    duree: str


class PatientInfo(BaseModel):
    patient: str
    medicaments: List[MedicamentInfo]


class OrdoAgent:
    def __init__(self):
        self.api_client = API_Client()  # Instanciez votre client API ici
        self.medecin_info = "Dr Jean Martin"

    def parler(self, texte: str):
        """Utilise la fonction TTS pour parler au patient."""
        audio_path = self.api_client.tts(texte)
        os.system(f"afplay {audio_path}")  # Utilisez 'afplay' sur Mac pour jouer l'audio

    def transcrire_audio(self, audio_path: str) -> str:
        """Utilise la fonction STT pour transcrire l'audio en texte."""
        return self.api_client.stt(audio_path)

    def extraire_infos(self, texte: str) -> PatientInfo:
        """Utilise la fonction parse pour extraire les informations nécessaires."""
        # Modèle de données attendu pour l'ordonnance
        class OrdonnanceModel(BaseModel):
            patient: str
            medicaments: List[MedicamentInfo]

        # Messages à envoyer à l'API
        messages = [
            {"role": "user", "content": texte}
        ]

        # Appel à la fonction parse pour structurer les données
        ordonnance = self.api_client.parse(messages=messages, data_model=OrdonnanceModel)
        return ordonnance

    def generer_ordonnance(self, informations: PatientInfo) -> str:
        """Génère un fichier PDF contenant l'ordonnance."""
        chemin_fichier = f"ordonnance_{informations.patient.replace(' ', '_')}.pdf"
        c = canvas.Canvas(chemin_fichier, pagesize=A4)
        hauteur = A4[1]

        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, hauteur - 50, "ORDONNANCE MÉDICALE")

        c.setFont("Helvetica", 12)
        c.drawString(50, hauteur - 80, f"Médecin : {self.medecin_info}")
        c.drawString(50, hauteur - 100, f"Patient : {informations.patient}")

        c.setFont("Helvetica-Bold", 15)
        c.drawString(50, hauteur - 150, "Médicaments prescrits :")
        c.setFont("Helvetica", 12)
        y_position = hauteur - 180

        for med in informations.medicaments:
            c.drawString(50, y_position, f"- {med.nom} : {med.quantite} pendant {med.duree}")
            y_position -= 20

        c.drawString(350, y_position - 50, "Signature du médecin : ___________")
        c.save()

        print(f"📄 Ordonnance générée : {chemin_fichier}")
        return chemin_fichier

    def lancer(self):
        """Lance le processus complet."""
        self.parler("Bonjour, je suis votre assistant médical. Veuillez fournir les informations nécessaires pour l'ordonnance.")
        audio_path = "enregistrement.wav"  # Chemin où l'audio sera enregistré
        texte = self.transcrire_audio(audio_path)
        if not texte:
            self.parler("Je n'ai pas compris. Veuillez réessayer.")
            return None

        try:
            info = self.extraire_infos(texte)
            fichier = self.generer_ordonnance(info)
            self.parler(f"L'ordonnance a été générée avec succès. Vous pouvez la trouver dans le fichier {fichier}.")
        except ValueError as e:
            self.parler("Une erreur est survenue lors de la création de l'ordonnance. Veuillez réessayer.")
            print(f"Erreur : {e}")


if __name__ == "__main__":
    agent = OrdoAgent()
    agent.lancer()