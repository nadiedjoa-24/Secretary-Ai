# Suivi de projet

## Vendredi 14 février 2025
- Réflexion collective :
  - Définition des questions à poser aux médecins à contacter
  - Brainstorming sur les tâches potentielles à réaliser

## Mardi 18 février 2025
- Organisation des tâches :
  - Attribution des rôles et responsabilités :

  | Tâche                  | Responsable(s)                       |
  |------------------------|--------------------------------------|
  | Envoi des mails        | Antoine Ollivier                     |
  | Gestion du planning    | Théophile Nadiedjoa & Yifan Wang     |
  | Reconnaissance vocale  | Théophile Nadiedjoa & Yifan Wang     |
  | Développement appli    | Yannic & Agshay                      |

## Mardi 25 février 2025
- Entretien avec une secrétaire :
  - Rencontre peu productive
  - La personne s'est montrée réticente.
  - Analyse : Mauvais choix d'interlocuteur – une secrétaire pourrait percevoir notre projet comme une menace pour son emploi alors qu'il vise à l'aider en automatisant les tâches répétitives

## Mardi 4 mars 2025
- (Yanic) : Création d'un planning pour les rdv avec des données spécifiées
- (Yanic & Agshay) : Création d'un AI_Agent qui donne des ordonnances
- (Yifan & Théophile) : Début de la mise en place de Speech-to-text

## Mardi 18 mars 2025
- (Yifan) : Implémentation de LLaMA sur GPU
- (Antoine) : Création d'un premier modèle text-to-speech en utilisant pyttsx3 ou gtts

## Mardi 25 mars 2025
- (Yifan) : Implémentation de Whispers pour la voix de l'IA
- (Yanic) : Premier "speech-to-speech" fonctionnel
- (Antoine) : Mise en place d'un second script de speech-to-text
- (Agshay) : Tests d'intégration des fonctionnalités vocales dans l'application
- (Théophile) : Vérification speech-to-speech et Whispers

## Mardi 1er avril 2025
- (Yifan) : Intégration de Mistral avec les modules déjà implémentés
- (Yanic) : Amélioration du système de prise de rendez-vous intelligent
- (Théophile) : Tests de reconnaissance vocale avec différents accents
- (Agshay) : Débogage de l’AI_Agent sur certaines requêtes médicales
- (Antoine) : Documentation des modules de speech-to-text et TTS

## Mardi 8 avril 2025
- (Théophile) : Implémentation d'un programme text_to_speech avec plusieurs voix avec Whispers
- (Théophile) : Test programme text_to_speech avec Elevenlabs
- (Yifan) : Mise en place de Mistral pour répondre aux clients + documentation API à distance
- (Agshay) : Test de speech_to_text sur GPU avec Mistral et Whispers
- (Yanic) : Mise en place d'un script permettant de mettre en serveur un bot AI sur le GPU à distance

## Mardi 15 avril 2025
- (Yifan) : Planning + tentative de relier les scripts avec le bot à distance
- (Théophile) : Optimisation du pipeline vocal (du texte à la réponse audio)
- (Agshay) : Merge des 2 branches (master/main) + Résolution conflits + arrangement du Git
- (Antoine) : Préparation d'une présentation intermédiaire du projet
- (Yanic) : Déploiement du bot sur serveur distant

## Mercredi 16 avril 2025
- (Yifan) : Configuration finale de l’environnement distant + tests de latence
- (Théophile) : Documentation technique pour la partie vocale
- (Agshay) : Test utilisateur
- (Yanic) : Rédaction de l'état de l'art pour tout ce qui est en rapport avec les voix, whispers et tout
- (Antoine) : Création d’un support de communication pour la suite

## Lundi 5 mai 2025
- (Yifan) : Boîte mail, bot qui répond aux mails
- (Yifan, Théophile, Agshay, Yanic et Antoine) : Discussion sur les enjeux sociaux et/ou environnementaux
- (Théophile, Antoine) : Comparaison des performances en local sur GPU vs en global avec l'API d'OpenAI

## Lundi 12 mai 2025
- (Yifan, Yanic, Antoine, Agshay, Théophile) : Élaboration et rédaction du rapport sur les enjeux sociaux et/ou environnementaux
- (Yifan, Yanic, Antoine, Agshay, Théophile) : Discussion, état des lieux et attribution des tâches à finaliser avant la démo du 19 mai

## Lundi 19 mai 2025
- (Yanic) : Agent mail qui trie les mails dans différents dossiers selon le contenu
- (Yifan) : Même agent mail qui résume rapidement le contenu d'un mail
- (Agshay) : Agent ordonnance optimisé : produit des ordonnances par la voix
- (Antoine et Théophile) : Finetuning de la voix
- (Tous les membres) : Présentation du projet et échanges avec l’auditoire
- (Yifan et Yanic) : Implémentation sur les GPU mais bugs présents

## Lundi 26 mai 2025
- (Tous) : Discussion avec l'encadrant
- (Antoine) : Élaboration de la page spéciale mail
- (Agshay) : Élaboration de la page spéciale ordonnances
- (Yanic) : Redéfinition de la méthode utilisée pour l'ordonnance + optimisation du planning
- (Théophile) : Finetuning de la voix
- (Yifan) : Mise en place d'un site web pour le projet

## Lundi 2 juin 2025
- (Yanic) : Finetuning de la voix, utilisation d'une voix plus naturelle pour les TTS/STT
- (Théophile) : Tests comparatifs entre plusieurs APIs de voix (Google, ElevenLabs, OpenAI)
- (Antoine) : Début de l'intégration d'un résumé automatique dans l'interface mail
- (Agshay) : Refactoring de l’agent ordonnance pour intégrer des règles médicales conditionnelles simples
- (Yifan) : Setup du backend Flask + liaison avec la base de données MongoDB (sans authentification par token)

## Lundi 9 juin 2025
- (Agshay) : Détection automatique des médicaments, posologie, forme galénique et fréquence dans les requêtes médicales
- (Antoine) : Mise en place de la détection automatique des mots-clés importants dans les mails pour trier les priorités
- (Yifan) : Finalisation du backend Flask avec structuration du code pour héberger les différentes fonctionnalités

## Mercredi 11 juin 2025
- (Agshay, Antoine, Yifan) : Conception de l’affiche de présentation du projet sur Canva (graphisme, contenu, mise en page)
- (Théophile & Yanic) : Tests croisés des fonctionnalités principales (mail handler, ordonnance vocale, site Flask)
- (Antoine) : Ajustement de la mise en page de l'interface web (visuels, couleurs, ergonomie)

## Vendredi 13 juin 2025
- (Yanic et Yifan) : Ajouts sur le site web de boutons : tri automatique + résumé des mails
- (Théophile, Antoine) : Agent planificateur mis sur le site, mais quelques fonctionnalités sont à rajouter
- (Agshay) : Parsing des données pour l'ordonnance afin d'être plus concis

## Mardi 17 juin 2025
- (Agshay, Antoine et Yifan) : Finalisation de l'affiche

## Lundi 23 juin 2025
- (Agshay) : Conception de l'interface pour l'agent ordonnance
- (Yifan) : Conception du site web
- (Théophile, Yanic) : Nettoyage du git 
- (Théophile) : Optimisation du de l'agent vocal pour la génération d'ordonnance

## Mardi 24 juin 2025
-(Yanic) : Finalisation de l'agent Planning
-(Agshay, Antoine) : Création de l'interface Accueil du projet 
-(Yifan, Théophile) : Finalisation de l'agent vocal pour la génération d'ordonnance  

## Mercredi 25 juin 2025
-(Yifan, Antoine) : Mise en lien des interfaces agent et de l'interface Accueil
-(Théophile) : Optimisation de l'agent vocal pour la génération d'ordonnance
-(Yanic) : Finalisation de l'agent Planning et conception de l'interface pour l'agent Planning
-(Agshay) : Amélioration visuelle de l'interface 