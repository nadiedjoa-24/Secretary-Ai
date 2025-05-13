# Modèles Texte → Langage Naturel (Text-to-Speech expressif)

## OpenAI

### TTS-1
- Synthèse vocale expressive.
- Supporte émotions, intonation naturelle, pauses intelligentes.
- Utilisé dans ChatGPT Voice.
- Temps réel, très fluide, mais fermé.

### gpt-o4-mini-TTS
- Variante légère intégrée dans les agents vocaux GPT.
- Optimisé pour faible latence, bonne expressivité.

### Whisper-TTS (prototype interne)
- Variante exploratoire de Whisper orientée génération vocale (non publique).
- Possibilité de conversion texte-parole dans une boucle interactive.


## ElevenLabs

### Prime Voice AI
- Synthèse vocale hyper-réaliste.
- Clonage de voix avec émotion, accent et prosodie.
- Usage : narration, jeux vidéo, accessibilité.
- API complète avec contrôle SSML-like.

## Microsoft

### Azure Neural TTS
- Synthèse vocale neurale avec contrôle de style.
- Prend en charge SSML pour :
  - Intonation
  - Pauses
  - Emotions prédéfinies.
- Compatible avec plusieurs voix multilingues.

### VALL-E
- Synthèse vocale à partir de quelques secondes de voix.
- Basé sur des codebooks audio (tokenisation).
- Expressivité et style conservés.
- Pas open source, mais publication scientifique disponible.

### VALL-E X
- Extension multilingue de VALL-E avec capacité cross-lingue.
- Permet de lire un texte dans une langue tout en gardant l'accent d’une autre langue.



## Google / DeepMind

### Tacotron 2 + WaveNet
- Pipeline classique de génération vocale.
- Tacotron : spectrogrammes → WaveNet : audio.
- Très haute qualité, bien maîtrisé.

### SoundStorm (DeepMind, 2023)
- Modèle non autoregressif, type "SoundStream-like".
- Génère directement l'audio avec contrôle temporel.



## Meta

### Voicebox
- Multilingue, génératif, multitâche.
- Capable de :
  - Continuer une voix.
  - Traduire vocalement.
  - Appliquer un style vocal cible.
- Pas encore publié sous forme open source.

### Make-A-Voice
- Synthèse vocale générative avec diffusion.
- Expressivité poussée.
- Contrôle de style, pitch, timbre.

### AudioCraft (inclut EnCodec)
- EnCodec = compresseur audio neuronal (essentiel dans TTS modernes).
- Utilisé pour la reconstruction vocale.
- AudioCraft = suite pour musique et voix.

### Tortoise TTS
- Synthèse vocale expressive.
- Très haute qualité.
- Zéro-shot cloning avec plusieurs extraits.
- Open source.

## NVIDIA

### RAD-TTS
- Contrôle visuel de la prosodie.
- Éditeur de timeline vocal.
- Application : animation, voix de personnages.

### FastPitch + HiFi-GAN
- Synthèse rapide avec vocodeur efficace.
- Contrôle explicite de la hauteur et de la vitesse.

### NeMo-TTS
- Framework complet open source pour créer, entraîner et utiliser des modèles TTS.

## Amazon

### Polly Neural TTS
- Synthèse vocale avec SSML avancé.
- Intonation, pauses, émotions supportées.
- Grande diversité de voix.

---

## Open Source / Académiques

### Bark (Suno)
- Génère des voix réalistes avec pauses, rires, émotions.
- Prend en charge des balises comme *[laughs]*, *[sighs]*.
- Open source.

---

## Entreprises Françaises & Concurrents Européens

### Voxygen (France)
- Spécialisé dans les voix françaises expressives.
- Application dans les transports, assistants vocaux, accessibilité.
- Voix avec personnalité (narrateur, animateur…).

### Acapela Group (France / Belgique)
- Large base de voix personnalisées.
- Synthèse émotionnelle.
- Voix pour enfants, personnes âgées, handicaps.

### ReadSpeaker (France / Global)
- Solutions de synthèse vocale dans l’éducation, santé, sites web.
- Contrôle SSML complet.
- Voix humaines expressives en français.

### Vivoka (France)
- Synthèse vocale embarquée.
- Solutions offline pour objets connectés, industrie.
- Reconnaissance vocale et TTS intégrés.



# Modèles Texte → Langage Naturel (Text-to-Speech expressif)

## OpenAI

### TTS-1
- Synthèse vocale expressive.
- Supporte émotions, intonation naturelle, pauses intelligentes.
- Utilisé dans ChatGPT Voice.
- Temps réel, très fluide, mais fermé.

### gpt-o4-mini-TTS
- Variante légère intégrée dans les agents vocaux GPT.
- Optimisé pour faible latence, bonne expressivité.

### Whisper-TTS 
- Variante exploratoire de Whisper orientée génération vocale (non publique).
- Possibilité de conversion texte-parole dans une boucle interactive.

## ElevenLabs

### Prime Voice AI
- Synthèse vocale hyper-réaliste.
- Clonage de voix avec émotion, accent et prosodie.
- Usage : narration, jeux vidéo, accessibilité.
- API complète avec contrôle SSML-like.

## Microsoft

### Azure Neural TTS
- Synthèse vocale neurale avec contrôle de style.
- Prend en charge SSML pour :
  - Intonation
  - Pauses
  - Emotions prédéfinies.
- Compatible avec plusieurs voix multilingues.

### VALL-E
- Synthèse vocale à partir de quelques secondes de voix.
- Basé sur des codebooks audio (tokenisation).
- Expressivité et style conservés.
- Pas open source, mais publication scientifique disponible.


## Google / DeepMind

### Tacotron 2 + WaveNet
- Pipeline classique de génération vocale.
- Tacotron : spectrogrammes → WaveNet : audio.
- Très haute qualité, bien maîtrisé.

### SoundStorm 
- Modèle non autoregressif, type "SoundStream-like".
- Génère directement l'audio avec contrôle temporel.



## Meta

### Voicebox
- Multilingue, génératif, multitâche.
- Capable de :
  - Continuer une voix.
  - Traduire vocalement.
  - Appliquer un style vocal cible.
- Pas encore publié sous forme open source.

### Make-A-Voice
- Synthèse vocale générative avec diffusion.
- Expressivité poussée.
- Contrôle de style, pitch, timbre.

### AudioCraft (inclut EnCodec)
- EnCodec = compresseur audio neuronal (essentiel dans TTS modernes).
- Utilisé pour la reconstruction vocale.
- AudioCraft = suite pour musique et voix.

### Tortoise TTS
- Synthèse vocale expressive.
- Très haute qualité.
- Zéro-shot cloning avec plusieurs extraits.
- Open source.

## NVIDIA

### RAD-TTS
- Contrôle visuel de la prosodie.
- Éditeur de timeline vocal.
- Application : animation, voix de personnages.

### FastPitch + HiFi-GAN
- Synthèse rapide avec vocodeur efficace.
- Contrôle explicite de la hauteur et de la vitesse.

### NeMo-TTS
- Framework complet open source pour créer, entraîner et utiliser des modèles TTS.

## Amazon

### Polly Neural TTS
- Synthèse vocale avec SSML avancé.
- Intonation, pauses, émotions supportées.
- Grande diversité de voix.

---

## Open Source / Académiques

### Bark (Suno)
- Génère des voix réalistes avec pauses, rires, émotions.
- Prend en charge des balises comme *[laughs]*, *[sighs]*.
- Open source.

### Coqui TTS
- Suite TTS complète.
- Supporte fine-tuning et multilingue.
- Clonage vocal rapide.

---

## Entreprises Françaises & Concurrents Européens

### Voxygen (France)
- Spécialisé dans les voix françaises expressives.
- Application dans les transports, assistants vocaux, accessibilité.
- Voix avec personnalité (narrateur, animateur…).

### Acapela Group (France / Belgique)
- Large base de voix personnalisées.
- Synthèse émotionnelle.
- Voix pour enfants, personnes âgées, handicaps.

### ReadSpeaker (France / Global)
- Solutions de synthèse vocale dans l’éducation, santé, sites web.
- Contrôle SSML complet.
- Voix humaines expressives en français.

### Vivoka (France)
- Synthèse vocale embarquée.
- Solutions offline pour objets connectés, industrie.
- Reconnaissance vocale et TTS intégrés.



---


# LLMs (2024-2025)

## OpenAI

### GPT-4o (4o-mini)
- **Accès** : API / ChatGPT Plus
- **Contexte** : 128k tokens
- **Multimodal** : Texte + image + voix
- **Points forts** : Très bon raisonnement, stable, rapide
- **Usage** : Chat, analyse, génération, agents IA, le mini fonctionne bien rapidement et consomme peu.



---

## Anthropic

### Claude 3 (Opus, Sonnet, Haiku)
- **Accès** : Claude.ai / API via Amazon Bedrock
- **Contexte** : 200k tokens (context window), 1M en preview
- **Points forts** : Compréhension documentaire, raisonnement sûr
- **Usage** : Chat professionnel, résumé, traitement juridique

---

## Google DeepMind

### Gemini 1.5 (Flash, Pro)
- **Accès** : API via Vertex AI, Gemini.google.com
- **Contexte** : Jusqu’à 1M de tokens
- **Multimodal** : Oui (image, code, vidéo, audio)
- **Points forts** : Mémoire longue, multitâche
- **Usage** : Agents multi-entrée, analyse massive

### PaLM 2 (legacy)
- **Accès** : Bard (remplacé par Gemini)
- **Multilingue**, bon en traduction

---

## Meta

### LLaMA 2 (7B, 13B, 70B)
- **Accès** : Téléchargeable (Meta License), API via Together, Perplexity, etc.
- **Points forts** : Solide, très répandu, nombreuses variantes (fine-tuned)
- **Usage** : Chat open source, assistants spécialisés

### LLaMA 3 (2024)
- **Accès** : Arrivée prévue avril 2024 (7B, 65B, puis 400B)
- **Objectif** : concurrencer GPT-4
- **Multimodal** (à venir), support multilingue

---

## Mistral (France)

### Mistral 7B
- **Accès** : Open-weight (Apache 2.0), API via Hugging Face, Fireworks
- **Type** : Dense
- **Points forts** : Léger, performant

### Mixtral 8x7B
- **Type** : Mixture of Experts (MoE), active 2 experts
- **Accès** : Open-weight (Apache 2.0)
- **Avantage** : Rapport qualité/performance excellent

### Tiny/Mistral Mini (expérimental)
- **Ultra-léger**, possible usage edge/mobile

---



## Aleph Alpha (Allemagne)

### Luminous (Base, Control, Supreme)
- **Accès** : API / sur demande
- **Points forts** : Multilingue, explicabilité
- **Objectif** : Souveraineté européenne

---

## xAI (Elon Musk)

### Grok (Grok-1)
- **Accès** : X (Twitter) Premium+
- **Objectif** : Humour + information temps réel via X
- **Multimodal** (à venir)

---

## Open Source / Alternatifs

### Falcon 7B / 180B (TII - EAU)
- **Accès** : Open-weight (licence non commerciale pour le 180B)
- **Utilisation** : Très répandu en entreprise + recherche

### Zephyr / OpenChat
- **Basé sur Mistral, LLaMA, etc.**
- **Fine-tuned pour conversation et dialogue**

---



# Modèles Speech → Speech (Direct Speech-to-Speech)

## OpenAI

### Voice Engine (prototype, 2024)
- **Fonction** : conversion voix → voix avec conservation du **style vocal**, accent, émotion.
- **Capacité** :
  - Synthèse vocale dans une langue différente tout en gardant l'identité vocale.
- **Statut** : Modèle non public, utilisé en démonstration privée.
- **Pipeline probable** : Whisper (STT) + TTS-1 + Voice conversion.
- **Utilisation** : agents vocaux, traduction émotionnelle, accessibilité.

### GPT-4 Voice Loop (S2S implicite)
- **Fonction** : agent vocal réactif.
- **Pipeline** : STT (Whisper) + GPT + TTS-1 en temps réel.
- **Particularité** : latence très faible, voix fluide, adaptative.

---

## Meta

### SeamlessM4T (2023)
- **Fonction** : Multimodal, Multilingue, Multi-tâches (speech ↔ speech, speech ↔ text, etc.)
- **Langues** : +100 en texte, +36 en audio.
- **Particularités** :
  - Traduction vocale directe.
  - Maintien de l’émotion du locuteur.
- **Pipeline** :
  - Encodeur audio + traducteur + vocodeur.
  - Peut fonctionner end-to-end ou modulaire.
- **SeamlessExpressive (2024)** :
  - **Ajoute** : gestion de **l’émotion**, **intonation**, **style vocal** dans la traduction.
  - **Open source** (partiellement, via HuggingFace + Meta).

---

## Google / DeepMind

### Translatotron 1 & 2
- **Type** : Modèles end-to-end speech → speech.
- **Pipeline** :
  - Encodeur audio → spectrogrammes → vocodeur.
  - Sans transcription intermédiaire explicite.
- **Capacités** :
  - Traduction vocale avec **conservation de l’identité vocale**.
  - Translatotron 2 ajoute un **speaker encoder** pour un meilleur contrôle vocal.
- **Applications** : traduction vocale en direct, doublage multilingue.
- **Limites** : Pas open source, pas encore en production Google Translate.

### AudioPaLM
- **Fusion** de PaLM-2 (texte) + AudioLM (audio).
- **Multimodalité complète** : texte, parole, audio tokens.
- **Fonctionnalité** : traduction audio multilingue.
- **Statut** : expérimental (publication 2023).

---

## Microsoft

### Speech Translation API (Azure)
- **Fonction** : S2S multilingue en streaming.
- **Pipeline** : ASR + Traduction + Neural TTS.
- **Voix personnalisées**, pauses naturelles, émotions.
- **Usage** : réunions, live events, sous-titrage vocalisé.

### VALL-E X (recherche)
- **Type** : TTS conditionné sur style vocal, y compris cross-lingue.
- **Fonction** : Générer la voix du locuteur d’origine dans une langue différente.
- **Approche** : tokenisation audio + apprentissage vocoder.

---

## Amazon

### Alexa S2S Translation
- **Utilisation** : Traduction vocale entre deux personnes via Alexa.
- **Pipeline** : STT + Traduction + TTS, mais intégré de manière fluide.
- **Langues supportées** : anglais, espagnol, allemand, italien, etc.

---


