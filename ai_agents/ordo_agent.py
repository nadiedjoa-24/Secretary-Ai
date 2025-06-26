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
                    f"Aujourd'hui, nous sommes le {datetime.date.today().strftime('%d/%m/%Y')}.\n\n"

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
        Arrête l'écoute dès que l'utilisateur dit 'c'est tout' ou si stop_flag est activé.
        Retourne la transcription complète.
        """
        import Site_web.ordonnance as ordonnance_py  # pour accéder à stop_flag
        print("Veuillez parler après le bip... (dites 'c'est tout' ou cliquez sur Arrêter pour stopper)")
        full_text = []
        while True:
            # Vérifie le flag d'arrêt externe AVANT d'écouter
            if hasattr(ordonnance_py, "stop_flag") and ordonnance_py.stop_flag.is_set():
                ordonnance_py.stop_flag.clear()
                print("Arrêt demandé par le site.")
                break
            audio_path = self.audio_ctrl._listen()
            # Vérifie le flag d'arrêt externe APRÈS l'écoute (au cas où il a été enclenché pendant l'écoute)
            if hasattr(ordonnance_py, "stop_flag") and ordonnance_py.stop_flag.is_set():
                ordonnance_py.stop_flag.clear()
                print("Arrêt demandé par le site (après écoute).")
                break
            msg = self.api_client.stt(audio_path)
            print(f"Transcription : {msg.content}")
            # Arrêt vocal classique
            if "c'est tout" in msg.content.lower() or "stop" in msg.content.lower():
                break
            full_text.append(msg.content)
        transcript = " ".join(full_text)
        print("Cest fini")
        return transcript

    def generer_ordonnance(self, informations: PatientInfo):
        # Calcule le chemin du dossier 'ordonnances' au même niveau que 'ai_agents'
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # remonte d'un cran depuis ai_agents
        dossier_ordonnances = os.path.join(base_dir, "ordonnances")
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
        return chemin_fichier  # <-- Ajoute ce return

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
        all_text = []
        while True:
            user_text = self.reconnaitre_voix()
            if "c'est tout" in user_text.lower():
                break
            if user_text.strip():
                all_text.append(user_text)
                self.full_transcript.append({"role": "user", "content": user_text})

        # Concatène tous les segments pour une extraction complète
        transcript = " ".join(all_text)
        try:
            info_patient = self.extraire_infos_ordonnance(transcript)
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
        print(f"📝 Transcription à analyser : {transcript}")
        
        messages = self.ordo_extraction_prompt + [{"role": "user", "content": transcript}]
        try:
            # Utilise basic() au lieu de parse() pour voir la réponse brute
            response = self.api_client.basic([Message(role=msg["role"], content=msg["content"]) for msg in messages])
            print(f"🤖 Réponse IA brute : {response.content}")
            
            # Parse manuellement le JSON
            import json
            try:
                json_data = json.loads(response.content)
                print(f"✅ JSON parsé : {json_data}")
                
                # Crée les objets manuellement
                medicaments = []
                for med_data in json_data.get("medicaments", []):
                    medicaments.append(MedicamentInfo(
                        nom=med_data.get("nom", ""),
                        posologie=med_data.get("posologie", ""),
                        duree=med_data.get("durée", med_data.get("duree", ""))  # Gère les deux orthographes
                    ))
                
                info_patient = PatientInfo(
                    patient=json_data.get("patient", ""),
                    medicaments=medicaments
                )
                
                print(f"✅ Objet PatientInfo créé : {info_patient}")
                return info_patient
                
            except json.JSONDecodeError as e:
                print(f"❌ Erreur JSON : {e}")
                print(f"Contenu reçu : {response.content}")
                return None
                
        except Exception as e:
            print(f"❌ Erreur extraction infos ordonnance : {e}")
            return None

    def afficher_confirmation(self, informations: PatientInfo):
        """Affiche les informations extraites pour confirmation"""
        print("\n" + "="*60)
        print("CONFIRMATION DES INFORMATIONS EXTRAITES")
        print("="*60)
        print(f"Patient : {informations.patient}")
        print("\nMédicaments prescrits :")
        
        for i, med in enumerate(informations.medicaments, 1):
            print(f"  {i}. Nom : {med.nom}")
            print(f"     Posologie : {med.posologie}")
            print(f"     Durée : {med.duree}")
            print()
        
        print("="*60)
        print("Veuillez confirmer ces informations en répondant 'oui' ou 'non' à l'oral.")
        print("="*60)

    def reconnaitre_voix_simple(self):
        """Version simplifiée de reconnaissance vocale pour les confirmations"""
        try:
            audio_path = self.audio_ctrl._listen()
            msg = self.api_client.stt(audio_path)
            print(f"Réponse entendue : {msg.content}")
            return msg.content
        except Exception as e:
            print(f"Erreur lors de la reconnaissance vocale : {e}")
            return ""

    def demander_confirmation_orale(self):
        """Demande une confirmation orale et retourne True pour oui, False pour non, ou la correction directement"""
        print("En attente de votre réponse orale...")
        reponse = self.reconnaitre_voix_simple()
        
        if reponse:
            reponse_lower = reponse.lower().strip()
            
            # Vérifie si c'est une correction directe (contient des mots-clés de correction)
            mots_correction = ["il y a", "deux l", "corriger", "modifier", "nom de famille", "prénom", "changer"]
            est_correction = any(mot in reponse_lower for mot in mots_correction)
            
            if est_correction:
                print(f"Correction détectée directement : {reponse}")
                return reponse  # Retourne la correction au lieu de True/False
            elif "oui" in reponse_lower or "yes" in reponse_lower or "ok" in reponse_lower:
                return True
            elif "non" in reponse_lower or "no" in reponse_lower:
                return False
        
        # Si pas de réponse claire, redemander
        print("Je n'ai pas compris. Veuillez dire 'oui' ou 'non'.")
        return self.demander_confirmation_orale()

    def traiter_correction_directe(self, informations: PatientInfo, correction_texte: str):
        """Traite une correction donnée directement lors de la confirmation"""
        print(f"Traitement de la correction : {correction_texte}")
        
        # Utilise le même système que corriger_informations mais avec une seule correction
        correction_prompt = [
            {
                "role": "system",
                "content": (
                    "Vous devez corriger les informations d'une ordonnance selon la correction demandée.\n"
                    "Appliquez EXACTEMENT la correction demandée et retournez le JSON corrigé.\n"
                    "RÈGLES DE CORRECTION :\n"
                    "- Si on dit 'il y a deux L à [nom]', ajoutez un L au nom mentionné\n"
                    "- Si on dit 'le nom est [nouveau_nom]', remplacez par le nouveau nom\n"
                    "- Si on dit 'corriger [ancien] par [nouveau]', remplacez ancien par nouveau\n"
                    "- Si on dit 'modifier [élément]', analysez le contexte pour comprendre la modification\n\n"
                    "Format de réponse JSON STRICT :\n"
                    "{\n"
                    "  \"patient\": \"\",\n"
                    "  \"pathologie\": \"\",\n"
                    "  \"medicaments\": [\n"
                    "    {\"nom\": \"\", \"posologie\": \"\", \"durée\": \"\"}\n"
                    "  ]\n"
                    "}\n"
                )
            },
            {
                "role": "user",
                "content": (
                    f"INFORMATIONS ACTUELLES :\n"
                    f"Patient : {informations.patient}\n"
                    f"Médicaments : "
                    + ", ".join([f"{med.nom} ({med.posologie} pendant {med.duree})" for med in informations.medicaments])
                    + f"\n\nCORRECTION À APPLIQUER :\n{correction_texte}\n\n"
                    + "EXEMPLE : Si on dit 'il y a deux L au nom de famille Olivier', "
                    + "le nom 'Antoine Olivier' doit devenir 'Antoine Ollivier'.\n"
                    + "Appliquez maintenant cette correction et retournez le JSON corrigé."
                )
            }
        ]
        
        try:
            response = self.api_client.basic([Message(role=msg["role"], content=msg["content"]) for msg in correction_prompt])
            print(f"🔧 Réponse correction : {response.content}")
            
            # Parse le JSON corrigé
            import json
            json_data = json.loads(response.content)
            
            # Crée les objets corrigés
            medicaments_corriges = []
            for med_data in json_data.get("medicaments", []):
                medicaments_corriges.append(MedicamentInfo(
                    nom=med_data.get("nom", ""),
                    posologie=med_data.get("posologie", ""),
                    duree=med_data.get("durée", med_data.get("duree", ""))
                ))
            
            nouvelles_infos = PatientInfo(
                patient=json_data.get("patient", ""),
                medicaments=medicaments_corriges
            )
            
            print("✅ Correction appliquée avec succès.")
            return nouvelles_infos
            
        except Exception as e:
            print(f"❌ Erreur lors de la correction : {e}")
            return informations

if __name__ == "__main__":
    agent = OrdoAgent()
    
    while True:  # Boucle principale pour permettre de recommencer
        print("Veuillez dicter l'ordonnance après le bip.")
        transcript = agent.reconnaitre_voix()
        
        print(f"📝 Transcription reçue : '{transcript}'")
        
        infos = agent.extraire_infos_ordonnance(transcript)
        
        # Vérification des informations extraites
        if infos and infos.patient and infos.medicaments:
            # Vérification que tous les médicaments ont les infos complètes
            medicaments_complets = True
            for med in infos.medicaments:
                if not med.nom or not med.posologie or not med.duree:
                    medicaments_complets = False
                    break
            
            if medicaments_complets:
                # Boucle de confirmation et correction
                while True:
                    # Affichage de la confirmation
                    agent.afficher_confirmation(infos)
                    
                    # Demande de confirmation orale
                    confirmation = agent.demander_confirmation_orale()
                    
                    if confirmation == True:
                        print("✅ Informations confirmées. Génération de l'ordonnance...")
                        agent.generer_ordonnance(infos)
                        print("🎉 Ordonnance générée avec succès ! Programme terminé.")
                        exit()
                    elif confirmation == False:
                        print("❌ Veuillez dire les corrections nécessaires.")
                        infos = agent.corriger_informations(infos)
                    elif isinstance(confirmation, str):
                        # C'est une correction directe
                        print("🔧 Correction directe détectée.")
                        infos = agent.traiter_correction_directe(infos, confirmation)
                    # Continue la boucle pour redemander confirmation
            else:
                print("❌ Informations de médicaments incomplètes (posologie ou durée manquante).")
                print("Voulez-vous recommencer la dictée ? (Dites 'oui' pour recommencer ou 'non' pour arrêter)")
                
                reponse = agent.reconnaitre_voix_simple()
                if reponse and ("non" in reponse.lower() or "stop" in reponse.lower() or "arrêt" in reponse.lower()):
                    print("Programme arrêté.")
                    break
                else:
                    print("🔄 Recommençons la dictée...")
                    continue  # Recommence la boucle principale
        else:
            print("❌ Impossible d'extraire les informations de l'ordonnance ou patient manquant.")
            if infos:
                print(f"Patient détecté : '{infos.patient}'")
                print(f"Nombre de médicaments : {len(infos.medicaments) if infos.medicaments else 0}")
            
            print("Voulez-vous recommencer la dictée ? (Dites 'oui' pour recommencer ou 'non' pour arrêter)")
            
            reponse = agent.reconnaitre_voix_simple()
            if reponse and ("non" in reponse.lower() or "stop" in reponse.lower() or "arrêt" in reponse.lower()):
                print("Programme arrêté.")
                break
            else:
                print("🔄 Recommençons la dictée...")
                continue  # Recommence la boucle principale
