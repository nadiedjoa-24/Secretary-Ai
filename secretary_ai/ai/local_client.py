"""Experimental BaseAIModel running Hugging Face models locally. Not wired into the agents yet."""
import json
from typing import List

import soundfile as sf
from pydantic import BaseModel
from transformers import pipeline

from secretary_ai.ai.base_model import BaseAIModel, Message
from secretary_ai.config import AUDIO_DIR


class LocalClient(BaseAIModel):

    def __init__(self):
        self.chat_pipe = pipeline("text-generation", model="microsoft/DialoGPT-small")
        self.asr_pipe = pipeline("automatic-speech-recognition", model="openai/whisper-small")
        self.tts_pipe = pipeline("text-to-speech", model="facebook/mms-tts-fra")

    def _generate(self, prompt: str, max_length: int) -> str:
        result = self.chat_pipe(prompt, max_length=max_length, num_return_sequences=1)
        return result[0]["generated_text"]

    def basic(self, messages: List[Message]) -> Message:
        prompt = messages[-1].content if messages else ""
        return Message(role="assistant", content=self._generate(prompt, max_length=50))

    def reflexion(self, messages: List[Message]) -> Message:
        question = messages[-1].content if messages else ""
        prompt = f"Think step by step, then answer.\nQuestion: {question}"
        return Message(role="assistant", content=self._generate(prompt, max_length=500))

    def parse(self, messages: List[Message], data_model: type[BaseModel]) -> BaseModel:
        conversation = "\n".join(f"{m.role}: {m.content}" for m in messages)
        prompt = (
            "Return only valid JSON matching this schema:\n"
            f"{json.dumps(data_model.model_json_schema())}\n"
            f"Input:\n{conversation}"
        )
        return data_model.model_validate_json(self._generate(prompt, max_length=500))

    def tts(self, text: str, filename: str = "output.wav") -> str:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = AUDIO_DIR / filename
        output = self.tts_pipe(text)
        sf.write(output_path, output["audio"].squeeze(), output["sampling_rate"])
        return str(output_path)

    def stt(self, audio_path: str) -> Message:
        result = self.asr_pipe(audio_path)
        text = result["text"] if isinstance(result, dict) else result[0]["text"]
        return Message(role="user", content=text)


if __name__ == "__main__":
    client = LocalClient()
    print(client.basic([Message(role="user", content="Bonjour, comment allez-vous ?")]).content)
    audio_path = client.tts("Ceci est un test de synthèse vocale.")
    print(client.stt(audio_path).content)
