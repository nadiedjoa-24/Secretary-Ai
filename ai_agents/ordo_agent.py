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
    posologie: str
    duree: str

class PatientInfo(BaseModel):
    patient: str
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

                            f"🩺 [Identité] Vous êtes un médecin généraliste assistant virtuel, chargé d'extraire des informations médicales dictées par un patient.\n"
                

                    "🎯 [Mission] Votre tâche consiste UNIQUEMENT à EXTRAIRE les informations EXPLICITEMENT énoncées par le patient pendant une conversation vocale, pour générer une ordonnance médicale.\n"
                    "Aucune interprétation, aucun raisonnement médical, aucun complément d'information ne doit être ajouté.\n\n"

                    "📌 [Champs attendus - Format JSON STRICT] :\n"
                    "- patient : Nom complet du patient\n"
                    "- pathologie : Motif médical de l'ordonnance (si exprimé)\n"
                    "- medicaments : liste de médicaments ({ nom, posologie, durée })\n\n"

                    "📋 [Exigences de validation] :\n"
                    "1. Chaque donnée doit être clairement PRÉSENTE dans les propos du patient.\n"
                    "2. Aucune donnée ne doit être reformulée, corrigée ou déduite implicitement.\n"
                    "3. Si une information est manquante, ambiguë ou absente, laisser le champ vide (`\"\"`) ou une liste vide (`[]`).\n\n"

                    "🚫 [Interdictions Absolues] :\n"
                    "- Ne pas commenter, expliquer ou reformuler les propos du patient\n"
                    "- Ne pas utiliser de phrases complètes ou naturelles (juste du JSON brut)\n"
                    "- Ne pas répondre en dehors du format JSON\n"
                    "- Ne pas mentionner votre statut ou rôle\n\n"

                    "✅ [Format de réponse attendu] :\n"
                    "{\n"
                    "  \"patient\": \"\",\n"
                    "  \"pathologie\": \"\",\n"
                    "  \"medicaments\": [\n"
                    "    {\"nom\": \"\", \"posologie\": \"\", \"durée\": \"\"}\n"
                    "  ]\n"
                    "}\n\n"

                    "🛡️ [Exemples de comportement attendu] :\n"
                    "- Si le patient dit : \"Je suis Pierre Durand, j’ai une angine. Prenez Doliprane 1g matin et soir pendant 5 jours\", alors vous renvoyez :\n"
                    "{\n"
                    "  \"patient\": \"Pierre Durand\",\n"
                    "  \"pathologie\": \"angine\",\n"
                    "  \"medicaments\": [\n"
                    "    {\"nom\": \"Doliprane 1g\", \"posologie\": \"matin et soir\", \"durée\": \"5 jours\"}\n"
                    "  ]\n"
                    "}\n"
                    "- Si aucune pathologie n’est citée, mettez : \"pathologie\": \"\"\n\n"

                    "🔒 Toute réponse ne respectant pas ce format sera rejetée par le système."
                    
                )
            }
        ]

    def parler(self, texte: str):
        """Synthèse vocale et lecture audio via API_Client et AUDIO_Controller."""
        tts_path = self.api_client.tts(texte)
        print(f"TTS généré : {tts_path}")
        self.audio_ctrl.play(tts_path)

    def reconnaitre_voix(self):
        """
        Écoute le micro, enregistre, puis transcrit avec l'API_Client.
        Retourne la transcription complète, ou rien si stop_flag est activé.
        """
        import Site_web.ordonnance as ordonnance_py  # pour accéder à stop_flag
        print("Veuillez parler après le bip... (cliquez sur Arrêter pour stopper)")
        if hasattr(ordonnance_py, "stop_flag") and ordonnance_py.stop_flag.is_set():
            ordonnance_py.stop_flag.clear()
            print("Arrêt demandé par le site (avant écoute).")
            return ""
        audio_path = self.audio_ctrl.listen()
        msg = self.api_client.stt(audio_path)
        print(f"Transcription : {msg.content}")
        # Si le flag est activé juste après l'écoute
        if hasattr(ordonnance_py, "stop_flag") and ordonnance_py.stop_flag.is_set():
            ordonnance_py.stop_flag.clear()
            print("Arrêt demandé par le site (après écoute).")
            return msg.content
        # Arrêt vocal classique
        if "c'est tout" in msg.content.lower() or "stop" in msg.content.lower():
            print("Arrêt vocal détecté.")
            return msg.content
        return msg.content

    def generer_ordonnance(self, informations: PatientInfo):
        dossier_ordonnances = os.path.expanduser("~/Desktop/ordonnances")
        os.makedirs(dossier_ordonnances, exist_ok=True)

        if not informations or not informations.patient or not informations.medicaments:
            print("❌ Erreur : Informations incomplètes.")
            return

        for med in informations.medicaments:
            if not med.nom or not med.posologie or not med.duree:
                print(f"❌ Erreur : Données incomplètes pour : {med}")
                return

        print("✅ Informations valides. Génération de l'ordonnance...")

        patient_nom = informations.patient
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
        c.drawString(50, hauteur - 100, f"Patient : {patient_nom}")

        c.setFont("Helvetica-Bold", 15)
        c.drawString(50, hauteur - 220, "Médicaments prescrits :")
        c.setFont("Helvetica", 12)
        y_position = hauteur - 250

        for med in medicaments:
            c.drawString(50, y_position, f"- {med.nom} : {med.posologie} pendant {med.duree}")
            y_position -= 20

        c.drawString(350, y_position - 50, "Signature : ___________")
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
        self.parler("Je suis prêt. Dites toutes les informations pour l'ordonnance, puis dites 'c'est tout' quand vous avez terminé.")
        self.full_transcript = []
        while True:
            user_text = self.reconnaitre_voix()
            if "c'est tout" in user_text.lower():
                break
            self.full_transcript.append({"role": "user", "content": user_text})

        try:
            # Extraction structurée avec parse
            info_patient = self.api_client.parse(
                self.ordo_extraction_prompt + self.full_transcript,
                PatientInfo
            )
            # Génération de l'ordonnance PDF
            self.generer_ordonnance(info_patient)
            self.parler("Ordonnance générée avec succès.")
        except Exception as e:
            print("Erreur lors de l'extraction ou de la génération :", e)
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

    def extraire_infos_ordonnance(self, transcript: str):
        """
        Prend une transcription brute (str) et retourne un PatientInfo structuré.
        """
        messages = self.ordo_extraction_prompt + [{"role": "user", "content": transcript}]
        try:
            info_patient = self.api_client.parse(messages, PatientInfo)
            return info_patient
        except Exception as e:
            print("Erreur extraction infos ordonnance :", e)
            return None

if __name__ == "__main__":
    agent = OrdoAgent()
    print("Veuillez dicter l'ordonnance après le bip.")
    transcript = agent.reconnaitre_voix()
    infos = agent.extraire_infos_ordonnance( transcript)
    if infos:
        print("Patient :", infos.patient)
        for med in infos.medicaments:
            print(f"Médicament : {med.nom}, Posologie : {med.posologie}, Durée : {med.duree}")
        agent.generer_ordonnance(infos)
    else:
        print("Impossible d'extraire les informations de l'ordonnance.")
