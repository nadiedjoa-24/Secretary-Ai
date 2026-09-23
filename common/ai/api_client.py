from typing import List, Optional

import openai
from google.cloud import texttospeech
from pydantic import BaseModel

from common.config import AUDIO_DIR, GOOGLE_TTS_KEY_FILE, require_env
from common.ai.model.base_model import BaseAIModel, Message

OPENAI_TTS = "openai"
GOOGLE_TTS = "google"


def _as_dicts(messages: List[Message | dict]) -> List[dict]:
    return [m.model_dump() if isinstance(m, BaseModel) else m for m in messages]


class APIClient(BaseAIModel):
    """BaseAIModel backed by the OpenAI API, with Google Cloud Text-to-Speech for French voice output."""

    def __init__(self, api_key: Optional[str] = None, tts_engine: str = GOOGLE_TTS):
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

    def tts(self, text: str, filename: str = "output.wav") -> str:
        AUDIO_DIR.mkdir(parents=True, exist_ok=True)
        output_path = AUDIO_DIR / filename
        if self.tts_engine == OPENAI_TTS:
            audio = self._openai_tts(text)
        elif self.tts_engine == GOOGLE_TTS:
            audio = self._google_tts(text)
        else:
            raise ValueError(f"Unknown TTS engine {self.tts_engine!r}, expected {OPENAI_TTS!r} or {GOOGLE_TTS!r}.")
        output_path.write_bytes(audio)
        return str(output_path)

    def _openai_tts(self, text: str) -> bytes:
        response = self.client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="alloy",
            input=text,
            instructions="Speak in a neutral, professional tone, like a medical secretary.",
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

    def stt(self, audio_path: str) -> Message:
        with open(audio_path, "rb") as audio_file:
            response = self.client.audio.transcriptions.create(model="gpt-4o-mini-transcribe", file=audio_file)
        if not response.text:
            raise ValueError("Empty transcription from the OpenAI API.")
        return Message(role="user", content=response.text)


if __name__ == "__main__":
    from common.ai.audio_controller.audio_controller import AudioController

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
