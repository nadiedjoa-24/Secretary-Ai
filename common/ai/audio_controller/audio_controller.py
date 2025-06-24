import os
import pyaudio
import wave
import numpy as np
import time
import speech_recognition as sr

class AUDIO_Controller:
    def __init__(self, directory: str = "./audio_recordings/", device_index: int = None) -> None:
        """
        Initialise le contrôleur audio.
        directory : dossier où seront enregistrés les fichiers .wav
        """
        self.directory = directory
        os.makedirs(self.directory, exist_ok=True)

        self.format = pyaudio.paInt16
        self.rate = 16000
        self.channels = 1
        self.chunk = 1024
        self.threshold = 45.0  
        self.silence_duration = 6
        self.alpha = 0.2  
        self.noise_calibration_chunks = 30   
        self.threshold_factor = 0.8          
        self.audio = pyaudio.PyAudio()
        self.device_index = device_index

    def _rms(self, data: bytes) -> float:
        """Calcule le RMS (énergie) d'un buffer audio."""
        samples = np.frombuffer(data, dtype=np.int16)
        if samples.size == 0:
            return 0.0
        return np.sqrt(np.mean(samples**2))

    def listen(self) -> str:
        """
        Enregistre depuis le micro jusqu'à 2s de silence.
        Retourne le chemin du .wav créé,
        ou lève RuntimeError si aucune voix n'a été détectée.
        """
        params = {
            'format': self.format,
            'channels': self.channels,
            'rate': self.rate,
            'input': True,
            'frames_per_buffer': self.chunk,
        }
        if self.device_index is not None:
            params['input_device_index'] = self.device_index
        stream = self.audio.open(**params)
        for i in range(self.audio.get_device_count()):
            dev = self.audio.get_device_info_by_index(i)
            if dev['maxInputChannels'] > 0:
                print(f"Entrée {i}: {dev['name']} (canaux: {dev['maxInputChannels']})")

        # Seuil fixe sans calibration
        threshold = self.threshold
        print(f"▶️ Prêt. Utilisation du seuil fixe = {threshold:.1f}")

        frames = []
        envelope = 0.0
        alpha = self.alpha
        recording = False
        last_sound_time = time.time()

        try:
            while True:
                data = stream.read(self.chunk, exception_on_overflow=False)
                raw = self._rms(data)
                envelope = alpha * raw + (1 - alpha) * envelope
                energy = envelope
                print(f"\rRaw: {raw:6.1f}  Env: {energy:6.1f}", end="", flush=True)

                if energy < threshold:
                    if not recording:
                        print("\n🔴 Enregistrement lancé.")
                        recording = True
                    frames.append(data)
                    last_sound_time = time.time()
                elif recording:
                    frames.append(data)
                    if time.time() - last_sound_time > self.silence_duration:
                        print("\n⏹️ Silence détecté, arrêt de l'enregistrement.")
                        break
        finally:
            stream.stop_stream()
            stream.close()

        if not frames:
            raise RuntimeError("Aucune voix détectée.")

        timestamp = int(time.time())
        filename = f"output_stt.wav"
        filepath = os.path.join(self.directory, filename)

        with wave.open(filepath, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self.audio.get_sample_size(self.format))
            wf.setframerate(self.rate)
            wf.writeframes(b''.join(frames))

        print(f"✅ Enregistré dans : {filepath}")
        return filepath

    def play(self, filepath: str) -> None:
        """
        Joue le fichier audio spécifié.
        filename peut être un chemin absolu ou relatif à directory.
        """
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Fichier introuvable : {filepath}")

        wf = wave.open(filepath, 'rb')
        stream = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                                 channels=wf.getnchannels(),
                                 rate=wf.getframerate(),
                                 output=True)

        print(f"▶️ Lecture de : {filepath}")
        data = wf.readframes(self.chunk)
        while data:
            stream.write(data)
            data = wf.readframes(self.chunk)

        stream.stop_stream()
        stream.close()
        wf.close()
        print("✅ Lecture terminée.")

    def _listen(self) -> str:
        """
        Enregistre l'audio depuis le micro avec SpeechRecognition et enregistre dans un fichier WAV.
        Retourne le chemin du fichier audio créé.
        """
        r = sr.Recognizer()
        with sr.Microphone(device_index=self.device_index) as source:
            print("⏳ Calibration du bruit ambiant (restez silencieux)...")
            r.adjust_for_ambient_noise(source, duration=1)
            r.pause_threshold = 1.0
            print("▶️ Parlez maintenant…")
            audio_data = r.listen(source)

        timestamp = int(time.time())
        filename = f"audio_input.wav"
        filepath = os.path.join(self.directory, filename)

        with open(filepath, "wb") as f:
            f.write(audio_data.get_wav_data())

        print(f"✅ Audio enregistré dans : {filepath}")
        return filepath

    def __del__(self):
        self.audio.terminate()

# Test 
if __name__ == "__main__":
    ctrl = AUDIO_Controller(device_index=2)
    try:
        file_path = ctrl._listen()
        ctrl.play(file_path)
    except Exception as e:
        print(f"❌ Erreur : {e}")