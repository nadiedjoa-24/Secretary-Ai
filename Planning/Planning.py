from datetime import datetime, timedelta

class Personne:
    def __init__(self, nom, email=None, telephone=None):
        self.nom = nom
        self.email = email
        self.telephone = telephone

class RendezVous:
    def __init__(self, titre, date_heure, duree_minutes, Practicien, participant=None, description=None):
        self.titre = titre
        self.date_heure = date_heure
        self.duree_minutes = duree_minutes
        self.Practicien = Practicien
        self.participant = participant
        self.description = description

class Planning:
    def __init__(self):
        self.rendez_vous = []

    def ajouter_rdv(self, rdv: RendezVous) -> bool:
        for existing_rdv in self.rendez_vous:
            if existing_rdv.date_heure == rdv.date_heure and existing_rdv.Practicien == rdv.Practicien:
                return False
        self.rendez_vous.append(rdv)
        return True

    def trouver_creneaux_disponibles(self, debut: datetime, fin: datetime, duree_minutes: int):
        creneaux_disponibles = []
        current_time = debut

        self.rendez_vous.sort(key=lambda rdv: rdv.date_heure)

        for rdv in self.rendez_vous:
            if current_time + timedelta(minutes=duree_minutes) <= rdv.date_heure:
                creneaux_disponibles.append((current_time, rdv.date_heure))
            current_time = max(current_time, rdv.date_heure + timedelta(minutes=rdv.duree_minutes))

        if current_time + timedelta(minutes=duree_minutes) <= fin:
            creneaux_disponibles.append((current_time, fin))

        return creneaux_disponibles

    def afficher_planning(self):
        if not self.rendez_vous:
            print("Aucun rendez-vous dans le planning.")
            return

        print("Planning des rendez-vous :")
        for rdv in sorted(self.rendez_vous, key=lambda r: r.date_heure):
            print(f"- {rdv.date_heure.strftime('%A %d %B %Y à %H:%M')} : {rdv.titre} avec {rdv.Practicien}")

# Création du planning
planning = Planning()

# Création d'une personne
personne = Personne(nom="Antoine Ollivier", email="alice@example.com")
personne2 = Personne(nom="Cédric Ollivier", email="CedricOllivier@example.com")

# Création d'un rendez-vous
rdv = RendezVous(
    titre="Consultation médicale",
    date_heure=datetime(2025, 4, 20, 15, 30),
    duree_minutes=30,
    Practicien="Dr Martin",
    participant=personne,
    description="Suivi annuel"
)
rdv2 = RendezVous(
    titre="Consultation médicale",
    date_heure=datetime(2025, 4, 20, 15, 30),
    duree_minutes=30,
    Practicien="Cabinet du Dr Martin",
    participant=personne2,
    description="Suivi annuel"
)


# Ajout au planning


# Affichage
planning.afficher_planning()

