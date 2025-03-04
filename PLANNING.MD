```mermaid
gantt
    title Planification ARTISHOW 
    dateFormat  DD-MM-YYYY

    section General
        Définition des formats (planning/rdv/patient)                   :a1, 04-03-2025, 20d
        Création d'un planning                                          :20d
        Créer un format pour un rdv                                     :20d
        Créer un format/BDD l'accès à la patientèle                     :20d 

    section Planner AGENT
        Accès planning                                                  :b1, 04-03-2025, 10d 
        Gestion des horaires d'un médecin pour chaque jour              :30d
        Vérif dispo                                                     :10d 
        Ajout / Supr de rdv                                             :10d 
        Proposition d'horaires (dép rdv)                                :30d

    section Vocal AGENT
        Speech-to-Text                                                  :c1, 04-03-2025, 20d 
        Text-to-Speech                                                  :20d 
        Prise de rdv (dialogue pour remplir rdv)                        :30d 
        Annulation/Déplacement de rdv                                   :30d 


    section Email AGENT
        Ouverture + connexion à une boite mail                          :d1, 04-03-2025, 15d 
        Tri des mails                                                   :20d 
        Résumé des points importants (mails non lus)                    :20d 
        Gestion des annulations et déplacements de rdv                  :30d 


    section Ordonnance AGENT
        définir un format d'ordonnance                                  :e1, 04-03-2025, 20d
        Récupérer les info d'une ordonnance                             : 30d 
        Génerer une ordonnance pdf (sur une base de templates préfaits) :40d 
