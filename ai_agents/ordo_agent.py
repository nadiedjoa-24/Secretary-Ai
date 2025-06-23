import os
import datetime
from openai import OpenAI
import speech_recognition as sr
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from typing import List
from pydantic import BaseModel
import pyttsx3  # Synthèse vocale

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
        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.medecin_info = "Dr Jean Martin"
        self.voix = pyttsx3.init()
        self.voix.setProperty('rate', 150)

    def parler(self, texte: str):
        self.voix.say(texte)
        self.voix.runAndWait()

    def reconnaitre_voix(self):
        recognizer = sr.Recognizer()
        with sr.Microphone() as source:
            print("🎤 Parlez maintenant...")
            recognizer.pause_threshold = 2.0
            recognizer.energy_threshold = 300
            recognizer.dynamic_energy_threshold = False
            recognizer.adjust_for_ambient_noise(source, duration=1)

            try:
                audio = recognizer.listen(source, timeout=10)
                texte = recognizer.recognize_google(audio, language="fr-FR")
                print(f"📝 Requête vocale reconnue : {texte}")
                return texte
            except sr.UnknownValueError:
                print("❌ Erreur : Impossible de reconnaître la voix.")
                return None
            except sr.RequestError:
                print("❌ Erreur : Problème avec le service de reconnaissance vocale.")
                return None
            except sr.WaitTimeoutError:
                print("⏱️ Aucun son détecté.")
                return None

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
        self.parler("Commençons la création d'une ordonnance.")
        
        self.parler("Quel est le nom du patient ?")
        nom_patient = self.reconnaitre_voix()
        if not nom_patient:
            self.parler("Je n'ai pas compris le nom du patient. Abandon.")
            return

        medicaments = []
        while True:
            self.parler("Nom du médicament ?")
            nom_med = self.reconnaitre_voix()
            if nom_med and "c'est tout" in nom_med.lower():
                break
            if not nom_med:
                self.parler("Je n'ai pas compris. Recommençons ce médicament.")
                continue

            self.parler("Quelle quantité ?")
            quantite = self.reconnaitre_voix()
            if not quantite:
                self.parler("Quantité non comprise. Recommençons ce médicament.")
                continue

            self.parler("Pendant combien de jours ?")
            duree = self.reconnaitre_voix()
            if not duree:
                self.parler("Durée non comprise. Recommençons ce médicament.")
                continue

            medicaments.append(MedicamentInfo(nom=nom_med, quantite=quantite, duree=duree))
            self.parler("Médicament ajouté. Dites 'c'est tout' si vous avez terminé.")

        if not medicaments:
            self.parler("Aucun médicament ajouté. Ordonnance annulée.")
            return

        info_patient = PatientInfo(patient=nom_patient, medecin=self.medecin_info, medicaments=medicaments)
        self.generer_ordonnance(info_patient)
        self.parler("Ordonnance générée avec succès.")

if __name__ == "__main__":
    agent = OrdoAgent()
    agent.remplir_ordonnance_par_questions()
