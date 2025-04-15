from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel
from Planning import Planning, RendezVous, Personne
import os

app = FastAPI()

# Simuler le planning
planning = Planning()

# Servir des fichiers statiques (comme index.html)
app.mount("/static", StaticFiles(directory=os.path.dirname(__file__)), name="static")

# Modèles pour l'API
class PersonneAPI(BaseModel):
    nom: str
    email: str
    telephone: str

class RendezVousAPI(BaseModel):
    titre: str
    date_heure: datetime
    duree_minutes: int
    Practicien: str
    participant: PersonneAPI
    description: str

@app.get("/planning", response_model=List[dict])
def get_planning():
    return [
        {
            "titre": rdv.titre,
            "date_heure": rdv.date_heure.strftime("%A %d %B %Y à %H:%M"),
            "duree_minutes": rdv.duree_minutes,
            "Practicien": rdv.Practicien,
            "participant": {
                "nom": rdv.participant.nom,
                "email": rdv.participant.email,
                "telephone": rdv.participant.telephone,
            } if rdv.participant else None,
            "description": rdv.description,
        }
        for rdv in planning.rendez_vous
    ]

@app.get("/creneaux-disponibles")
def get_creneaux_disponibles(debut: str, fin: str, duree_minutes: int):
    debut_datetime = datetime.fromisoformat(debut)
    fin_datetime = datetime.fromisoformat(fin)
    creneaux = planning.trouver_creneaux_disponibles(debut_datetime, fin_datetime, duree_minutes)
    return [{"debut": c[0], "fin": c[1]} for c in creneaux]

@app.post("/planning")
def add_rendezvous(rdv: RendezVousAPI):
    # Convertir les données en objet RendezVous
    participant = Personne(
        nom=rdv.participant.nom,
        email=rdv.participant.email,
        telephone=rdv.participant.telephone,
    )
    nouveau_rdv = RendezVous(
        titre=rdv.titre,
        date_heure=rdv.date_heure,
        duree_minutes=rdv.duree_minutes,
        Practicien=rdv.Practicien,
        participant=participant,
        description=rdv.description,
    )

    # Tenter d'ajouter le rendez-vous
    if planning.ajouter_rdv(nouveau_rdv):
        return {"message": "Rendez-vous ajouté avec succès"}
    else:
        return {"message": "Rendez-vous non disponible : le créneau est déjà pris pour ce praticien"}

@app.post("/demande-rdv")
def demande_rdv(client_data: dict):
    # Extraire les données du client
    nom = client_data.get("nom", "Client")
    email = client_data.get("email", "inconnu@example.com")
    telephone = client_data.get("telephone", "0000000000")
    duree_minutes = client_data.get("duree_minutes", 30)

    # Définir une plage horaire par défaut (par exemple, aujourd'hui + 7 jours)
    debut = datetime.now()
    fin = debut + timedelta(days=7)

    # Trouver les créneaux disponibles
    creneaux = planning.trouver_creneaux_disponibles(debut, fin, duree_minutes)

    if creneaux:
        # Retourner les créneaux disponibles
        return {
            "message": f"Bonjour {nom}, voici les créneaux disponibles :",
            "creneaux": [
                {"debut": c[0].strftime("%A %d %B %Y à %H:%M"), "fin": c[1].strftime("%A %d %B %Y à %H:%M")}
                for c in creneaux
            ],
        }
    else:
        return {"message": f"Désolé {nom}, aucun créneau disponible dans les 7 prochains jours."}

@app.get("/", response_class=HTMLResponse)
def serve_html():
    with open("index.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read())