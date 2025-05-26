
import pyaudio
import wave
import numpy as np
import time

class AUDIO_Controller:
    def __init__(self, filename="output.wav", rate=16000, channels=1, chunk=1024, threshold=500, silence_duration=2.0):
        self.filename = filename
        self.rate = rate
        self.channels = channels
        self.chunk = chunk
        self.threshold = threshold
        self.silence_duration = silence_duration
        self.format = pyaudio.paInt16
        self.audio = pyaudio.PyAudio()

    def _rms(self, data):
        samples = np.frombuffer(data, dtype=np.int16)
        return np.sqrt(np.mean(samples**2))

    def listen(self):
        stream = self.audio.open(format=self.format,
                                 channels=self.channels,
                                 rate=self.rate,
                                 input=True,
                                 frames_per_buffer=self.chunk)

        print("En attente de la voix...")

        frames = []
        recording = False
        last_sound_time = time.time()

        try:
            while True:
                data = stream.read(self.chunk)
                energy = self._rms(data)

                if energy > self.threshold:
                    if not recording:
                        print("Début de l'enregistrement.")
                    recording = True
                    last_sound_time = time.time()
                    frames.append(data)
                elif recording:
                    frames.append(data)
                    if time.time() - last_sound_time > self.silence_duration:
                        print("Fin de l'enregistrement.")
                        break
        finally:
            stream.stop_stream()
            stream.close()

        if frames:
            with wave.open(self.filename, 'wb') as wf:
                wf.setnchannels(self.channels)
                wf.setsampwidth(self.audio.get_sample_size(self.format))
                wf.setframerate(self.rate)
                wf.writeframes(b''.join(frames))
            print("Fichier enregistré :", self.filename)
        else:
            print("Aucun son détecté.")

    def play(self):
        with wave.open(self.filename, 'rb') as wf:
            stream = self.audio.open(format=self.audio.get_format_from_width(wf.getsampwidth()),
                                     channels=wf.getnchannels(),
                                     rate=wf.getframerate(),
                                     output=True)

            data = wf.readframes(self.chunk)
            while data:
                stream.write(data)
                data = wf.readframes(self.chunk)

            stream.stop_stream()
            stream.close()
            print("Lecture terminée.")

    def continuous_listening(self):
        pass

    def __del__(self):
        self.audio.terminate()



if __name__ == "__main__":
    pass