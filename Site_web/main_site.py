from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory, session
import os
import sys
import threading
import json
from datetime import datetime, date

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_agents.ordo_agent import OrdoAgent, PatientInfo
from main.agents.email_agent.mail_agent.mail_agent import Mail_Agent
from main.agents.planner_agent.planner_agent import Planner_agent
from main.agents.planner_agent.planner_controller.planner_controller import Appointment

# Import de l'app Flask du planner
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'webapp_planner')))

app = Flask(__name__)
app.secret_key = "supersecretkey"
stop_flag = threading.Event()
mail_agent = Mail_Agent()

# Charge tous les rendez-vous depuis le JSON
with open("./planning_json/2025.json", encoding="utf-8") as f:
    raw = json.load(f)
appointments = []
if isinstance(raw, dict) and all(isinstance(days, dict) for days in raw.values()):
    for month_str, days in sorted(raw.items(), key=lambda x: int(x[0])):
        for day_str, day_list in sorted(days.items(), key=lambda x: int(x[0])):
            for appt in day_list:
                appt_copy = appt.copy()
                appt_copy['date'] = appt_copy.get(
                    'date', f"2025-{int(month_str):02d}-{int(day_str):02d}"
                )
                appointments.append(appt_copy)
elif isinstance(raw, list):
    appointments = raw
else:
    raise ValueError("Format inattendu pour 2025.json : attendu dict de dicts ou liste.")

api_key = "***REMOVED-OPENAI-KEY-1***"
if not api_key:
    raise RuntimeError("Il faut définir la variable d'environnement API_KEY pour utiliser le backend API")
planner = Planner_agent(backend="API", API_KEY=api_key)

@app.route("/")
def home():
    return render_template("home.html")

# --- Ordonnance ---
@app.route("/ordonnance", methods=["GET", "POST"])
def ordonnance():
    agent = OrdoAgent()
    if request.method == "POST":
        if "step" not in session:
            flash("Veuillez dicter l'ordonnance après le bip...", "info")
            transcript = agent.reconnaitre_voix()
            infos = agent.extraire_infos_ordonnance(transcript)
            if infos and infos.patient and infos.medicaments:
                medicaments_complets = all(med.nom and med.posologie and med.duree for med in infos.medicaments)
                confirmation_text = get_confirmation_text(infos)
                if medicaments_complets:
                    # Affiche la confirmation sur le site
                    agent.afficher_confirmation(infos)
                    # Demande confirmation orale (micro)
                    confirmation = agent.demander_confirmation_orale()
                    if confirmation is True:
                        chemin_pdf = agent.generer_ordonnance(infos)
                        if chemin_pdf:
                            flash("✅ Ordonnance générée avec succès !", "success")
                            flash(f"{os.path.basename(chemin_pdf)}", "file")
                        else:
                            flash("Erreur lors de la génération du fichier.", "danger")
                        # Propose de recommencer ou d'arrêter après génération
                        session["step"] = "retry"
                        session["infos"] = infos.model_dump()
                        return render_template(
                            "ordonnance.html",
                            infos=infos,
                            retry="after_success",
                            confirmation=False,
                            confirmation_text=confirmation_text
                        )
                    elif confirmation is False:
                        flash("Vous avez demandé une correction. Veuillez recommencer la dictée.", "info")
                        session["step"] = "retry"
                        session["infos"] = infos.model_dump()
                        return render_template(
                            "ordonnance.html",
                            infos=infos,
                            retry=True,
                            confirmation=False,
                            confirmation_text=confirmation_text
                        )
                    else:
                        flash("Réponse non comprise. Veuillez recommencer la dictée.", "danger")
                        session["step"] = "retry"
                        session["infos"] = infos.model_dump()
                        return render_template(
                            "ordonnance.html",
                            infos=infos,
                            retry=True,
                            confirmation=False,
                            confirmation_text=confirmation_text
                        )
                else:
                    flash("❌ Informations de médicaments incomplètes (posologie ou durée manquante).", "danger")
                    flash("Voulez-vous recommencer la dictée ? (Dites 'oui' pour recommencer ou 'non' pour arrêter)", "info")
                    session["step"] = "retry"
                    session["infos"] = infos.model_dump()
                    return render_template(
                        "ordonnance.html",
                        infos=infos,
                        retry=True,
                        confirmation=False,
                        confirmation_text=confirmation_text
                    )
            else:
                flash("❌ Impossible d'extraire les informations de l'ordonnance ou patient manquant.", "danger")
                flash("Voulez-vous recommencer la dictée ? (Dites 'oui' pour recommencer ou 'non' pour arrêter)", "info")
                session["step"] = "retry"
                session["infos"] = infos.model_dump() if infos else None
                return render_template(
                    "ordonnance.html",
                    infos=infos,
                    retry=True,
                    confirmation=False,
                    confirmation_text=None
                )

        # 2. Gestion de l'étape "retry"
        elif session.get("step") == "retry":
            if request.form.get("retry") == "oui":
                session.pop("step", None)
                session.pop("infos", None)
                return redirect(url_for("ordonnance"))
            elif request.form.get("retry") == "non":
                flash("Programme arrêté.", "danger")
                session.pop("step", None)
                session.pop("infos", None)
                return redirect(url_for("ordonnance"))
            else:
                infos = PatientInfo.parse_obj(session["infos"]) if session.get("infos") else None
                confirmation_text = get_confirmation_text(infos) if infos else None
                return render_template(
                    "ordonnance.html",
                    infos=infos,
                    retry=True,
                    confirmation=False,
                    confirmation_text=confirmation_text
                )
    # GET : affichage initial
    session.pop("step", None)
    session.pop("infos", None)
    return render_template("ordonnance.html", infos=None, confirmation=False, retry=False, confirmation_text=None)

@app.route("/stop", methods=["POST"])
def stop_recording():
    stop_flag.set()
    return jsonify({"status": "stopped"})

@app.route('/ordonnances/<filename>')
def download_ordonnance(filename):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    dossier_ordonnances = os.path.join(base_dir, "ordonnances")
    return send_from_directory(dossier_ordonnances, filename)

# --- Gestion des mails ---
@app.route('/auto_sort', methods=['GET', 'POST'])
def auto_sort():
    mode = None
    mails = []
    folders = mail_agent.M.get_folders()
    message = None
    messages = None

    # Résumer les mails
    if request.method == 'GET' and request.args.get('action') == 'summarize':
        mode = "summarize"
        unseen_emails = mail_agent.M.get_unread_emails()
        for email in unseen_emails:
            date = getattr(email, "date", "Date inconnue")
            summary = mail_agent.summarize_email(email)
            sender = getattr(email, "sender", "Expéditeur inconnu")
            if not summary or summary.strip() == "":
                summary = "Ce message ne peut pas être résumé."
            mails.append({
                "id": email.id,
                "date": date,
                "summary": summary,
                "sender": sender
            })

    # Déplacement manuel
    if request.method == 'POST' and 'email_id' in request.form:
        mode = "summarize"
        email_id = request.form.get('email_id')
        target_folder = request.form.get('target_folder')
        if email_id and target_folder:
            mail_agent.M.move_email(email_id, target_folder)
            message = "Mail déplacé avec succès !"
        unseen_emails = mail_agent.M.get_unread_emails()
        for email in unseen_emails:
            date = getattr(email, "date", "Date inconnue")
            summary = mail_agent.summarize_email(email)
            sender = getattr(email, "sender", "Expéditeur inconnu")
            if not summary or summary.strip() == "":
                summary = "Ce message ne peut pas être résumé."
            mails.append({
                "id": email.id,
                "date": date,
                "summary": summary,
                "sender": sender
            })

        # Tri automatique
    if request.method == 'POST' and 'auto_sort' in request.form:
        mode = "auto_sort"
        classifications = mail_agent.classify_mailbox()
        if classifications:
            messages = [f"Mail déplacé avec succès dans : {folder}" for folder in classifications]
        else:
            messages = ["Aucun mail à trier."]


    return render_template("auto_sort.html", mails=mails, folders=folders, mode=mode, message=message, messages=messages)

@app.route("/planner/")
def planner_index():
    current_month = datetime.now().month
    return render_template("index.html", current_month=current_month)

@app.route("/planner/appointments")
def show_appointments():
    month = request.args.get("month", type=int, default=datetime.now().month)
    appointments_by_day = {}
    for idx, appt in enumerate(appointments):
        appt_date = datetime.strptime(appt["date"], "%Y-%m-%d")
        if appt_date.month == month:
            day = appt_date.day
            appt_copy = appt.copy()
            appt_copy["id"] = idx
            appointments_by_day.setdefault(day, []).append(appt_copy)
    return render_template(
        "appointments.html", appointments_by_day=appointments_by_day, month=month
    )

@app.route("/planner/available")
def show_available():
    month = request.args.get("month", type=int, default=datetime.now().month)
    from_date = date(2025, month, 1)
    slots = planner.get_available_timeslots(from_date)
    return render_template(
        "available.html", slots=slots, month=month
    )

@app.route("/planner/reschedule/<int:appt_id>")
def reschedule(appt_id):
    global appointments
    appt_data = appointments[appt_id]
    appt_date = datetime.strptime(appt_data["date"], "%Y-%m-%d").date()
    time_str = appt_data.get("start_time", "")
    if "+" in time_str:
        time_str = time_str.split("+", 1)[0]
    elif time_str.endswith("Z"):
        time_str = time_str[:-1]
    try:
        start_time = datetime.strptime(time_str, "%H:%M:%S").time()
    except ValueError:
        start_time = datetime.strptime(time_str, "%H:%M").time()
    appointment = Appointment(
        name=appt_data["name"],
        surname=appt_data["surname"],
        date=appt_date,
        mail=appt_data.get("mail"),
        phone=appt_data.get("phone"),
        description=appt_data.get("description", ""),
        start_time=start_time
    )
    planner.reschedule_appointment(appointment)
    with open("./planning_json/2025.json", encoding="utf-8") as f:
        raw = json.load(f)
    appointments = []
    if isinstance(raw, dict) and all(isinstance(days, dict) for days in raw.values()):
        for month_str, days in sorted(raw.items(), key=lambda x: int(x[0])):
            for day_str, day_list in sorted(days.items(), key=lambda x: int(x[0])):
                for appt in day_list:
                    appt_copy = appt.copy()
                    appt_copy['date'] = appt_copy.get(
                        'date', f"2025-{int(month_str):02d}-{int(day_str):02d}"
                    )
                    appointments.append(appt_copy)
    elif isinstance(raw, list):
        appointments = raw
    else:
        raise ValueError("Format inattendu pour 2025.json : attendu dict de dicts ou liste.")
    flash(f"✅ Rendez-vous reprogrammé : {appt_data['date']} à {appt_data['start_time']}")
    return redirect(url_for("show_appointments", month=appointment.date.month))

def get_confirmation_text(infos):
    if not infos:
        return ""
    lines = []
    lines.append("\n" + "="*60)
    lines.append("CONFIRMATION DES INFORMATIONS EXTRAITES")
    lines.append("="*60)
    lines.append(f"Patient : {infos.patient}")
    lines.append("\nMédicaments prescrits :")
    for i, med in enumerate(infos.medicaments, 1):
        lines.append(f"  {i}. Nom : {med.nom}")
        lines.append(f"     Posologie : {med.posologie}")
        lines.append(f"     Durée : {med.duree}")
        lines.append("")
    lines.append("="*60)
    lines.append("Veuillez confirmer ces informations en répondant 'oui' ou 'non' à l'oral.")
    lines.append("="*60)
    return "\n".join(lines)

if __name__ == "__main__":
    app.run(debug=True)