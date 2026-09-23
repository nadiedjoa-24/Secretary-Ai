from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Literal

from pydantic import BaseModel

from secretary_ai.config import AUDIO_DIR


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class BaseAIModel(ABC):
    """Common interface implemented by every AI backend (OpenAI API or local Hugging Face models)."""

    @abstractmethod
    def basic(self, messages: List[Message]) -> Message:
        """Fast chat completion."""

    @abstractmethod
    def reflexion(self, messages: List[Message]) -> Message:
        """Slower completion with a reasoning model."""

    @abstractmethod
    def parse(self, messages: List[Message], data_model: type[BaseModel]) -> BaseModel:
        """Extract structured data matching `data_model` from a conversation."""

    @abstractmethod
    def synthesize(self, text: str) -> bytes:
        """Synthesize French speech and return it as WAV bytes."""

    @abstractmethod
    def transcribe(self, audio: bytes, filename: str = "audio.wav") -> str:
        """Transcribe French speech. `filename` tells the backend the audio format (wav, webm, mp4...)."""

    def tts(self, text: str, filename: str = "output.wav") -> str:
        """Synthesize `text` to a WAV file and return its path."""
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        path = AUDIO_DIR / filename
        path.write_bytes(self.synthesize(text))
        return str(path)

    def stt(self, audio_path: str) -> Message:
        path = Path(audio_path)
        return Message(role="user", content=self.transcribe(path.read_bytes(), path.name))
