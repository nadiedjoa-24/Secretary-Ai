// Microphone recording and API helpers shared by the voice pages.

class VoiceRecorder {
    async start() {
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.chunks = [];
        this.recorder = new MediaRecorder(this.stream);
        this.recorder.addEventListener("dataavailable", (event) => this.chunks.push(event.data));
        this.recorder.start();
    }

    stop() {
        return new Promise((resolve) => {
            this.recorder.addEventListener("stop", () => {
                this.stream.getTracks().forEach((track) => track.stop());
                resolve(new Blob(this.chunks, { type: this.recorder.mimeType }));
            }, { once: true });
            this.recorder.stop();
        });
    }

    get recording() {
        return this.recorder !== undefined && this.recorder.state === "recording";
    }
}

function audioFilename(blob) {
    if (blob.type.includes("mp4")) return "audio.mp4";
    if (blob.type.includes("ogg")) return "audio.ogg";
    return "audio.webm";
}

async function postToApi(url, { audio, text } = {}) {
    const form = new FormData();
    if (audio) form.append("audio", audio, audioFilename(audio));
    if (text) form.append("text", text);
    const response = await fetch(url, { method: "POST", body: form });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || "Erreur inattendue, réessayez.");
    return data;
}

function frenchVoice() {
    const voices = speechSynthesis.getVoices().filter((voice) => voice.lang.startsWith("fr"));
    return voices.find((voice) => /natural|google/i.test(voice.name)) || voices[0];
}

let playing = null;

// Stops the assistant's voice, for instance when the user starts answering.
function stopSpeaking() {
    if (playing) playing.pause();
    playing = null;
    if ("speechSynthesis" in window) speechSynthesis.cancel();
}

// Plays the audio synthesized by the server, or reads `text` with the browser's own French voice.
function speak(text, audioUrl) {
    stopSpeaking();
    if (audioUrl) {
        playing = new Audio(audioUrl);
        playing.play().catch(() => {});
        return;
    }
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.lang = "fr-FR";
    utterance.voice = frenchVoice() || null;
    speechSynthesis.speak(utterance);
}

// Browsers load their voice list asynchronously.
if ("speechSynthesis" in window) speechSynthesis.getVoices();

// Turns `button` into a start/stop toggle and passes the finished recording to `onRecording`.
function bindRecordButton(button, labels, onRecording, onError) {
    const recorder = new VoiceRecorder();
    let starting = false;
    button.addEventListener("click", async () => {
        if (starting) return;  // the browser is still opening the microphone
        if (recorder.recording) {
            button.textContent = labels.idle;
            button.classList.remove("recording");
            onRecording(await recorder.stop());
            return;
        }
        stopSpeaking();  // so that the recording only picks up the user
        starting = true;
        try {
            await recorder.start();
        } catch {
            onError("Micro indisponible ou refusé. Vous pouvez utiliser la saisie au clavier.");
            return;
        } finally {
            starting = false;
        }
        button.textContent = labels.recording;
        button.classList.add("recording");
    });
}

// Sends the text typed in `form` and clears the field.
function bindTextForm(form, onText) {
    form.addEventListener("submit", (event) => {
        event.preventDefault();
        const input = form.elements.text;
        const text = input.value.trim();
        if (!text) return;
        stopSpeaking();
        input.value = "";
        onText(text);
    });
}
