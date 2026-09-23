import pytest

from secretary_ai.ai.api_client import APIClient


def test_groq_uses_its_own_endpoint_and_models():
    client = APIClient(api_key="test", provider="groq", tts_engine="browser")

    assert str(client.client.base_url).startswith("https://api.groq.com/openai/v1")
    assert client.provider.transcription_model == "whisper-large-v3-turbo"


def test_missing_key_names_the_variable_of_the_provider(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="GROQ_API_KEY"):
        APIClient(provider="groq", tts_engine="browser")


@pytest.mark.parametrize("provider, tts_engine", [("mistral", "browser"), ("groq", "openai"), ("openai", "espeak")])
def test_invalid_configuration_is_rejected(provider, tts_engine):
    with pytest.raises(ValueError):
        APIClient(api_key="test", provider=provider, tts_engine=tts_engine)


def test_browser_voice_synthesizes_nothing_on_the_server():
    client = APIClient(api_key="test", provider="groq", tts_engine="browser")

    with pytest.raises(RuntimeError):
        client.synthesize("Bonjour")
