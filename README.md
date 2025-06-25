# ARTISHOW - SECRETARYAI

Le projet **secretaryAI** a pour objectif de développer des outils basés sur l’intelligence artificielle afin d’optimiser les tâches répétitives d’une secrétaire médicale.

Chaque tâche sera prise en charge par un agent d’intelligence artificielle, composé de deux parties : 
- un contrôleur technique chargé de manipuler les données, 
- et une partie intelligente s’appuyant soit sur une API externe (OpenAI, Mistral, etc.), soit sur une solution locale (modèles HuggingFace via `transformers`, accompagnés d’une interface réseau).

## Client intelligent

Pour garantir une bonne interopérabilité, chaque client (API ou local) devra implémenter une interface commune définie dans `BaseAIModel`. Les fonctionnalités à implémenter sont les suivantes :

- **Basic** : requête simple pour un traitement rapide avec une bonne fiabilité.
- **Reflexion** : requête plus complexe offrant une meilleure compréhension du problème, mais avec un temps de traitement plus long.
- **Parsing** : extraction de données à partir d’une conversation, selon un modèle de données prédéfini.
- **STT (Speech-to-Text)** : conversion d’un fichier audio (.wav, .mp3) en texte.
- **TTS (Text-to-Speech)** : génération d’un fichier audio fluide et naturel à partir d’un prompt textuel.

 ```python
class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str

class BaseAIModel(ABC):
    
    @abstractmethod
    def basic(self, messages: List[Message]) -> Message:
        pass

    @abstractmethod
    def reflexion(self, messages: List[Message]) -> Message:
        pass

    @abstractmethod
    def parse(self, messages: List[Message], data_model: BaseModel) -> BaseModel:
        pass

    @abstractmethod
    def tts(self, text: str, output_path: str) -> str:
        pass
    
    @abstractmethod
    def stt(self, audio_path: str) -> Message:
        pass


 ```

### 1. API

La classe `API_Client` implémente l’interface `BaseAIModel` en s’appuyant sur une API existante. Pour notre projet, nous avons choisi l’API d’OpenAI.

- **Avantages** : Solution complète, très bien documentée et particulièrement performante.  
- **Inconvénients** : La sécurité des données n’est pas totalement garantie une fois celles-ci envoyées sur les serveurs de l’API. De plus, les requêtes sont payantes, ce qui peut engendrer un coût.

Nous avons estimé le coût moyen d’utilisation dans un scénario réaliste. Dans notre cas, 100 requêtes représentent environ 1 centime d’euro. En supposant qu’un cabinet médical effectue environ 200 actions par jour, cela reviendrait à environ 50 centimes par mois — un coût négligeable.  
Par ailleurs, une solution basée sur une API nécessite généralement moins de maintenance technique.

### 2. LOCAL

La classe `API_Local` implémente également `BaseAIModel`, mais en utilisant le package `transformers` de HuggingFace. L’inférence des modèles est exécutée localement sur des GPU via CUDA, avec une interface réseau permettant la communication entre les agents et les ressources de calcul.

- **Avantages** : Meilleur contrôle des paramètres des modèles, ce qui permet une adaptation fine à chaque usage. La sécurité est renforcée grâce à une maîtrise complète des données.  
- **Inconvénients** : Mise en œuvre plus complexe, nécessitant un effort de maintenance accru. De plus, l’inférence locale requiert du matériel dédié, comme des GPU.

D’un point de vue financier, cette solution garantit la confidentialité des données des patients, mais elle engendre un coût plus élevé, estimé entre 30 et 40 euros par mois (incluant la maintenance, l’infrastructure et le matériel nécessaire).





## Reprogrammation de rendez-vous

La gestion de la reprogrammation des rendez-vous repose sur deux composants principaux :

- **`PlannerController`** : Ce module permet de créer et gérer un planning structuré au format JSON. Il inclut plusieurs fonctionnalités :
  - ajout et suppression de rendez-vous selon un format temporel prédéfini,
  - récupération des rendez-vous pour une période donnée à partir d’une date de référence,
  - détection automatique des créneaux horaires disponibles,
  - persistance des données dans un fichier JSON local, assurant la sauvegarde et la traçabilité des actions.

- **`planning_agent`** : Il s’agit d’un agent conversationnel intelligent, reposant sur une API externe. Il interagit directement avec le `PlannerController` pour proposer une interface naturelle permettant de reprogrammer un rendez-vous. La méthode principale `reschedule` permet à un utilisateur (secrétaire ou patient) de reformuler une demande de rendez-vous, qui sera analysée, interprétée, puis exécutée de manière autonome.

## Gestion automatique et simplifiée d'une boîte mail

Pour faciliter la gestion quotidienne d’une boîte mail professionnelle, deux modules interagissent ensemble :

- **`mail_handler`** : Ce module exploite les protocoles **IMAP** (réception) et **SMTP** (envoi) grâce aux bibliothèques Python `imaplib` et `smtplib`. Il est connecté à une boîte Gmail dédiée au projet et permet de :
  - lire les e-mails entrants non lus,
  - extraire les pièces jointes,
  - envoyer automatiquement des réponses ou des notifications.

- **`Mail_agent`** : Cet agent IA permet :
  - de générer un résumé automatique de tous les e-mails non lus,
  - de trier les courriels selon leur contenu, expéditeur ou urgence,
  - de proposer des réponses types ou des actions à entreprendre en fonction du contexte.

## Génération d’ordonnance automatique

Un dernier agent vise à assister les médecins dans la création rapide et fiable d’ordonnances médicales :

- **`ordo_agent`** : Ce composant permet de :
  - générer un document PDF à partir d’un modèle personnalisable aux couleurs et coordonnées du cabinet,
  - enregistrer les informations du médecin (nom, spécialité, numéro RPPS, etc.),
  - parser une requête vocale ou textuelle contenant les médicaments prescrits ainsi que les données du patient (nom, prénom, posologie, durée...),
  - produire une ordonnance finalisée, prête à être imprimée ou envoyée.

Cet outil vise à améliorer la fluidité de la consultation, tout en assurant la rigueur et la lisibilité des prescriptions.

