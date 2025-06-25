import sys
import os
# Ajoute la racine du projet au PYTHONPATH pour permettre les imports absolus de "common"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from common.ai.model.BaseAIModel import BaseAIModel, Message
from transformers import pipeline
from typing import List
import soundfile as sf
from pydantic import BaseModel
import json


class LOCAL_Client(BaseAIModel):

    def __init__(self):
        self._load_models()

    def _load_models(self):
        # Chat model pipeline
        self.chat_pipe = pipeline("text-generation", model="microsoft/DialoGPT-small")
        # Speech-to-text pipeline
        self.asr_pipe = pipeline("automatic-speech-recognition", model="openai/whisper-small")
        # Text-to-speech pipeline (French) using MMS-TTS
        self.tts_pipe = pipeline(
            "text-to-speech",
            model="facebook/mms-tts-fra",
            trust_remote_code=True
        )

    def tts(self, text: str, output_path: str) -> str:
        output = self.tts_pipe(text)
        wav = output["wav"]
        sr = output["sampling_rate"]
        sf.write(output_path, wav, sr)
        return output_path

    def stt(self, audio_path: str) -> Message:
        result = self.asr_pipe(audio_path)
        # result may be a dict or list of dicts
        text = result["text"] if isinstance(result, dict) else result[0]["text"]
        return Message(role="assistant", content=text)

    def basic(self, messages: List[Message]) -> Message:
        # Use the last user message to generate a reply via text-generation
        content = messages[-1].content if messages else ""
        result = self.chat_pipe(content, max_length=50, num_return_sequences=1)
        reply = result[0]["generated_text"]
        return Message(role="assistant", content=reply)
    
    def parse(self, messages: List[Message], data_model: BaseModel) -> BaseModel:
        # Construire un prompt décrivant le schéma et les messages
        msgs_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
        prompt = (
            "Génère uniquement un JSON valide correspondant au schéma suivant :\n"
            f"{data_model.schema_json()}\n"
            "À partir des entrées suivantes :\n"
            f"{msgs_text}"
        )
        # Appel au modèle pour obtenir la sortie JSON
        result = self.chat_pipe(prompt, max_length=500, num_return_sequences=1)
        json_str = result[0]["generated_text"]
        try:
            return data_model.parse_raw(json_str)
        except Exception as e:
            raise ValueError(f"Échec du parsing : {e}")

    def reflexion(self, messages: List[Message]) -> Message:
        # Réfléchir à haute voix puis répondre
        content = messages[-1].content if messages else ""
        prompt = (
            "Réfléchis à haute voix, énumère tes étapes de raisonnement, "
            "puis donne la réponse.\n"
            f"Question : {content}"
        )
        result = self.chat_pipe(prompt, max_length=500, num_return_sequences=1)
        reply = result[0]["generated_text"]
        return Message(role="assistant", content=reply)

if __name__ == "__main__":
    # Instantiate the local client and test its methods
    client = LOCAL_Client()
    print("=== Testing LOCAL_Client functionalities ===")
    
    # Test basic chat
    print("\n-- basic chat --")
    user_msg = Message(role="user", content="Bonjour, comment allez-vous?")
    resp = client.basic([user_msg])
    print("Response:", resp.content)
    
    # Test text-to-speech (TTS)
    print("\n-- text-to-speech --")
    tts_file = "test_tts.wav"
    client.tts("Ceci est un test de synthèse vocale.", tts_file)
    print("Generated audio file:", tts_file)
    
    # Test speech-to-text (STT)
    print("\n-- speech-to-text --")
    stt_msg = client.stt(tts_file)
    print("Transcription:", stt_msg.content)
