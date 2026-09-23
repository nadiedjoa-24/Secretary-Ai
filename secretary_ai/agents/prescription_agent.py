import logging
import re
import unicodedata
import uuid
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from secretary_ai.ai.api_client import APIClient
from secretary_ai.ai.base_model import BaseAIModel, Message
from secretary_ai.config import PRESCRIPTIONS_DIR

if TYPE_CHECKING:
    from secretary_ai.ai.audio_controller import AudioController

logger = logging.getLogger(__name__)

STOP_WORDS = ("c'est tout", "stop")
CORRECTION_WORDS = ("corriger", "modifier", "changer", "il y a", "prénom", "nom de famille", "deux l")
YES_WORDS = ("oui", "ok", "yes")
NO_WORDS = ("non", "no")

MEDICAL_CENTER = [
    "Centre Médical Saint Jean",
    "23 rue des Lilas, Yerres 91330",
    "Tél : 01 23 45 67 89",
    "Dentiste, Médecine Générale, Kinésithérapeute",
]

EXTRACTION_PROMPT = (
    "You extract prescription data from a doctor's dictation, transcribed from French speech.\n"
    "Fill in the patient's full name and, for each medication, its name, dosage and duration, "
    "copying the wording of the dictation in French.\n"
    "Only use information that is explicitly stated. Never guess, complete or correct anything: "
    "leave a field empty when it is missing or ambiguous.\n"
    'Example: "Je suis Pierre Durand, Doliprane 1g matin et soir pendant 5 jours" gives '
    'patient "Pierre Durand" and one medication: name "Doliprane 1g", dosage "matin et soir", duration "5 jours".'
)

CORRECTION_PROMPT = (
    "You update the data of a prescription according to a correction from the doctor, in French: it either fixes "
    "a field or adds missing information. Change nothing else.\n"
    'Examples: "il y a deux L à Olivier" turns the patient "Antoine Olivier" into "Antoine Ollivier"; '
    '"le patient s\'appelle Pierre Durand" fills in an empty patient name; '
    '"Doliprane pendant 7 jours" sets the duration of the Doliprane.'
)


class Medication(BaseModel):
    name: str
    dosage: str
    duration: str


class Prescription(BaseModel):
    patient: str
    medications: List[Medication]

    def missing_fields(self) -> List[str]:
        """What still has to be dictated, worded for the French user interface."""
        missing = [] if self.patient else ["le nom du patient"]
        if not self.medications:
            missing.append("au moins un médicament")
        for medication in self.medications:
            label = medication.name or "un médicament"
            if not medication.name:
                missing.append("le nom d'un médicament")
            if not medication.dosage:
                missing.append(f"la posologie de {label}")
            if not medication.duration:
                missing.append(f"la durée de {label}")
        return missing

    def is_complete(self) -> bool:
        return not self.missing_fields()

    def summary(self) -> str:
        lines = [f"Patient : {self.patient}", "Médicaments prescrits :"]
        lines += [f"  {i}. {m.name} : {m.dosage}, pendant {m.duration}" for i, m in enumerate(self.medications, 1)]
        return "\n".join(lines)


def safe_filename(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "_", ascii_text).strip("_") or "patient"


def download_name(filename: str) -> str:
    """Name shown to the user for a stored prescription, without its random suffix."""
    return re.sub(r"_[0-9a-f]{8}(\.pdf)$", r"\1", filename)


class PrescriptionAgent:
    """Turns a doctor's spoken dictation into a PDF prescription."""

    def __init__(self, client: Optional[BaseAIModel] = None, audio: Optional["AudioController"] = None):
        self.client = client or APIClient()
        self._audio = audio

    @property
    def audio(self) -> "AudioController":
        """Local microphone and speakers, only used by the command line version."""
        if self._audio is None:
            # Imported here because PyAudio is an optional dependency (the "cli" extra).
            from secretary_ai.ai.audio_controller import AudioController
            self._audio = AudioController()
        return self._audio

    def transcribe(self, audio: bytes, filename: str) -> str:
        return self.client.transcribe(audio, filename)

    def speak(self, text: str) -> None:
        self.audio.play(self.client.tts(text))

    def listen_once(self) -> str:
        try:
            return self.client.stt(self.audio.listen()).content
        except Exception:
            logger.exception("Speech recognition failed.")
            return ""

    def record_dictation(self) -> str:
        """Transcribe the microphone until the doctor says "c'est tout"."""
        segments = []
        while True:
            text = self.client.stt(self.audio.listen()).content
            logger.info("Transcribed: %s", text)
            if any(word in text.lower() for word in STOP_WORDS):
                return " ".join(segments)
            segments.append(text)

    def extract_prescription(self, transcript: str) -> Optional[Prescription]:
        try:
            return self.client.parse(
                [Message(role="system", content=EXTRACTION_PROMPT), Message(role="user", content=transcript)],
                Prescription,
            )
        except Exception:
            logger.exception("Could not extract the prescription from the dictation.")
            return None

    def apply_correction(self, prescription: Prescription, correction: str) -> Prescription:
        try:
            return self.client.parse([
                Message(role="system", content=CORRECTION_PROMPT),
                Message(role="user", content=f"Current data:\n{prescription.model_dump_json()}\n\nCorrection: {correction}"),
            ], Prescription)
        except Exception:
            logger.exception("Could not apply the correction.")
            return prescription

    def ask_confirmation(self) -> bool | str:
        """Listen for "oui" or "non". A spoken correction is returned as text."""
        while True:
            answer = self.listen_once().lower().strip()
            if any(word in answer for word in CORRECTION_WORDS):
                return answer
            if any(word in answer for word in YES_WORDS):
                return True
            if any(word in answer for word in NO_WORDS):
                return False
            logger.info("Answer not understood, listening again.")

    def generate_pdf(self, prescription: Prescription) -> Path:
        if not prescription.is_complete():
            raise ValueError("The prescription is incomplete.")

        PRESCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)
        # The random suffix keeps prescriptions from overwriting each other and makes their URL impossible
        # to guess. It is left out of the name of the downloaded file (see download_name).
        path = PRESCRIPTIONS_DIR / (f"ordonnance_{safe_filename(prescription.patient)}_{date.today().isoformat()}"
                                    f"_{uuid.uuid4().hex[:8]}.pdf")
        pdf = canvas.Canvas(str(path), pagesize=A4)
        _, height = A4

        for i, line in enumerate(MEDICAL_CENTER):
            pdf.drawString(330, 800 - i * 15, line)

        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(50, height - 50, "ORDONNANCE MÉDICALE")
        pdf.setFont("Helvetica", 12)
        pdf.drawString(50, height - 80, f"Date : {date.today().strftime('%d/%m/%Y')}")
        pdf.drawString(50, height - 100, f"Patient : {prescription.patient}")

        pdf.setFont("Helvetica-Bold", 15)
        pdf.drawString(50, height - 220, "Médicaments prescrits :")
        pdf.setFont("Helvetica", 12)
        y = height - 250
        for medication in prescription.medications:
            pdf.drawString(50, y, f"- {medication.name} : {medication.dosage} pendant {medication.duration}")
            y -= 20
        pdf.drawString(350, y - 50, "Signature : ___________")
        pdf.save()
        return path


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    agent = PrescriptionAgent()
    print("Dictate the prescription, then say \"c'est tout\".")
    prescription = agent.extract_prescription(agent.record_dictation())
    while prescription and prescription.is_complete():
        print(prescription.summary())
        print('Say "oui" to generate the PDF, "non" or a correction to change it.')
        answer = agent.ask_confirmation()
        if answer is True:
            print(f"Prescription saved to {agent.generate_pdf(prescription)}")
            break
        correction = answer if isinstance(answer, str) else agent.listen_once()
        prescription = agent.apply_correction(prescription, correction)
    else:
        print("The dictation is incomplete, please start again.")
