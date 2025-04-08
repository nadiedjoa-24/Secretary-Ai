
# 🎙️ Utiliser Whisper (transcription audio vers texte) avec `pip`

Voici comment utiliser un modèle **Whisper** (ici `whisper-large-v3`) pour convertir un **fichier audio en texte** en Python à l’aide de `transformers` et `datasets`.

---

## ⚙️ Prérequis

Installe les bibliothèques nécessaires :

```bash
pip install torch transformers datasets
```

---

##  Code complet

```python
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline
from datasets import load_dataset

# Détection automatique du device (GPU si dispo)
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

#  Modèle utilisé
model_id = "openai/whisper-large-v3"

#  Chargement du modèle et du processeur
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_id,
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True,
    use_safetensors=True,
).to(device)

processor = AutoProcessor.from_pretrained(model_id)

#  Création du pipeline de transcription
pipe = pipeline(
    "automatic-speech-recognition",
    model=model,
    tokenizer=processor.tokenizer,
    feature_extractor=processor.feature_extractor,
    torch_dtype=torch_dtype,
    device=device,
)

#  Exemple avec un échantillon du dataset LibriSpeech
dataset = load_dataset("distil-whisper/librispeech_long", "clean", split="validation")
sample = dataset[0]["audio"]

#  Transcription à partir d’un fichier audio local
#  Si l’audio dure plus de 30 secondes, ajoute `return_timestamps=True`
result = pipe("nom_du_fichier.mp3", return_timestamps=True)

# Affichage du texte transcrit
print(result["text"])
```

---

##  Remarques

- Le modèle `whisper-large-v3` est puissant mais demande pas mal de VRAM (~10-15Go en float16).
- Si ton audio dure plus de **30 secondes**, le pipeline passe en mode "long-form" et nécessite `return_timestamps=True`.
- Tu peux aussi utiliser directement `sample["array"]` et `sample["sampling_rate"]` si tu veux travailler avec les données du dataset Hugging Face.

---

##  Résultat attendu

Une transcription textuelle du contenu de ton fichier audio, et si `return_timestamps=True`, des segments horodatés utiles pour les sous-titres ou l’alignement.

```python
{
  'text': "Hello and welcome...",
  'chunks': [
    {'timestamp': (0.0, 3.2), 'text': "Hello"},
    {'timestamp': (3.2, 6.5), 'text': "and welcome"},
    ...
  ]
}
```
