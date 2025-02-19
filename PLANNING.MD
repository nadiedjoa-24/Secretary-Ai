```mermaid
gantt
    title Planification ARTISHOW 
    dateFormat  DD/MM/YYYY
    axisFormat  %d/%m/%Y

    section COMMUN 
    Evaluation des taches       :done , 02/02/2025, 18/02/2025
    Répartition des tâches       :active, 18/02/2025, 02/03/2025
    Architecture logiciel        :active,    b1, 18/02/2025, 02/03/2025
    Mise en commun + debbug     : 18/05/2025, 15/06/2025

    section Yanic - Développement logiciel / Managing
    Système de login       :  a2, 02/03/2025, 20/04/2025
    Interface pro (Planning rdv) :    b2, 30/03/2025, 04/05/2025
    Interface pro (Communication avec assistant pour déprogrammation, …) :    b2, 20/04/2025, 18/05/2025
    Interface pro (doss patient sur plann) :    b2, 04/05/2025, 18/05/2025


    section Agshay - Développement logiciel
    Interface patient (Prise de rdv par assistant) :    b1, 02/03/2025, 30/03/2025
    Interface patient (Planning rdv) :    b2, 30/03/2025, 04/05/2025
    Interface patient (Dossier medical) :    b3, 04/05/2025, 18/05/2025
    

    section Antoine - Assistant de gestion boîte mail
    Login + gestion boite mail dans un script :     c1, 02/03/2025, 23/03/2025
    Assistant IA pour classer les mails:    c2, 23/03/2025, 06/04/2025
    Prise de rdv + annulation par mail:     c3, 06/04/2025, 04/05/2025
    Résumé boite mail pour jour donné : c4, 04/05/2025, 18/05/2025


    section Théophile - Assistant vocal et gestion de planning
    Création structure  Planning  : 02/03/2025, 16/03/2025
    Interactions planning : 16/03/2025, 06/04/2025
    Assistant gestion intelligente du planning (en comm avec assist vocal): 06/04/2025, 18/05/2025


    section Yifan - Assistant vocal et gestion de planning
    Speech to text  + text to speech : 02/03/2025, 16/03/2025
    Connexion telephonique avec twilio : 16/03/2025, 06/04/2025
    Assistant vocal + comm avec assistant planning : 06/04/2025, 18/05/2025