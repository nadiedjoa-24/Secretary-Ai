import os
import pyaudio
import wave
import numpy as np
import time

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

        print("⏳ Calibration du bruit de fond (restez silencieux)...")
        noise_levels = []
        for _ in range(self.noise_calibration_chunks):
            data = stream.read(self.chunk, exception_on_overflow=False)
            noise_levels.append(self._rms(data))
        noise_floor = sum(noise_levels) / len(noise_levels)
        threshold = noise_floor * self.threshold_factor
        print(f"  • Bruit moyen = {noise_floor:.1f} → seuil = {threshold:.1f}\n")
        print("▶️ Parlez pour démarrer l'enregistrement...")
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

    def play(self, filename: str) -> None:
        """
        Joue le fichier audio spécifié.
        filename peut être un chemin absolu ou relatif à directory.
        """
        # Détermine chemin complet
        filepath = filename if os.path.isabs(filename) else os.path.join(self.directory, filename)
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

    def __del__(self):
        self.audio.terminate()

# Test 
if __name__ == "__main__":
    ctrl = AUDIO_Controller(device_index=1)
    try:
        file_path = ctrl.listen()
        ctrl.play(file_path)
    except Exception as e:
        print(f"❌ Erreur : {e}")