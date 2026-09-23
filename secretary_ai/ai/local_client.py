"""Experimental BaseAIModel running Hugging Face models locally. Not wired into the agents yet."""
import io
import json
from typing import List

import soundfile as sf
from pydantic import BaseModel
from transformers import pipeline

from secretary_ai.ai.base_model import BaseAIModel, Message


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

    def synthesize(self, text: str) -> bytes:
        output = self.tts_pipe(text)
        buffer = io.BytesIO()
        sf.write(buffer, output["audio"].squeeze(), output["sampling_rate"], format="WAV")
        return buffer.getvalue()

    def transcribe(self, audio: bytes, filename: str = "audio.wav") -> str:
        # The pipeline decodes compressed formats such as webm through ffmpeg.
        result = self.asr_pipe(audio, generate_kwargs={"language": "french"})
        return result["text"] if isinstance(result, dict) else result[0]["text"]


if __name__ == "__main__":
    client = LocalClient()
    print(client.basic([Message(role="user", content="Bonjour, comment allez-vous ?")]).content)
    audio_path = client.tts("Ceci est un test de synthèse vocale.")
    print(client.stt(audio_path).content)
