import os
import datetime
from openai import OpenAI
import speech_recognition as sr
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from typing import List, Dict
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
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY2")
        self.openai_client = OpenAI(api_key = self.openai_api_key)
        self.ecoute_active = False  
        self.medecin_info = "Dr Jean Martin"  

    def activer_ecoute(self):
        """
        Active l'écoute continue jusqu'à désactivation manuelle.
        """
        self.ecoute_active = True
        print("🎤 Mode d'écoute activé. Dites 'stop' pour arrêter.")

        while self.ecoute_active:
            texte = self.reconnaitre_voix()
            if texte and "stop" in texte.lower():
                print("🛑 Arrêt de l'écoute.")
                self.ecoute_active = False
                break
            elif texte:
                self.creer_ordonnance_depuis_requete(texte, mode="texte")

    def extraire_infos(self, requete):
        """
        Utilise l'API OpenAI pour extraire les informations nécessaires, avec le médecin prérempli.
        """
        try:
            response = self.openai_client.beta.chat.completions.parse(
                model="gpt-4o",
                messages=[{"role": "system", "content": f"Tu es un assistant médical. Extrait les informations sous forme d'un objet structuré contenant uniquement les détails du patient et la prescription. Le médecin est {self.medecin_info}."},
                          {"role": "user", "content": requete}],
                response_format=PatientInfo
            ).choices[0].message.parsed

            patient_info = response
            patient_info.medecin = self.medecin_info 

            print("Réponse parsée de l'API :", patient_info)
            return patient_info

        except Exception as e:
            print(f"Erreur lors du parsing OpenAI : {e}")
            return None

    def reconnaitre_voix(self):
        """
        Utilise speech_recognition pour capturer une requête vocale et la convertir en texte.
        Ajuste les paramètres pour éviter l'arrêt prématuré.
        """
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("🎤 Parlez maintenant...")

            recognizer.pause_threshold = 2.0  # Temps max de silence avant arrêt
            recognizer.energy_threshold = 300  # Sensibilité au bruit
            recognizer.dynamic_energy_threshold = False  

            recognizer.adjust_for_ambient_noise(source, duration=1)
            audio = recognizer.listen(source, timeout=10)

        try:
            texte = recognizer.recognize_google(audio, language="fr-FR")
            print(f"📝 Requête vocale reconnue : {texte}")
            return texte
        except sr.UnknownValueError:
            print("❌ Erreur : Impossible de reconnaître la voix.")
            return None
        except sr.RequestError:
            print("❌ Erreur : Problème avec le service de reconnaissance vocale.")
            return None

    def generer_ordonnance(self, informations: PatientInfo):
        """
        Génère un fichier PDF d'ordonnance à partir des informations extraites.
        """
        dossier_ordonnances = os.path.expanduser("~/Desktop/ordonnances")
        os.makedirs(dossier_ordonnances, exist_ok=True)

        if not informations:
            print("❌ Erreur : Aucune information extraite de la requête.")
            return

        if not informations.patient or not informations.medecin or not informations.medicaments:
            print("❌ Erreur : Les informations du patient, du médecin ou de la prescription sont incomplètes.")
            return

        for med in informations.medicaments:
            if not med.nom or not med.quantite or not med.duree:
                print(f"❌ Erreur : Informations incomplètes pour le médicament : {med}")
                return

        print("✅ Toutes les informations sont complètes. Génération de l'ordonnance...")

        data = informations 
        patient_nom = data.patient
        medecin_nom = data.medecin
        medicaments = data.medicaments

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
            c.drawString(50, y_position, f"- {med.nom} : {med.quantite} fois par jour, pendant {med.duree} jours")
            y_position -= 20

        c.drawString(350, y_position - 50, "Signature du médecin : ___________")

        c.save()
        print(f"Ordonnance générée avec succès : {chemin_fichier}")

    def creer_ordonnance_depuis_requete(self, requete=None, mode="texte"):
        """
        Créé une ordonnance à partir d'une requête en texte ou en vocal.
        """
        if mode == "vocal":
            requete = self.reconnaitre_voix()
            if not requete:
                return
        
        informations = self.extraire_infos(requete)
        self.generer_ordonnance(informations)



if __name__ == "__main__":
    agent = OrdoAgent()
    agent.activer_ecoute()