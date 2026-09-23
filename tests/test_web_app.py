import io
from datetime import date, time

import pytest

from secretary_ai.agents.mail_handler import ReceivedEmail
from secretary_ai.agents.planner_agent import PlannerAgent, RescheduleDecision
from secretary_ai.agents.planner_controller import Appointment, PlannerController
from secretary_ai.agents.prescription_agent import Medication, Prescription
from secretary_ai.ai.base_model import Message
from web import app as web_app

DOLIPRANE = Medication(name="Doliprane 1g", dosage="matin et soir", duration="5 jours")


class FakeAIClient:
    def __init__(self, decisions=()):
        self.decisions = list(decisions)
        self.speech_fails = False

    def basic(self, messages):
        return Message(role="assistant", content="Quel jour vous conviendrait ?")

    def parse(self, messages, data_model):
        return self.decisions.pop(0) if self.decisions else RescheduleDecision()

    def transcribe(self, audio, filename):
        return f"transcription de {filename}"

    def synthesize(self, text):
        if self.speech_fails:
            raise RuntimeError("TTS down")
        return b"RIFF-fake-wav"


class FakePrescriptionAgent:
    def __init__(self, pdf_dir):
        self.pdf_dir = pdf_dir

    def transcribe(self, audio, filename):
        return "Pierre Durand, Doliprane 1g matin et soir pendant 5 jours"

    def extract_prescription(self, transcript):
        if "Doliprane" not in transcript:
            return Prescription(patient="Pierre Durand", medications=[])
        return Prescription(patient="Pierre Durand", medications=[DOLIPRANE])

    def apply_correction(self, prescription, correction):
        return prescription.model_copy(update={"patient": "Pierre Duran"})

    def generate_pdf(self, prescription):
        return self.pdf_dir / "ordonnance_Pierre_Durand_1234.pdf"


class FakeMailHandler:
    def get_unread_emails(self):
        return [ReceivedEmail(id="42", content="...", subject="Report de rendez-vous",
                              sender="claire@example.com", date="Mon, 3 Mar 2025")]

    def get_folders(self):
        return ["INBOX", "RDV"]

    def move_email(self, email_id, folder):
        pass


class FakeMailAgent:
    def __init__(self):
        self.handler = FakeMailHandler()

    def summarize_email(self, email):
        return "Demande de report du rendez-vous."

    def classify_mailbox(self):
        return ["RDV"]


@pytest.fixture
def ai():
    return FakeAIClient()


@pytest.fixture
def planner(tmp_path, ai):
    controller = PlannerController(year=2025, path=tmp_path)
    controller.add_appointment(Appointment(
        name="Emma", surname="Lefevre", date=date(2025, 3, 3), mail="emma@example.com",
        description="Consultation fatigue", start_time=time(11)))
    return PlannerAgent(client=ai, controller=controller, audio=object())


@pytest.fixture
def client(monkeypatch, planner, tmp_path):
    monkeypatch.setattr(web_app, "planner", lambda: planner)
    monkeypatch.setattr(web_app, "mail_agent", FakeMailAgent)
    monkeypatch.setattr(web_app, "prescription_agent", lambda: FakePrescriptionAgent(tmp_path))
    monkeypatch.setattr(web_app, "AI_REQUESTS_PER_HOUR", 0)
    web_app._conversations.clear()
    web_app._ai_calls.clear()
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


def test_home_links_to_every_feature(client):
    page = client.get("/").get_data(as_text=True)

    for path in ("/prescription", "/mail", "/planner/"):
        assert f'href="{path}"' in page


# Planner

def test_appointments_page_lists_the_month(client):
    page = client.get("/planner/appointments?month=3").get_data(as_text=True)

    assert "Emma Lefevre" in page
    assert "/planner/reschedule/0" in page


def test_available_page_hides_booked_slots(client):
    page = client.get("/planner/available?month=3").get_data(as_text=True)

    assert "Créneaux libres en mars 2025" in page
    assert "Lundi 3" in page
    assert "10:30, 11:30" in page


def test_reschedule_page_describes_the_appointment(client):
    page = client.get("/planner/reschedule/0").get_data(as_text=True)

    assert "Emma Lefevre" in page
    assert "lundi 3 mars à 11:00" in page


def test_reschedule_unknown_appointment_returns_404(client):
    assert client.get("/planner/reschedule/99").status_code == 404
    assert client.post("/api/reschedule/99/start").status_code == 404


def test_conversation_start_returns_the_first_reply_with_audio(client):
    data = client.post("/api/reschedule/0/start").get_json()

    assert data["reply"] == "Quel jour vous conviendrait ?"
    assert data["audio"].startswith("data:audio/wav;base64,")
    assert data["conversation_id"]


def test_typed_message_continues_the_conversation(client):
    conversation_id = client.post("/api/reschedule/0/start").get_json()["conversation_id"]

    data = client.post(f"/api/reschedule/{conversation_id}/message", data={"text": "Plutôt jeudi"}).get_json()

    assert data["patient"] == "Plutôt jeudi"
    assert data["done"] is False


def test_recorded_message_is_transcribed(client):
    conversation_id = client.post("/api/reschedule/0/start").get_json()["conversation_id"]

    response = client.post(f"/api/reschedule/{conversation_id}/message",
                           data={"audio": (io.BytesIO(b"fake webm"), "audio.webm")})

    assert response.get_json()["patient"] == "transcription de audio.webm"


def test_confirmed_slot_ends_the_conversation(client, ai, planner):
    ai.decisions = [RescheduleDecision(new_date=date(2025, 3, 5), new_time=time(9, 30), final=True)]
    conversation_id = client.post("/api/reschedule/0/start").get_json()["conversation_id"]

    data = client.post(f"/api/reschedule/{conversation_id}/message", data={"text": "Mercredi 9h30"}).get_json()

    assert data["done"] is True
    assert data["summary"] == "Rendez-vous reprogrammé le 05/03/2025 à 09:30."
    assert data["next"] == "/planner/appointments?month=3"
    assert planner.controller.get_day_appointments(date(2025, 3, 5))[0].name == "Emma"


def test_speech_failure_still_returns_the_text(client, ai):
    ai.speech_fails = True

    data = client.post("/api/reschedule/0/start").get_json()

    assert data["reply"] == "Quel jour vous conviendrait ?"
    assert data["audio"] is None


def test_unknown_conversation_returns_404(client):
    response = client.post("/api/reschedule/unknown/message", data={"text": "Bonjour"})

    assert response.status_code == 404
    assert "error" in response.get_json()


def test_message_without_audio_or_text_is_rejected(client):
    conversation_id = client.post("/api/reschedule/0/start").get_json()["conversation_id"]

    assert client.post(f"/api/reschedule/{conversation_id}/message").status_code == 400


# Prescriptions

def test_typed_dictation_is_extracted(client):
    data = client.post("/api/prescription/dictation",
                       data={"text": "Pierre Durand, Doliprane 1g matin et soir pendant 5 jours"}).get_json()

    assert data["prescription"]["patient"] == "Pierre Durand"
    assert data["missing"] == []


def test_recorded_dictation_is_transcribed(client):
    data = client.post("/api/prescription/dictation",
                       data={"audio": (io.BytesIO(b"fake webm"), "audio.webm")}).get_json()

    assert data["heard"].startswith("Pierre Durand")


def test_incomplete_dictation_lists_what_is_missing(client):
    data = client.post("/api/prescription/dictation", data={"text": "Pierre Durand"}).get_json()

    assert data["missing"] == ["au moins un médicament"]
    assert client.post("/api/prescription/pdf").status_code == 400


def test_correction_updates_the_prescription(client):
    client.post("/api/prescription/dictation", data={"text": "Pierre Durand, Doliprane 1g"})

    data = client.post("/api/prescription/correction", data={"text": "Durand sans D final"}).get_json()

    assert data["prescription"]["patient"] == "Pierre Duran"


def test_correction_needs_a_dictation_first(client):
    assert client.post("/api/prescription/correction", data={"text": "..."}).status_code == 400


def test_pdf_link_after_a_complete_dictation(client):
    client.post("/api/prescription/dictation", data={"text": "Pierre Durand, Doliprane 1g"})

    data = client.post("/api/prescription/pdf").get_json()

    assert data["url"] == "/prescriptions/ordonnance_Pierre_Durand_1234.pdf"


# Mail

def test_mail_summaries(client):
    page = client.get("/mail?action=summarize").get_data(as_text=True)

    assert "claire@example.com" in page
    assert "Report de rendez-vous" in page
    assert "Demande de report du rendez-vous." in page


def test_mail_auto_sort_reports_destinations(client):
    page = client.post("/mail", data={"auto_sort": "1"}).get_data(as_text=True)

    assert "Mail déplacé dans : RDV" in page


# Demo protections

def test_ai_calls_are_rate_limited(client, monkeypatch):
    monkeypatch.setattr(web_app, "AI_REQUESTS_PER_HOUR", 2)

    statuses = [client.post("/api/prescription/dictation", data={"text": "Pierre Durand"}).status_code
                for _ in range(3)]

    assert statuses == [200, 200, 429]
    assert "Limite" in client.get("/mail?action=summarize").get_data(as_text=True)


def test_oversized_upload_is_rejected(client, monkeypatch):
    monkeypatch.setitem(web_app.app.config, "MAX_CONTENT_LENGTH", 10)

    response = client.post("/api/prescription/dictation",
                           data={"audio": (io.BytesIO(b"x" * 100), "audio.webm")})

    assert response.status_code == 413
    assert "error" in response.get_json()
