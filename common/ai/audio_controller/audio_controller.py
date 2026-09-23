import wave
from pathlib import Path
from typing import Optional

import pyaudio
import speech_recognition as sr

from common.config import AUDIO_DEVICE_INDEX, AUDIO_DIR


class AudioController:
    """Records speech from the microphone and plays WAV files."""

    CHUNK = 1024

    def __init__(self, directory: Path = AUDIO_DIR, device_index: Optional[int] = AUDIO_DEVICE_INDEX):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.device_index = device_index
        self.audio = pyaudio.PyAudio()

    def listen(self, filename: str = "audio_input.wav") -> str:
        """Record until the speaker pauses and return the path of the WAV file."""
        recognizer = sr.Recognizer()
        recognizer.pause_threshold = 1.0
        with sr.Microphone(device_index=self.device_index) as source:
            print("Calibrating for ambient noise, please stay silent...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("Listening...")
            audio_data = recognizer.listen(source)

        filepath = self.directory / filename
        filepath.write_bytes(audio_data.get_wav_data())
        return str(filepath)

    def play(self, filepath: str) -> None:
        if not Path(filepath).exists():
            raise FileNotFoundError(f"Audio file not found: {filepath}")

        with wave.open(str(filepath), "rb") as wav:
            stream = self.audio.open(
                format=self.audio.get_format_from_width(wav.getsampwidth()),
                channels=wav.getnchannels(),
                rate=wav.getframerate(),
                output=True,
            )
            try:
                data = wav.readframes(self.CHUNK)
                while data:
                    stream.write(data)
                    data = wav.readframes(self.CHUNK)
            finally:
                stream.stop_stream()
                stream.close()

    def __del__(self):
        self.audio.terminate()


if __name__ == "__main__":
    controller = AudioController()
    controller.play(controller.listen())
