# **Documentation du Projet de Gestion de Planning**

## **Description**
Ce projet permet de gérer un planning de rendez-vous via une API REST et une interface utilisateur. Les fonctionnalités incluent :
- Ajouter des rendez-vous.
- Trouver des créneaux disponibles.
- Proposer des créneaux via une chatbox connectée à une IA.
- Afficher les rendez-vous et les créneaux disponibles dans une interface web.

---

## **Structure des fichiers**
1. **`Planning.py`** : Contient la logique principale pour gérer les rendez-vous et les créneaux.
2. **`api.py`** : Expose une API REST pour interagir avec le planning et inclut une route pour la chatbox.
3. **`index.html`** : Interface utilisateur pour afficher les rendez-vous, les créneaux disponibles, et interagir avec la chatbox.

---

## **Dépendances**
Avant de commencer, installez les dépendances nécessaires avec `pip` :

pip install fastapi uvicorn openai


---

## **Fichier : `Planning.py`**

### **Description**
Ce fichier contient la logique principale pour gérer les rendez-vous et les créneaux.

### **Classes et Méthodes**

#### 1. Classe `Personne`
Représente une personne participant à un rendez-vous.

**Attributs :**
- `nom` (str) : Nom de la personne.
- `email` (str, optionnel) : Email de la personne.
- `telephone` (str, optionnel) : Téléphone de la personne.

#### 2. Classe `RendezVous`
Représente un rendez-vous.

**Attributs :**
- `titre` (str) : Titre du rendez-vous.
- `date_heure` (datetime) : Date et heure du rendez-vous.
- `duree_minutes` (int) : Durée du rendez-vous en minutes.
- `Practicien` (str, optionnel) : Nom du praticien.
- `participant` (Personne, optionnel) : Participant au rendez-vous.
- `description` (str, optionnel) : Description du rendez-vous.

#### 3. Classe `Planning`
Gère la liste des rendez-vous et les créneaux disponibles.

**Méthodes :**
- `ajouter_rdv(rdv: RendezVous)` :  
  Ajoute un rendez-vous au planning.  
  Vérifie les conflits de créneaux pour le même praticien.

- `afficher_planning()` :  
  Affiche tous les rendez-vous triés par date.

- `trouver_creneaux_disponibles(debut: datetime, fin: datetime, duree_minutes: int)` :  
  Retourne une liste de créneaux disponibles entre deux dates.

---

## **Fichier : `api.py`**

### **Description**
Ce fichier expose une API REST pour interagir avec le planning et inclut une route pour la chatbox.

### **Routes**

#### 1. `POST /planning`
**Description** : Ajoute un rendez-vous au planning.  
**Requête :**
{
    "titre": "Consultation médicale",
    "date_heure": "2025-04-20T15:30:00",
    "duree_minutes": 30,
    "Practicien": "Dr Martin",
    "participant": {
        "nom": "Jean Dupont",
        "email": "jean.dupont@example.com",
        "telephone": "0123456789"
    },
    "description": "Suivi annuel"
}
**Réponse :**
- Succès : {"message": "Rendez-vous ajouté avec succès"}
- Échec : {"message": "Rendez-vous non disponible : le créneau est déjà pris pour ce praticien"}

#### 2. `POST /demande-rdv`
**Description** : Propose des créneaux disponibles à un client.  
**Requête :**
{
    "nom": "Jean Dupont",
    "email": "jean.dupont@example.com",
    "telephone": "0123456789",
    "duree_minutes": 30
}
**Réponse :**
{
    "message": "Bonjour Jean Dupont, voici les créneaux disponibles :",
    "creneaux": [
        {"debut": "Mercredi 20 Avril 2025 à 10:00", "fin": "Mercredi 20 Avril 2025 à 10:30"},
        {"debut": "Mercredi 20 Avril 2025 à 11:00", "fin": "Mercredi 20 Avril 2025 à 11:30"}
    ]
}
**Si aucun créneau n'est disponible :**
{
    "message": "Désolé Jean Dupont, aucun créneau disponible dans les 7 prochains jours."
}

}

#### 3. `GET /`
**Description** : Sert le fichier HTML pour l'interface utilisateur.

---

## **Comment utiliser le projet**

### 1. Lancer l'API
Exécutez la commande suivante pour démarrer le serveur FastAPI :
uvicorn api:app --reload

### 2. Accéder à l'interface utilisateur
Ouvrez le fichier `index.html` dans un navigateur pour afficher les rendez-vous, les créneaux disponibles, et interagir avec la chatbox.

### 3. Tester les routes
- Ajouter un rendez-vous : Utilisez la route POST /planning.
- Demander des créneaux disponibles : Utilisez la route POST /demande-rdv.
---

## **Exemple de flux complet**

1. Demander des créneaux disponibles  
   Envoyez une requête à /demande-rdv.  
   L'API retourne une liste de créneaux disponibles.

2. Choisir un créneau  
   Le client choisit un créneau parmi ceux proposés.

3. Confirmer le rendez-vous  
   Envoyez une requête à /planning pour ajouter le rendez-vous.

---

## **Améliorations possibles**
- Ajouter une gestion des utilisateurs avec authentification.
- Intégrer un système de notification (email ou SMS) pour confirmer les rendez-vous.
- Améliorer l'interface utilisateur avec des frameworks comme React ou Vue.js.

