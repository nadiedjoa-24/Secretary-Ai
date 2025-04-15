import os
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generer_ordonnance():
    # Définir le dossier de sauvegarde
    dossier_ordonnances = os.path.expanduser("~/Desktop/ordonnances")  # Sur le Bureau
    os.makedirs(dossier_ordonnances, exist_ok=True)  # Crée le dossier s'il n'existe pas
    
    # Demander les informations du patient
    patient_nom = input("Nom du patient : ")
    medecin_nom = input("Nom du médecin : ")
    
    # Liste des médicaments
    medicaments = []
    while True:
        nom_medicament = input("Nom du médicament (ou 'fin' pour terminer) : ")
        if nom_medicament.lower() == 'fin':
            break
        quantite = input("Quantité : ")
        duree = input("Durée du traitement (en jours) : ")
        medicaments.append((nom_medicament, quantite, duree))
    
    # Définir le fichier PDF
    fichier_nom = f"ordonnance_{patient_nom.replace(' ', '_')}.pdf"
    chemin_fichier = os.path.join(dossier_ordonnances, fichier_nom)
    
    # Création du PDF
    c = canvas.Canvas(chemin_fichier, pagesize=A4)
    largeur, hauteur = A4

    centre_info = [
    "Centre Médical Saint Jean",
    "23 rue des Lilas, Yerres 91330",
    "Tél : 01 23 45 67 89",
    "Dentiste, Médecine Générale, Kinésithérapeute",
]

    #Position du texte (en haut à droite)
    x_position = 330  # À ajuster selon la largeur de la page
    y_position = 800  # Position verticale (en haut de la page)

    # Affichage des informations en haut à droite
    for i, line in enumerate(centre_info):
        c.drawString(x_position, y_position - i*15, line)

    c.setFont("Helvetica-Bold", 20)
    c.drawString(50, hauteur - 50, "ORDONNANCE MÉDICALE")
    
    c.setFont("Helvetica", 12)
    date_ajd = datetime.date.today().strftime("%d/%m/%Y")
    c.drawString(50, hauteur - 80, f"Date : {date_ajd}")
    c.drawString(50, hauteur - 100, f"Médecin : Dr {medecin_nom}")
    c.drawString(50, hauteur - 120, f"Patient : {patient_nom}")
    
    c.setFont("Helvetica-Bold", 15)
    c.drawString(50, hauteur - 220, "Médicaments prescrits :")
    c.setFont("Helvetica", 12)
    y_position = hauteur - 250
    
    for med in medicaments:
        c.drawString(50, y_position, f"- {med[0]} : {med[1]} fois par jour, pendant {med[2]} jours")
        y_position -= 20
    
    c.drawString(350, y_position - 550, "\nSignature du médecin : ___________")
    
    c.save()
    print(f"Ordonnance générée avec succès : {chemin_fichier}")

generer_ordonnance()