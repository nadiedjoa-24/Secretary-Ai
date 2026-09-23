from abc import ABC, abstractmethod
from typing import List, Literal

from pydantic import BaseModel


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
    def tts(self, text: str) -> str:
        """Synthesize `text` to a WAV file and return its path."""

    @abstractmethod
    def stt(self, audio_path: str) -> Message:
        """Transcribe an audio file."""
