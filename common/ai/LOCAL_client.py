from transformers import AutoTokenizer, AutoModel
from .model.BaseAIModel import BaseAIModel, Message
from typing import List


class LOCAL_Client(BaseAIModel):

    def __init__(self):
        pass

    def _load_models(self):
        pass

    def tts(self, text: str, output_path: str) -> str:
        pass

    def stt(self, audio_path: str) -> str:
        pass

    def basic(self, messages: List[Message]) -> Message:
        pass

    def basic(self, messages: List[Message]) -> Message:
        pass


