import logging
import os
import secrets
import threading
from datetime import date
from functools import cache

from flask import Flask, abort, flash, jsonify, redirect, render_template, request, send_from_directory, url_for

from common.config import PRESCRIPTIONS_DIR
from main.agents.email_agent.mail_agent.mail_agent import MailAgent
from main.agents.planner_agent.planner_agent import PlannerAgent
from main.agents.prescription_agent.prescription_agent import PrescriptionAgent

PLANNING_YEAR = 2025
MONTHS = ["janvier", "février", "mars", "avril", "mai", "juin",
          "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
WEEKDAYS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY") or secrets.token_hex(32)

stop_flag = threading.Event()


@app.template_filter("month_name")
def month_name(month: int) -> str:
    return MONTHS[month - 1]


@app.template_global()
def day_label(month: int, day: int) -> str:
    return f"{WEEKDAYS[date(PLANNING_YEAR, month, day).weekday()]} {day}"


@app.context_processor
def planning_year():
    return {"year": PLANNING_YEAR}


# Agents are created on first use so that each page works even if another agent is not configured.
@cache
def mail_agent() -> MailAgent:
    return MailAgent()


@cache
def planner() -> PlannerAgent:
    return PlannerAgent(year=PLANNING_YEAR)


@cache
def prescription_agent() -> PrescriptionAgent:
    return PrescriptionAgent()


@app.route("/")
def home():
    return render_template("home.html")


@app.route("/prescription", methods=["GET", "POST"])
def prescription():
    if request.method == "GET" or request.form.get("retry") == "oui":
        return render_template("prescription.html")
    if request.form.get("retry") == "non":
        flash("Dictée arrêtée.", "info")
        return redirect(url_for("prescription"))

    agent = prescription_agent()
    result = agent.extract_prescription(agent.record_dictation(stop_flag))
    if not result or not result.is_complete():
        flash("Informations incomplètes : il manque le patient, un médicament, sa posologie ou sa durée.", "danger")
        return render_template("prescription.html", infos=result, retry=True)

    logging.info("Waiting for spoken confirmation of:\n%s", result.summary())
    if agent.ask_confirmation() is not True:
        flash("Correction demandée : veuillez recommencer la dictée.", "info")
        return render_template("prescription.html", infos=result, retry=True)

    pdf_path = agent.generate_pdf(result)
    flash(pdf_path.name, "file")
    return render_template("prescription.html", infos=result, retry="after_success")


@app.route("/stop", methods=["POST"])
def stop_recording():
    stop_flag.set()
    return jsonify({"status": "stopped"})


@app.route("/prescriptions/<path:filename>")
def download_prescription(filename):
    return send_from_directory(PRESCRIPTIONS_DIR, filename, as_attachment=True)


@app.route("/mail", methods=["GET", "POST"])
def mail():
    agent = mail_agent()
    messages = []
    summarize = request.args.get("action") == "summarize"

    if request.method == "POST" and "auto_sort" in request.form:
        destinations = agent.classify_mailbox()
        messages = [f"Mail déplacé dans : {folder}" for folder in destinations] or ["Aucun mail à trier."]
    elif request.method == "POST" and request.form.get("email_id"):
        agent.handler.move_email(request.form["email_id"], request.form["target_folder"])
        messages = ["Mail déplacé."]
        summarize = True

    mails = []
    if summarize:
        mails = [
            {"id": email.id, "sender": email.sender, "date": email.date,
             "summary": agent.summarize_email(email) or "Ce message ne peut pas être résumé."}
            for email in agent.handler.get_unread_emails()
        ]

    return render_template("mail.html", mode="summarize" if summarize else None, mails=mails,
                           folders=agent.handler.get_folders(), messages=messages)


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
    appointments = planner().controller.all_appointments()
    if not 0 <= appt_id < len(appointments):
        abort(404)
    appointment = planner().reschedule_appointment(appointments[appt_id])
    flash(f"Rendez-vous reprogrammé le {appointment.date:%d/%m/%Y} à {appointment.start_time:%H:%M}.")
    return redirect(url_for("show_appointments", month=appointment.date.month))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")
