from dataclasses import dataclass, field
from typing import List, Optional

import openai
from google.cloud import texttospeech
from pydantic import BaseModel

from secretary_ai.ai.base_model import BaseAIModel, Message
from secretary_ai.config import AI_PROVIDER, GOOGLE_TTS_KEY_FILE, TTS_ENGINE, require_env

OPENAI_TTS = "openai"
GOOGLE_TTS = "google"
# The web app lets the visitor's browser read the answers aloud, so the server synthesizes nothing.
BROWSER_TTS = "browser"


@dataclass(frozen=True)
class Provider:
    key_variable: str
    chat_model: str
    reasoning_model: str
    transcription_model: str
    extraction_model: str
    base_url: Optional[str] = None
    chat_options: dict = field(default_factory=dict)


PROVIDERS = {
    "openai": Provider(
        key_variable="OPENAI_API_KEY",
        chat_model="gpt-4o-mini",
        reasoning_model="o4-mini",
        transcription_model="gpt-4o-mini-transcribe",
        extraction_model="gpt-4o-mini",
        chat_options={"temperature": 0.7},
    ),
    # Groq serves open-weight models behind an OpenAI-compatible API, with a free tier.
    # Rate limits are per model, so extraction runs on a second model.
    "groq": Provider(
        key_variable="GROQ_API_KEY",
        chat_model="openai/gpt-oss-120b",
        reasoning_model="openai/gpt-oss-120b",
        transcription_model="whisper-large-v3-turbo",
        extraction_model="openai/gpt-oss-20b",
        base_url="https://api.groq.com/openai/v1",
        chat_options={"reasoning_effort": "low"},
    ),
}


def _as_dicts(messages: List[Message | dict]) -> List[dict]:
    return [m.model_dump() if isinstance(m, BaseModel) else m for m in messages]


class APIClient(BaseAIModel):
    """BaseAIModel backed by an OpenAI-compatible API (OpenAI or Groq).

    Speech synthesis uses OpenAI, Google Cloud Text-to-Speech, or is left to the browser.
    """

    def __init__(self, api_key: Optional[str] = None, provider: str = AI_PROVIDER, tts_engine: str = TTS_ENGINE):
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown AI provider {provider!r}, expected one of {sorted(PROVIDERS)}.")
        if tts_engine not in (OPENAI_TTS, GOOGLE_TTS, BROWSER_TTS):
            raise ValueError(f"Unknown TTS engine {tts_engine!r}, expected "
                             f"{OPENAI_TTS!r}, {GOOGLE_TTS!r} or {BROWSER_TTS!r}.")
        if tts_engine == OPENAI_TTS and provider != "openai":
            raise ValueError(f"The {OPENAI_TTS!r} TTS engine needs the openai provider.")
        self.provider = PROVIDERS[provider]
        self.client = openai.OpenAI(api_key=api_key or require_env(self.provider.key_variable),
                                    base_url=self.provider.base_url)
        self.tts_engine = tts_engine

    def _complete(self, messages: List[Message | dict], **options) -> Message:
        response = self.client.chat.completions.create(messages=_as_dicts(messages), **options)
        content = response.choices[0].message.content
        if not content:
            raise ValueError("Empty response from the model.")
        return Message(role="assistant", content=content.strip())

    def basic(self, messages: List[Message | dict]) -> Message:
        return self._complete(messages, model=self.provider.chat_model, **self.provider.chat_options)

    def reflexion(self, messages: List[Message | dict]) -> Message:
        return self._complete(messages, model=self.provider.reasoning_model)

    def parse(self, messages: List[Message | dict], data_model: type[BaseModel]) -> BaseModel:
        response = self.client.chat.completions.parse(
            model=self.provider.extraction_model,
            messages=_as_dicts(messages),
            response_format=data_model,
        )
        parsed = response.choices[0].message.parsed
        if parsed is None:
            raise ValueError("The model returned no parsable output.")
        return parsed

    def synthesize(self, text: str) -> bytes:
        if self.tts_engine == GOOGLE_TTS:
            return self._google_tts(text)
        if self.tts_engine == OPENAI_TTS:
            return self._openai_tts(text)
        raise RuntimeError("Speech synthesis is left to the browser (TTS_ENGINE=browser).")

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
            model=self.provider.transcription_model,
            file=(filename, audio),
            language="fr",
        )
        if not response.text:
            raise ValueError("Empty transcription.")
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
