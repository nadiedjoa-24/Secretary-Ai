import openai

openai.api_key = "TON_OPENAI_API_KEY"

def audio_to_text_whisper(file_path):
    with open(file_path, "rb") as audio_file:
        response = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
    return response.text

# Exemple d'utilisation
texte = audio_to_text_whisper("exemple_francis_cabrel.mp3")
print(texte)
