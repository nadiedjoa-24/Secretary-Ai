import base64
import logging
import os
import secrets
import threading
import time
import uuid
from collections import OrderedDict, defaultdict, deque
from datetime import date
from functools import cache
from typing import Callable, Optional

from flask import Flask, abort, jsonify, render_template, request, send_from_directory, session, url_for
from werkzeug.middleware.proxy_fix import ProxyFix

from secretary_ai.agents.demo_mailbox import DemoMailHandler
from secretary_ai.agents.mail_agent import MailAgent
from secretary_ai.agents.planner_agent import PlannerAgent, RescheduleConversation
from secretary_ai.agents.planner_controller import Appointment
from secretary_ai.agents.prescription_agent import Prescription, PrescriptionAgent
from secretary_ai.ai.base_model import BaseAIModel
from secretary_ai.config import PRESCRIPTIONS_DIR

PLANNING_YEAR = 2025
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin",
          "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

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


# Agents are created on first use so that each page works even if another agent is not configured.
@cache
def mail_agent() -> MailAgent:
    return MailAgent(handler=DemoMailHandler()) if DEMO_MODE else MailAgent()


@cache
def planner() -> PlannerAgent:
    return PlannerAgent(year=PLANNING_YEAR)


@cache
def prescription_agent() -> PrescriptionAgent:
    return PrescriptionAgent()


@app.template_filter("month_name")
def month_name(month: int) -> str:
    return MONTHS[month - 1]


@app.template_global()
def day_label(month: int, day: int) -> str:
    return f"{WEEKDAYS[date(PLANNING_YEAR, month, day).weekday()]} {day}"


@app.context_processor
def template_constants():
    return {"year": PLANNING_YEAR, "demo_mode": DEMO_MODE}


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
    if not text:
        raise ValueError("Aucune parole détectée, réessayez.")
    return text


def speech_data_url(client: BaseAIModel, text: str) -> Optional[str]:
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
    return send_from_directory(PRESCRIPTIONS_DIR, filename, as_attachment=True)


# Mail

@app.route("/mail", methods=["GET", "POST"])
def mail():
    agent = mail_agent()
    messages = []
    summarize = request.args.get("action") == "summarize"
    auto_sort = request.method == "POST" and "auto_sort" in request.form

    if request.method == "POST" and request.form.get("email_id"):
        agent.handler.move_email(request.form["email_id"], request.form["target_folder"])
        messages = ["Mail déplacé."]
        summarize = True

    if (auto_sort or summarize) and over_ai_limit():
        return render_template("mail.html", mode=None, mails=[], folders=[], messages=[LIMIT_MESSAGE])

    if auto_sort:
        destinations = agent.classify_mailbox()
        messages = [f"Mail déplacé dans : {folder}" for folder in destinations] or ["Aucun mail à trier."]

    mails = []
    if summarize:
        mails = [
            {"id": email.id, "sender": email.sender, "date": email.date, "subject": email.subject,
             "summary": agent.summarize_email(email) or "Ce message ne peut pas être résumé."}
            for email in agent.handler.get_unread_emails()
        ]

    return render_template("mail.html", mode="summarize" if summarize else None, mails=mails,
                           folders=agent.handler.get_folders(), messages=messages)


# Planner

def find_appointment(appt_id: int) -> Appointment:
    appointments = planner().controller.all_appointments()
    if not 0 <= appt_id < len(appointments):
        abort(404)
    return appointments[appt_id]


@app.route("/planner/")
def planner_index():
    return render_template("planner.html", current_month=date.today().month)


@app.route("/planner/appointments")
def show_appointments():
    month = request.args.get("month", type=int, default=date.today().month)
    appointments_by_day = {}
    for index, appointment in enumerate(planner().controller.all_appointments()):
        if appointment.date.month == month:
            appointments_by_day.setdefault(appointment.date.day, []).append(
                {"id": index, **appointment.model_dump(mode="json")}
            )
    return render_template("appointments.html", appointments_by_day=appointments_by_day, month=month)


@app.route("/planner/available")
def show_available():
    month = request.args.get("month", type=int, default=date.today().month)
    slots = planner().get_available_timeslots(date(PLANNING_YEAR, month, 1))
    return render_template("available.html", slots=slots, month=month)


@app.route("/planner/reschedule/<int:appt_id>")
def reschedule(appt_id):
    return render_template("reschedule.html", appt_id=appt_id, appointment=find_appointment(appt_id))


@app.post("/api/reschedule/<int:appt_id>/start")
def reschedule_start(appt_id):
    if over_ai_limit():
        return api_error(LIMIT_MESSAGE, 429)
    agent = planner()
    conversation, reply = agent.start_rescheduling(find_appointment(appt_id))
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
        payload["summary"] = (f"Rendez-vous reprogrammé le {appointment.date:%d/%m/%Y} "
                              f"à {appointment.start_time:%H:%M}.")
        payload["next"] = url_for("show_appointments", month=appointment.date.month)
    return jsonify(payload)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
