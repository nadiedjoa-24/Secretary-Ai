from typing import List, Optional

import openai
from google.cloud import texttospeech
from pydantic import BaseModel

from secretary_ai.ai.base_model import BaseAIModel, Message
from secretary_ai.config import GOOGLE_TTS_KEY_FILE, TTS_ENGINE, require_env

OPENAI_TTS = "openai"
GOOGLE_TTS = "google"


def _as_dicts(messages: List[Message | dict]) -> List[dict]:
    return [m.model_dump() if isinstance(m, BaseModel) else m for m in messages]


class APIClient(BaseAIModel):
    """BaseAIModel backed by the OpenAI API. Speech synthesis uses OpenAI or Google Cloud Text-to-Speech."""

    def __init__(self, api_key: Optional[str] = None, tts_engine: str = TTS_ENGINE):
        if tts_engine not in (OPENAI_TTS, GOOGLE_TTS):
            raise ValueError(f"Unknown TTS engine {tts_engine!r}, expected {OPENAI_TTS!r} or {GOOGLE_TTS!r}.")
        self.client = openai.OpenAI(api_key=api_key or require_env("OPENAI_API_KEY"))
        self.tts_engine = tts_engine

    def _complete(self, messages: List[Message | dict], **options) -> Message:
        response = self.client.chat.completions.create(messages=_as_dicts(messages), **options)
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from the OpenAI API.")
        return Message(role="assistant", content=content)

    def basic(self, messages: List[Message | dict]) -> Message:
        return self._complete(messages, model="gpt-4o-mini", temperature=0.7)

    def reflexion(self, messages: List[Message | dict]) -> Message:
        # Reasoning models only accept the default temperature.
        return self._complete(messages, model="o4-mini")

    def parse(self, messages: List[Message | dict], data_model: type[BaseModel]) -> BaseModel:
        response = self.client.responses.parse(
            model="gpt-4o-mini",
            input=_as_dicts(messages),
            text_format=data_model,
        )
        if response.output_parsed is None:
            raise ValueError("The OpenAI API returned no parsable output.")
        return response.output_parsed

    def synthesize(self, text: str) -> bytes:
        if self.tts_engine == GOOGLE_TTS:
            return self._google_tts(text)
        return self._openai_tts(text)

    def _openai_tts(self, text: str) -> bytes:
        response = self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            instructions="Speak French with a neutral, professional tone, like a medical secretary.",
            response_format="wav",
        )
        return response.content

    def _google_tts(self, text: str) -> bytes:
        if GOOGLE_TTS_KEY_FILE.is_file():
            tts_client = texttospeech.TextToSpeechClient.from_service_account_file(str(GOOGLE_TTS_KEY_FILE))
        else:
            tts_client = texttospeech.TextToSpeechClient()
        response = tts_client.synthesize_speech(
            input=texttospeech.SynthesisInput(text=text),
            voice=texttospeech.VoiceSelectionParams(
                language_code="fr-FR",
                ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL,
            ),
            audio_config=texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.LINEAR16),
        )
        if not response.audio_content:
            raise ValueError("Empty response from Google Cloud Text-to-Speech.")
        return response.audio_content

    def transcribe(self, audio: bytes, filename: str = "audio.wav") -> str:
        response = self.client.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=(filename, audio),
            language="fr",
        )
        if not response.text:
            raise ValueError("Empty transcription from the OpenAI API.")
        return response.text


if __name__ == "__main__":
    from secretary_ai.ai.audio_controller import AudioController

    client = APIClient()
    audio = AudioController()
    print("Voice chat demo, say 'exit' to quit.")
    while True:
        question = client.stt(audio.listen())
        if question.content.strip().lower() in ("exit", "quit", "stop"):
            break
        answer = client.basic([question])
        print(f"Assistant: {answer.content}")
        audio.play(client.tts(answer.content))
