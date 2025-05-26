from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import List, Literal, TypedDict



class Message(TypedDict):
    role: Literal["user", "assistant", "system"]
    content: str



class BaseAIModel(ABC):
    """
    Base class for AI models.
    The idea is to set a common interface for all AI models.
    Basically each client (LOCAL via Huggingface or API via OpenAI) deliver the same methods (signature) with its own implementation.
    Each client must provide a tts method, a stt method, a request method (basic or with reflexion) and a parse method.
    """
    
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

