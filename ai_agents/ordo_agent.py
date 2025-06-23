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
    medecin: str
    medicaments: List[MedicamentInfo]

class OrdoAgent:
    def __init__(self, api_key=None, audio_device_index=1):
        self.api_client = API_Client(API_KEY=api_key)
        self.audio_ctrl = AUDIO_Controller(device_index=audio_device_index)
        self.medecin_info = "Dr Jean Martin"
        self.full_transcript = []  # <-- AJOUTE CETTE LIGNE

        self.ordo_extraction_prompt = [
            {
                "role": "system",
                "content": (
                    "Vous êtes un médecin généraliste. "
                    "Votre tâche est d'extraire UNIQUEMENT les informations suivantes à partir de la conversation vocale du patient :\n"
                    "- Nom du patient\n"
                    "- Pathologie (motif de l'ordonnance)\n"
                    "- Médicaments (nom, posologie, durée)\n"
                    "N'EXTRAIRE QUE ce qui est explicitement dit, SANS commentaire, SANS explication, SANS phrase hors sujet. "
                    "Répondez STRICTEMENT sous forme de dictionnaire JSON avec les champs : patient, pathologie, medicaments (liste de {nom, posologie, durée}). "
                    "Si une information n'est pas présente, laissez le champ vide ou la liste vide. "
                    "NE PAS répondre à côté, NE PAS donner d'avis médical, NE PAS reformuler, NE PAS commenter."
                )
            }
        ]

    def parler(self, texte: str):
        """Synthèse vocale et lecture audio via API_Client et AUDIO_Controller."""
        tts_path = self.api_client.tts(texte)
        print(f"TTS généré : {tts_path}")
        self.audio_ctrl.play(tts_path)

    def reconnaitre_voix(self):
        """Écoute le micro, enregistre, puis transcrit avec l'API_Client."""
        print("Veuillez parler après le bip...")
        audio_path = self.audio_ctrl.listen()
        msg = self.api_client.stt(audio_path)
        print(f"Transcription : {msg.content}")
        self.full_transcript.append({"role": "user", "content": msg.content})
        return msg.content

    def generer_ordonnance(self, informations: PatientInfo):
        dossier_ordonnances = os.path.expanduser("~/Desktop/ordonnances")
        os.makedirs(dossier_ordonnances, exist_ok=True)

        if not informations or not informations.patient or not informations.medecin or not informations.medicaments:
            print("❌ Erreur : Informations incomplètes.")
            return

        for med in informations.medicaments:
            if not med.nom or not med.quantite or not med.duree:
                print(f"❌ Erreur : Données incomplètes pour : {med}")
                return

        print("✅ Informations valides. Génération de l'ordonnance...")

        patient_nom = informations.patient
        medecin_nom = informations.medecin
        medicaments = informations.medicaments

        fichier_nom = f"ordonnance_{patient_nom.replace(' ', '_')}.pdf"
        chemin_fichier = os.path.join(dossier_ordonnances, fichier_nom)

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
        c.drawString(50, hauteur - 100, f"Médecin : {medecin_nom}")
        c.drawString(50, hauteur - 120, f"Patient : {patient_nom}")

        c.setFont("Helvetica-Bold", 15)
        c.drawString(50, hauteur - 220, "Médicaments prescrits :")
        c.setFont("Helvetica", 12)
        y_position = hauteur - 250

        for med in medicaments:
            c.drawString(50, y_position, f"- {med.nom} : {med.quantite} pendant {med.duree}")
            y_position -= 20

        c.drawString(350, y_position - 50, "Signature du médecin : ___________")
        c.save()

        print(f"📄 Ordonnance générée : {chemin_fichier}")

    def remplir_ordonnance_par_questions(self):
        # Présentation claire à l'utilisateur
        self.parler("Bonjour, je suis votre assistant médecin. Je vais remplir une ordonnance à partir des informations que vous allez me donner oralement. Veuillez répondre précisément à chaque question, en indiquant le nom du patient, la pathologie, puis chaque médicament avec sa posologie et la durée du traitement.")

        # Nom du patient
        self.parler("Quel est le nom du patient ?")
        nom_patient = self.reconnaitre_voix()
        if not nom_patient:
            self.parler("Je n'ai pas compris le nom du patient. Abandon.")
            return

        # Pathologie
        self.parler("Quel est le motif ou la pathologie ?")
        pathologie = self.reconnaitre_voix()
        if not pathologie:
            self.parler("Je n'ai pas compris la pathologie. Abandon.")
            return

        # Médicaments
        medicaments = []
        while True:
            self.parler("Nom du médicament ? Dites 'c'est tout' si vous avez terminé.")
            nom_med = self.reconnaitre_voix()
            if nom_med and "c'est tout" in nom_med.lower():
                break
            if not nom_med:
                self.parler("Je n'ai pas compris. Recommençons ce médicament.")
                continue

            self.parler("Quelle posologie ? Par exemple : 2 comprimés matin et soir.")
            posologie = self.reconnaitre_voix()
            if not posologie:
                self.parler("Posologie non comprise. Recommençons ce médicament.")
                continue

            self.parler("Pendant combien de jours ?")
            duree = self.reconnaitre_voix()
            if not duree:
                self.parler("Durée non comprise. Recommençons ce médicament.")
                continue

            medicaments.append({
                "nom": nom_med,
                "quantite": posologie,
                "duree": duree
            })
            self.parler("Médicament ajouté.")

        if not medicaments:
            self.parler("Aucun médicament ajouté. Ordonnance annulée.")
            return

        # Création de l'objet PatientInfo adapté
        info_patient = PatientInfo(
            patient=patient,
            medecin=self.medecin_info,
            medicaments=[
                MedicamentInfo(nom=m["nom"], quantite=m["posologie"], duree=m["durée"])
                for m in medicaments
            ],
            pathologie=pathologie
        )

        # Génération de l'ordonnance
        self.generer_ordonnance(info_patient)
        self.parler("Ordonnance générée avec succès.")

    def remplir_ordonnance_auto(self):
        self.parler("Je suis votre médecin. Veuillez me donner toutes les informations pour l'ordonnance, puis dites 'c'est tout' à la fin.")
        while True:
            user_text = self.reconnaitre_voix()
            if "c'est tout" in user_text.lower():
                break
        infos = self.extraire_infos_ordonnance()
        if infos:
            patient = infos.get("patient", "")
            pathologie = infos.get("pathologie", "")
            medicaments = infos.get("medicaments", [])
            info_patient = PatientInfo(
                patient=patient,
                medecin=self.medecin_info,
                medicaments=[
                    MedicamentInfo(
                        nom=m.get("nom", ""),
                        quantite=m.get("posologie", ""),
                        duree=m.get("durée", "")
                    ) for m in medicaments
                ]
            )
            self.generer_ordonnance(info_patient)
            self.parler("Ordonnance générée avec succès.")
        else:
            self.parler("Je n'ai pas pu extraire toutes les informations nécessaires.")

    def discuter(self):
        """Boucle conversationnelle complète."""
        print("=== Conversation continue (dit 'exit' pour quitter) ===")
        while True:
            user_text = self.reconnaitre_voix()
            if user_text.strip().lower() in ("exit", "quit", "stop"):
                print("Fin de la conversation.")
                break
            ai_response = self.api_client.basic([Message(role="user", content=user_text)])
            print(f"Réponse AI : {ai_response.content}")
            self.parler(ai_response.content)

    def extraire_infos_ordonnance(self):
        messages = self.ordo_extraction_prompt + self.full_transcript
        response = self.api_client.basic(messages)
        try:
            infos = json.loads(response.content)
            return infos
        except Exception as e:
            print("Erreur extraction infos ordonnance :", e)
            return None

if __name__ == "__main__":
    agent = OrdoAgent()
    agent.discuter()
    transcript = "..."  # Remplacez par la transcription réelle
    infos = agent.extraire_infos_ordonnance(transcript)
    if infos:
        patient = infos.get("patient", "")
        pathologie = infos.get("pathologie", "")
        medicaments = infos.get("medicaments", [])
        # medicaments = [{"nom": ..., "posologie": ..., "durée": ...}, ...]
