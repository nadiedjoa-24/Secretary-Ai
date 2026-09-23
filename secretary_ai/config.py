import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent

load_dotenv(PROJECT_ROOT / ".env")

PLANNING_DIR = PROJECT_ROOT / "planning_json"
AUDIO_DIR = PROJECT_ROOT / "audio_recordings"
PRESCRIPTIONS_DIR = PROJECT_ROOT / "prescriptions"
AI_PROVIDER = os.getenv("AI_PROVIDER", "openai")
TTS_ENGINE = os.getenv("TTS_ENGINE", "openai")
GOOGLE_TTS_KEY_FILE = PROJECT_ROOT / os.getenv("GOOGLE_TTS_KEY_FILE", "google_cloud_tts_key.json")
# Microphone index as listed by PyAudio; unset means the system default microphone.
AUDIO_DEVICE_INDEX = int(os.environ["AUDIO_DEVICE_INDEX"]) if os.getenv("AUDIO_DEVICE_INDEX") else None


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable {name}. Copy .env.example to .env and fill it in.")
    return value
