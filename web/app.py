import base64
import logging
import os
import re
import secrets
import threading
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from datetime import date, timedelta
from email.utils import parsedate_to_datetime
from functools import cache
from typing import Callable, Optional

from flask import Flask, abort, jsonify, render_template, request, send_from_directory, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from secretary_ai.agents.demo_calendar import generate as generate_demo_calendar
from secretary_ai.agents.demo_mailbox import DemoMailHandler
from secretary_ai.agents.mail_agent import MailAgent
from secretary_ai.agents.mail_handler import ReceivedEmail
from secretary_ai.agents.planner_agent import (
    FRENCH_MONTHS,
    FRENCH_WEEKDAYS,
    PlannerAgent,
    RescheduleConversation,
    current_date,
)
from secretary_ai.agents.planner_controller import DOCTORS, Appointment
from secretary_ai.agents.prescription_agent import Prescription, PrescriptionAgent, download_name
from secretary_ai.ai.api_client import BROWSER_TTS
from secretary_ai.ai.base_model import BaseAIModel
from secretary_ai.config import PRESCRIPTIONS_DIR

# The public demo uses a fictional mailbox and caps AI calls per visitor to keep API costs bounded.
DEMO_MODE = os.getenv("DEMO_MODE") == "1"
AI_REQUESTS_PER_HOUR = int(os.getenv("AI_REQUESTS_PER_HOUR", "30" if DEMO_MODE else "0"))
LIMIT_MESSAGE = "Limite d'utilisation de la démo atteinte, réessayez dans une heure."
MAX_CONVERSATIONS = 200

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
if DEMO_MODE:
    # The demo is served behind the hosting provider's reverse proxy.
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1)

_ai_calls: defaultdict[str, deque] = defaultdict(deque)
_ai_calls_lock = threading.Lock()
_conversations: OrderedDict[str, RescheduleConversation] = OrderedDict()
_conversations_lock = threading.Lock()
_summaries: OrderedDict[str, str] = OrderedDict()
MAX_SUMMARIES = 500


# Agents are created on first use so that each page works even if another agent is not configured.
@cache
def mail_agent() -> MailAgent:
    return MailAgent(handler=DemoMailHandler()) if DEMO_MODE else MailAgent()


@cache
def planner() -> PlannerAgent:
    agent = PlannerAgent()
    if DEMO_MODE:
        # Every start of the demo gets a fresh fictional calendar around today's date.
        agent.controller.replace_all(generate_demo_calendar(current_date()))
    return agent


@cache
def prescription_agent() -> PrescriptionAgent:
    return PrescriptionAgent()


@app.template_filter("month_label")
def month_label(month: date) -> str:
    return f"{FRENCH_MONTHS[month.month - 1]} {month.year}"


@app.template_filter("day_label")
def day_label(day: date) -> str:
    return f"{FRENCH_WEEKDAYS[day.weekday()].capitalize()} {'1er' if day.day == 1 else day.day}"


@app.context_processor
def template_constants():
    return {"demo_mode": DEMO_MODE, "doctors": DOCTORS}


def over_ai_limit() -> bool:
    if not AI_REQUESTS_PER_HOUR:
        return False
    now = time.monotonic()
    with _ai_calls_lock:
        calls = _ai_calls[request.remote_addr]
        while calls and now - calls[0] > 3600:
            calls.popleft()
        if len(calls) >= AI_REQUESTS_PER_HOUR:
            return True
        calls.append(now)
        return False


def api_error(message: str, status: int = 400):
    return jsonify(error=message), status


@app.errorhandler(413)
def payload_too_large(error):
    return api_error("Enregistrement trop long.", 413) if request.path.startswith("/api/") else error


@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith("/api/"):
        return api_error("Le service est momentanément indisponible, réessayez.", 500)
    return error


def read_speech_or_text(transcribe: Callable[[bytes, str], str]) -> str:
    """The text typed in the page, or else the transcription of the uploaded recording."""
    text = (request.form.get("text") or "").strip()
    if text:
        return text
    audio = request.files.get("audio")
    if audio is None:
        raise ValueError("Aucun enregistrement ni texte reçu.")
    text = transcribe(audio.read(), audio.filename or "audio.webm").strip()
    # Speech-to-text models return "..." or similar on silence.
    if not re.search(r"\w", text):
        raise ValueError("Aucune parole détectée, réessayez.")
    return text


def speech_data_url(client: BaseAIModel, text: str) -> Optional[str]:
    """The answer as WAV audio, or None to let the browser read the text aloud."""
    if getattr(client, "tts_engine", None) == BROWSER_TTS:
        return None
    try:
        audio = client.synthesize(text)
    except Exception:
        logging.exception("Speech synthesis failed, answering with text only.")
        return None
    return "data:audio/wav;base64," + base64.b64encode(audio).decode()


@app.route("/")
def home():
    return render_template("home.html")


# Prescriptions

def prescription_payload(heard: str, prescription: Optional[Prescription]) -> dict:
    return {
        "heard": heard,
        "prescription": prescription.model_dump() if prescription else None,
        "missing": prescription.missing_fields() if prescription else ["le nom du patient", "au moins un médicament"],
    }


@app.route("/prescription")
def prescription():
    session.pop("prescription", None)
    return render_template("prescription.html")


@app.post("/api/prescription/dictation")
def prescription_dictation():
    if over_ai_limit():
        return api_error(LIMIT_MESSAGE, 429)
    agent = prescription_agent()
    try:
        transcript = read_speech_or_text(agent.transcribe)
    except ValueError as error:
        return api_error(str(error))
    result = agent.extract_prescription(transcript)
    session["prescription"] = result.model_dump() if result else None
    return jsonify(prescription_payload(transcript, result))


@app.post("/api/prescription/correction")
def prescription_correction():
    if over_ai_limit():
        return api_error(LIMIT_MESSAGE, 429)
    if not session.get("prescription"):
        return api_error("Aucune ordonnance à corriger, commencez par la dictée.")
    agent = prescription_agent()
    try:
        correction = read_speech_or_text(agent.transcribe)
    except ValueError as error:
        return api_error(str(error))
    result = agent.apply_correction(Prescription.model_validate(session["prescription"]), correction)
    session["prescription"] = result.model_dump()
    return jsonify(prescription_payload(correction, result))


@app.post("/api/prescription/pdf")
def prescription_pdf():
    if not session.get("prescription"):
        return api_error("Aucune ordonnance à générer, commencez par la dictée.")
    result = Prescription.model_validate(session["prescription"])
    if not result.is_complete():
        return api_error("L'ordonnance est incomplète.")
    path = prescription_agent().generate_pdf(result)
    return jsonify(url=url_for("download_prescription", filename=path.name))


@app.route("/prescriptions/<path:filename>")
def download_prescription(filename):
    return send_from_directory(PRESCRIPTIONS_DIR, filename, as_attachment=True, download_name=download_name(filename))


# Mail

@app.template_filter("mail_date")
def mail_date(value: str) -> str:
    """ "Mon, 21 Sep 2026 08:12:00 +0200" as "lundi 21 septembre 2026 à 08:12"."""
    try:
        sent = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return value
    return (f"{FRENCH_WEEKDAYS[sent.weekday()]} {sent.day} {FRENCH_MONTHS[sent.month - 1]} {sent.year} "
            f"à {sent:%H:%M}")


def summarize(agent: MailAgent, email: ReceivedEmail) -> str:
    # Summaries are kept, so that moving one email does not summarize the whole inbox again.
    key = f"{email.id}:{email.subject}"
    if key not in _summaries:
        _summaries[key] = agent.summarize_email(email) or "Ce message ne peut pas être résumé."
        while len(_summaries) > MAX_SUMMARIES:
            _summaries.popitem(last=False)
    return _summaries[key]


def sort_message(email: ReceivedEmail, folder: str) -> str:
    if folder == "INBOX":
        return f"« {email.subject} » laissé dans la boîte de réception"
    return f"« {email.subject} » rangé dans : {folder}"


@app.route("/mail", methods=["GET", "POST"])
def mail():
    agent = mail_agent()
    messages = []
    show_summaries = request.args.get("action") == "summarize"
    auto_sort = request.method == "POST" and "auto_sort" in request.form

    if request.method == "POST" and request.form.get("email_id"):
        agent.handler.move_email(request.form["email_id"], request.form["target_folder"])
        messages = [f"Mail déplacé dans : {request.form['target_folder']}"]
        show_summaries = True

    if (auto_sort or show_summaries) and over_ai_limit():
        return render_template("mail.html", mode=None, mails=[], folders=[], messages=messages, error=LIMIT_MESSAGE)

    mails, error = [], None
    try:
        if auto_sort:
            messages = [sort_message(email, folder) for email, folder in agent.classify_mailbox()] or ["Aucun mail à trier."]
        if show_summaries:
            mails = [{**email.model_dump(), "summary": summarize(agent, email)}
                     for email in agent.handler.get_unread_emails()]
    except Exception:
        logging.exception("The mail assistant failed.")
        error = "Le service d'IA est momentanément indisponible, réessayez dans un instant."

    return render_template("mail.html", mode="summarize" if show_summaries and not error else None, mails=mails,
                           folders=agent.handler.get_folders(), messages=messages, error=error)


# Planner

PAST_APPOINTMENT = "Ce rendez-vous est passé, il ne peut plus être reprogrammé."


def find_appointment(appt_id: str) -> Appointment:
    appointment = planner().controller.find(appt_id)
    if appointment is None:
        abort(404)
    return appointment


def is_upcoming(appointment: Appointment) -> bool:
    return appointment.date > current_date()


def this_month() -> date:
    return current_date().replace(day=1)


def shift_month(month: date, months: int) -> date:
    index = month.year * 12 + month.month - 1 + months
    return date(index // 12, index % 12 + 1, 1)


def selected_month() -> date:
    """The month given as ?month=YYYY-MM, or the current one."""
    try:
        year, month = map(int, request.args.get("month", "").split("-"))
        return date(year, month, 1)
    except ValueError:
        return this_month()


def month_range(first: date, last: date) -> list[date]:
    months = []
    while first <= last:
        months.append(first)
        first = shift_month(first, 1)
    return months


def selected_doctor() -> Optional[str]:
    doctor = request.args.get("doctor")
    return doctor if doctor in DOCTORS else None


@app.route("/planner/")
def planner_index():
    controller = planner().controller
    counts = controller.months()
    first, last = min([*counts, this_month()]), max([*counts, this_month()])
    # Month labels for each choice of doctor, so that the page can update them without reloading.
    labels = {
        doctor or "": {f"{m:%Y-%m}": month_option(m, controller.months(doctor).get(m, 0)) for m in month_range(first, last)}
        for doctor in [None, *DOCTORS]
    }
    return render_template("planner.html", months=month_range(first, last), labels=labels,
                           future_months=month_range(this_month(), last), selected=this_month())


def month_option(month: date, count: int) -> str:
    label = month_label(month).capitalize()
    return f"{label} ({count} rendez-vous)" if count else label


@app.route("/planner/appointments")
def show_appointments():
    month, doctor = selected_month(), selected_doctor()
    appointments_by_day = {}
    for appointment in planner().controller.all_appointments():
        if appointment.date.replace(day=1) == month and doctor in (None, appointment.doctor):
            appointments_by_day.setdefault(appointment.date, []).append(
                {"upcoming": is_upcoming(appointment), **appointment.model_dump()})
    return render_template("appointments.html", appointments_by_day=appointments_by_day, month=month,
                           doctor=doctor, count=sum(map(len, appointments_by_day.values())),
                           previous=shift_month(month, -1), next=shift_month(month, 1))


@app.route("/planner/available")
def show_available():
    month, doctor = selected_month(), selected_doctor() or next(iter(DOCTORS))
    # Only future days can still be booked.
    first_day = max(month, current_date() + timedelta(days=1))
    slots = {day: times for day, times in planner().get_available_timeslots(first_day, doctor).items()
             if day.replace(day=1) == month}
    return render_template("available.html", slots=slots, month=month, doctor=doctor,
                           past=month < this_month())


@app.route("/planner/reschedule/<appt_id>")
def reschedule(appt_id):
    appointment = find_appointment(appt_id)
    return render_template("reschedule.html", appointment=appointment, upcoming=is_upcoming(appointment),
                           past_message=PAST_APPOINTMENT)


@app.post("/api/reschedule/<appt_id>/start")
def reschedule_start(appt_id):
    appointment = find_appointment(appt_id)
    if not is_upcoming(appointment):
        return api_error(PAST_APPOINTMENT)
    if over_ai_limit():
        return api_error(LIMIT_MESSAGE, 429)
    agent = planner()
    conversation, reply = agent.start_rescheduling(appointment)
    conversation_id = uuid.uuid4().hex
    with _conversations_lock:
        _conversations[conversation_id] = conversation
        while len(_conversations) > MAX_CONVERSATIONS:
            _conversations.popitem(last=False)
    return jsonify(conversation_id=conversation_id, reply=reply, audio=speech_data_url(agent.client, reply))


@app.post("/api/reschedule/<conversation_id>/message")
def reschedule_message(conversation_id):
    if over_ai_limit():
        return api_error(LIMIT_MESSAGE, 429)
    conversation = _conversations.get(conversation_id)
    if conversation is None:
        return api_error("Conversation expirée, rechargez la page.", 404)
    if conversation.done:
        return api_error("Cette conversation est terminée.")
    agent = planner()
    try:
        text = read_speech_or_text(agent.client.transcribe)
    except ValueError as error:
        return api_error(str(error))
    reply = agent.handle_patient_message(conversation, text)
    payload = {"patient": text, "reply": reply, "audio": speech_data_url(agent.client, reply), "done": conversation.done}
    if conversation.done:
        appointment = conversation.appointment
        with_doctor = f" avec {appointment.doctor}" if appointment.doctor else ""
        payload["summary"] = (f"Rendez-vous reprogrammé le {appointment.date:%d/%m/%Y} "
                              f"à {appointment.start_time:%H:%M}{with_doctor}.")
        payload["next"] = url_for("show_appointments", month=f"{appointment.date:%Y-%m}", doctor=appointment.doctor)
    return jsonify(payload)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
