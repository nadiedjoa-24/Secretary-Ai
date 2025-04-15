import whisper

def audio_to_text_whisper_local(file_path):
    model = whisper.load_model("base")
    result = model.transcribe(file_path)
    return result["text"]

# Exemple d'utilisation
texte = audio_to_text_whisper_local("exemple_francis_cabrel.mp3")
print(texte)
