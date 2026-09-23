from datetime import date, time

import pytest

from main.agents.email_agent.mail_handler.mail_handler import ReceivedEmail
from main.agents.planner_agent.planner_agent import PlannerAgent
from main.agents.planner_agent.planner_controller.planner_controller import Appointment, PlannerController
from main.agents.prescription_agent.prescription_agent import Medication, Prescription
from web import app as web_app

COMPLETE = Prescription(patient="Pierre Durand", medications=[Medication(name="Doliprane 1g", dosage="matin et soir", duration="5 jours")])


class FakePrescriptionAgent:
    def __init__(self, prescription, confirmation=True, pdf_dir=None):
        self.prescription = prescription
        self.confirmation = confirmation
        self.pdf_dir = pdf_dir

    def record_dictation(self, stop_flag):
        return "dictation"

    def extract_prescription(self, transcript):
        return self.prescription

    def ask_confirmation(self):
        return self.confirmation

    def generate_pdf(self, prescription):
        return self.pdf_dir / "ordonnance_Pierre_Durand.pdf"


class FakeMailHandler:
    def __init__(self):
        self.moved = []

    def get_unread_emails(self):
        return [ReceivedEmail(id="42", content="...", subject="RDV", sender="claire@example.com", date="Mon, 3 Mar 2025")]

    def get_folders(self):
        return ["INBOX", "RDV"]

    def move_email(self, email_id, folder):
        self.moved.append((email_id, folder))


class FakeMailAgent:
    def __init__(self):
        self.handler = FakeMailHandler()

    def summarize_email(self, email):
        return "Demande de report du rendez-vous."

    def classify_mailbox(self):
        return ["RDV"]


@pytest.fixture
def planner(tmp_path):
    controller = PlannerController(year=2025, path=tmp_path)
    controller.add_appointment(Appointment(
        name="Emma", surname="Lefevre", date=date(2025, 3, 3), mail="emma@example.com",
        description="Consultation fatigue", start_time=time(11)))
    return PlannerAgent(client=object(), controller=controller, audio=object())


@pytest.fixture
def client(monkeypatch, planner):
    monkeypatch.setattr(web_app, "planner", lambda: planner)
    monkeypatch.setattr(web_app, "mail_agent", FakeMailAgent)
    web_app.app.config["TESTING"] = True
    return web_app.app.test_client()


def test_home_links_to_every_feature(client):
    page = client.get("/").get_data(as_text=True)

    for path in ("/prescription", "/mail", "/planner/"):
        assert f'href="{path}"' in page


def test_appointments_page_lists_the_month(client):
    page = client.get("/planner/appointments?month=3").get_data(as_text=True)

    assert "Emma Lefevre" in page
    assert "11:00" in page


def test_available_page_hides_booked_slots(client):
    page = client.get("/planner/available?month=3").get_data(as_text=True)

    assert "Créneaux libres en mars 2025" in page
    assert "Lundi 3" in page
    assert "10:30, 11:30" in page


def test_reschedule_unknown_appointment_returns_404(client):
    assert client.get("/planner/reschedule/99").status_code == 404


def test_reschedule_redirects_with_a_confirmation(client, monkeypatch, planner):
    def fake_reschedule(appointment):
        appointment.date, appointment.start_time = date(2025, 4, 2), time(9, 30)
        return appointment
    monkeypatch.setattr(planner, "reschedule_appointment", fake_reschedule)

    response = client.get("/planner/reschedule/0", follow_redirects=True)

    assert "Rendez-vous reprogrammé le 02/04/2025 à 09:30." in response.get_data(as_text=True)


def test_prescription_with_missing_fields_asks_to_start_again(client, monkeypatch):
    incomplete = Prescription(patient="Pierre Durand", medications=[])
    monkeypatch.setattr(web_app, "prescription_agent", lambda: FakePrescriptionAgent(incomplete))

    page = client.post("/prescription").get_data(as_text=True)

    assert "Informations incomplètes" in page
    assert "Oui, recommencer" in page


def test_confirmed_prescription_offers_the_pdf(client, monkeypatch, tmp_path):
    monkeypatch.setattr(web_app, "prescription_agent", lambda: FakePrescriptionAgent(COMPLETE, pdf_dir=tmp_path))

    page = client.post("/prescription").get_data(as_text=True)

    assert "/prescriptions/ordonnance_Pierre_Durand.pdf" in page
    assert "Doliprane 1g" in page


def test_refused_prescription_asks_for_a_new_dictation(client, monkeypatch):
    monkeypatch.setattr(web_app, "prescription_agent", lambda: FakePrescriptionAgent(COMPLETE, confirmation=False))

    page = client.post("/prescription").get_data(as_text=True)

    assert "Correction demandée" in page


def test_stop_sets_the_recording_flag(client):
    web_app.stop_flag.clear()

    assert client.post("/stop").get_json() == {"status": "stopped"}
    assert web_app.stop_flag.is_set()
    web_app.stop_flag.clear()


def test_mail_summaries(client):
    page = client.get("/mail?action=summarize").get_data(as_text=True)

    assert "claire@example.com" in page
    assert "Demande de report du rendez-vous." in page


def test_mail_auto_sort_reports_destinations(client):
    page = client.post("/mail", data={"auto_sort": "1"}).get_data(as_text=True)

    assert "Mail déplacé dans : RDV" in page
