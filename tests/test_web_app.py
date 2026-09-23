import io
from datetime import date, time

import pytest

from secretary_ai.agents import planner_agent
from secretary_ai.agents.mail_handler import ReceivedEmail
from secretary_ai.agents.planner_agent import PlannerAgent, RescheduleDecision
from secretary_ai.agents.planner_controller import Appointment, PlannerController
from secretary_ai.agents.prescription_agent import Medication, Prescription
from secretary_ai.ai.base_model import Message
from web import app as web_app

DOLIPRANE = Medication(name="Doliprane 1g", dosage="matin et soir", duration="5 jours")
TODAY = date(2025, 3, 1)


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
        return self.pdf_dir / "ordonnance_Pierre_Durand_2025-03-03_0a1b2c3d.pdf"


CLAIRE = ReceivedEmail(id="42", content="...", subject="Report de rendez-vous", sender="claire@example.com",
                       date="Mon, 3 Mar 2025 08:12:00 +0100")


class FakeMailHandler:
    def get_unread_emails(self):
        return [CLAIRE]

    def get_folders(self):
        return ["INBOX", "RDV"]

    def move_email(self, email_id, folder):
        pass


class FakeMailAgent:
    def __init__(self):
        self.handler = FakeMailHandler()
        self.summaries = 0
        self.fails = False

    def summarize_email(self, email):
        if self.fails:
            raise RuntimeError("API down")
        self.summaries += 1
        return "Demande de report du rendez-vous."

    def classify_mailbox(self):
        return [(CLAIRE, "RDV"), (CLAIRE.model_copy(update={"subject": "Résultats"}), "INBOX")]


@pytest.fixture
def ai():
    return FakeAIClient()


@pytest.fixture
def planner(tmp_path, ai):
    controller = PlannerController(path=tmp_path)
    controller.add_appointment(Appointment(
        id="emma", name="Emma", surname="Lefevre", date=date(2025, 3, 3), mail="emma@example.com",
        description="Consultation fatigue", start_time=time(11), doctor="Dr Claire Morel"))
    controller.add_appointment(Appointment(
        id="hugo", name="Hugo", surname="Petit", date=date(2025, 2, 10), mail="hugo@example.com",
        description="Détartrage", start_time=time(9), doctor="Dr Sarah Benhamou"))
    return PlannerAgent(client=ai, controller=controller, audio=object())


@pytest.fixture
def mail():
    return FakeMailAgent()


@pytest.fixture
def client(monkeypatch, planner, mail, tmp_path):
    for module in (web_app, planner_agent):
        monkeypatch.setattr(module, "current_date", lambda: TODAY)
    monkeypatch.setattr(web_app, "planner", lambda: planner)
    monkeypatch.setattr(web_app, "mail_agent", lambda: mail)
    web_app._summaries.clear()
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

def test_appointments_page_lists_the_month_with_the_doctor(client):
    page = client.get("/planner/appointments?month=2025-03").get_data(as_text=True)

    assert "Rendez-vous en mars 2025" in page
    assert "Emma Lefevre" in page
    assert "avec Dr Claire Morel" in page
    assert "/planner/reschedule/emma" in page


def test_past_appointments_cannot_be_rescheduled(client):
    page = client.get("/planner/appointments?month=2025-02").get_data(as_text=True)

    assert "Hugo Petit" in page
    assert "Passé" in page
    assert "/planner/reschedule/" not in page


def test_appointments_can_be_filtered_by_doctor(client):
    page = client.get("/planner/appointments?month=2025-03&doctor=Dr+Julien+Roux").get_data(as_text=True)

    assert "Emma Lefevre" not in page
    assert "Aucun rendez-vous pour ce mois." in page


def test_planner_opens_on_the_current_month_and_counts_appointments(client):
    page = client.get("/planner/").get_data(as_text=True)

    assert '<option value="2025-03" selected>' in page
    assert "Mars 2025 (1 rendez-vous)" in page
    assert "Février 2025 (1 rendez-vous)" in page
    assert "Dr Sarah Benhamou, chirurgienne-dentiste" in page


def test_invalid_month_falls_back_to_the_current_one(client):
    assert "Rendez-vous en mars 2025" in client.get("/planner/appointments?month=abc").get_data(as_text=True)


def test_available_page_shows_the_free_slots_of_one_doctor(client):
    morel = client.get("/planner/available?month=2025-03&doctor=Dr+Claire+Morel").get_data(as_text=True)
    roux = client.get("/planner/available?month=2025-03&doctor=Dr+Julien+Roux").get_data(as_text=True)

    assert "Créneaux libres en mars 2025" in morel
    assert "Lundi 3" in morel
    assert "10:30, 11:30" in morel
    assert "10:30, 11:00, 11:30" in roux


def test_available_page_of_a_past_month(client):
    page = client.get("/planner/available?month=2025-01").get_data(as_text=True)

    assert "Ce mois est passé." in page


def test_month_counts_follow_each_doctor(client):
    page = client.get("/planner/").get_data(as_text=True)

    assert '"Dr Claire Morel": {"2025-02": "F\\u00e9vrier 2025", "2025-03": "Mars 2025 (1 rendez-vous)"}' in page


def test_free_slots_can_only_be_asked_for_the_coming_months(client):
    page = client.get("/planner/").get_data(as_text=True)
    available_form = page.split('id="month-available"')[1].split("</select>")[0]

    assert "2025-03" in available_form
    assert "2025-02" not in available_form


def test_appointments_page_links_to_the_neighbouring_months(client):
    page = client.get("/planner/appointments?month=2025-01&doctor=Marc+Lefort").get_data(as_text=True)

    assert "month=2024-12&amp;doctor=Marc+Lefort" in page
    assert "month=2025-02&amp;doctor=Marc+Lefort" in page


def test_past_appointment_cannot_be_rescheduled_through_its_url(client):
    page = client.get("/planner/reschedule/hugo").get_data(as_text=True)
    response = client.post("/api/reschedule/hugo/start")

    assert "ne peut plus être reprogrammé" in page
    assert "Répondre à la voix" not in page
    assert response.status_code == 400


def test_reschedule_page_describes_the_appointment(client):
    page = client.get("/planner/reschedule/emma").get_data(as_text=True)

    assert "Emma Lefevre" in page
    assert "lundi 3 mars 2025 à 11:00 avec Dr Claire Morel" in page


def test_reschedule_unknown_appointment_returns_404(client):
    assert client.get("/planner/reschedule/unknown").status_code == 404
    assert client.post("/api/reschedule/unknown/start").status_code == 404


def test_conversation_start_returns_the_first_reply_with_audio(client):
    data = client.post("/api/reschedule/emma/start").get_json()

    assert data["reply"] == "Quel jour vous conviendrait ?"
    assert data["audio"].startswith("data:audio/wav;base64,")
    assert data["conversation_id"]


def test_typed_message_continues_the_conversation(client):
    conversation_id = client.post("/api/reschedule/emma/start").get_json()["conversation_id"]

    data = client.post(f"/api/reschedule/{conversation_id}/message", data={"text": "Plutôt jeudi"}).get_json()

    assert data["patient"] == "Plutôt jeudi"
    assert data["done"] is False


def test_recorded_message_is_transcribed(client):
    conversation_id = client.post("/api/reschedule/emma/start").get_json()["conversation_id"]

    response = client.post(f"/api/reschedule/{conversation_id}/message",
                           data={"audio": (io.BytesIO(b"fake webm"), "audio.webm")})

    assert response.get_json()["patient"] == "transcription de audio.webm"


def test_silent_recording_is_rejected(client, ai):
    ai.transcribe = lambda audio, filename: " ... "
    conversation_id = client.post("/api/reschedule/emma/start").get_json()["conversation_id"]

    response = client.post(f"/api/reschedule/{conversation_id}/message",
                           data={"audio": (io.BytesIO(b"silence"), "audio.webm")})

    assert response.status_code == 400
    assert response.get_json()["error"] == "Aucune parole détectée, réessayez."


def test_confirmed_slot_ends_the_conversation(client, ai, planner):
    ai.decisions = [RescheduleDecision(new_date=date(2025, 3, 5), new_time=time(9, 30), final=True)]
    conversation_id = client.post("/api/reschedule/emma/start").get_json()["conversation_id"]

    data = client.post(f"/api/reschedule/{conversation_id}/message", data={"text": "Mercredi 9h30"}).get_json()

    assert data["done"] is True
    assert data["summary"] == "Rendez-vous reprogrammé le 05/03/2025 à 09:30 avec Dr Claire Morel."
    assert data["next"] == "/planner/appointments?month=2025-03&doctor=Dr+Claire+Morel"
    assert planner.controller.get_day_appointments(date(2025, 3, 5))[0].name == "Emma"


def test_speech_failure_still_returns_the_text(client, ai):
    ai.speech_fails = True

    data = client.post("/api/reschedule/emma/start").get_json()

    assert data["reply"] == "Quel jour vous conviendrait ?"
    assert data["audio"] is None


def test_browser_voice_sends_no_audio(client, ai):
    ai.tts_engine = "browser"
    ai.synthesize = None  # must not be called

    data = client.post("/api/reschedule/emma/start").get_json()

    assert data["reply"] == "Quel jour vous conviendrait ?"
    assert data["audio"] is None


def test_unknown_conversation_returns_404(client):
    response = client.post("/api/reschedule/unknown/message", data={"text": "Bonjour"})

    assert response.status_code == 404
    assert "error" in response.get_json()


def test_message_without_audio_or_text_is_rejected(client):
    conversation_id = client.post("/api/reschedule/emma/start").get_json()["conversation_id"]

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

    assert data["url"] == "/prescriptions/ordonnance_Pierre_Durand_2025-03-03_0a1b2c3d.pdf"


def test_downloaded_pdf_is_named_without_its_random_suffix(client, monkeypatch, tmp_path):
    monkeypatch.setattr(web_app, "PRESCRIPTIONS_DIR", tmp_path)
    (tmp_path / "ordonnance_Pierre_Durand_2025-03-03_0a1b2c3d.pdf").write_bytes(b"%PDF")

    response = client.get("/prescriptions/ordonnance_Pierre_Durand_2025-03-03_0a1b2c3d.pdf")

    assert response.status_code == 200
    assert "filename=ordonnance_Pierre_Durand_2025-03-03.pdf" in response.headers["Content-Disposition"]


# Mail

def test_mail_summaries(client):
    page = client.get("/mail?action=summarize").get_data(as_text=True)

    assert "claire@example.com" in page
    assert "Report de rendez-vous" in page
    assert "Demande de report du rendez-vous." in page
    assert "lundi 3 mars 2025 à 08:12" in page


def test_summaries_are_not_computed_twice(client, mail):
    client.get("/mail?action=summarize")
    client.post("/mail", data={"email_id": "7", "target_folder": "RDV"})

    assert mail.summaries == 1


def test_mail_auto_sort_reports_each_email(client):
    page = client.post("/mail", data={"auto_sort": "1"}).get_data(as_text=True)

    assert "« Report de rendez-vous » rangé dans : RDV" in page
    assert "« Résultats » laissé dans la boîte de réception" in page


def test_mail_page_survives_an_ai_failure(client, mail):
    mail.fails = True

    response = client.get("/mail?action=summarize")

    assert response.status_code == 200
    assert "momentanément indisponible" in response.get_data(as_text=True)


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
