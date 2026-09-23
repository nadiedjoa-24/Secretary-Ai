import os
import sys

# Permet d’importer votre package 'main' situé au-dessus de ce dossier webapp_planner
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from flask import Flask, render_template, request, redirect, url_for, flash
import json
from datetime import datetime, date
from main.agents.planner_agent.planner_agent import Planner_agent
from main.agents.planner_agent.planner_controller.planner_controller import Appointment

app = Flask(__name__)
app.secret_key = 'dev'  # nécessaire pour les flash messages

# Charge tous les rendez-vous depuis le JSON
with open("./planning_json/2025.json", encoding="utf-8") as f:
    raw = json.load(f)

# Aplatir la structure mois → jour → liste
appointments = []
if isinstance(raw, dict) and all(isinstance(days, dict) for days in raw.values()):
    for month_str, days in sorted(raw.items(), key=lambda x: int(x[0])):
        for day_str, day_list in sorted(days.items(), key=lambda x: int(x[0])):
            for appt in day_list:
                appt_copy = appt.copy()
                # Force un champ date ISO si absent
                appt_copy['date'] = appt_copy.get(
                    'date',
                    f"2025-{int(month_str):02d}-{int(day_str):02d}"
                )
                appointments.append(appt_copy)
elif isinstance(raw, list):
    appointments = raw
else:
    raise ValueError("Format inattendu pour 2025.json : attendu dict de dicts ou liste.")

# Instancie votre agent de planification
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("Il faut définir la variable d'environnement OPENAI_API_KEY pour utiliser le backend API")
planner = Planner_agent(backend="API", API_KEY=api_key)

@app.route("/")
def index():
    current_month = datetime.now().month
    return render_template("index.html", current_month=current_month)

@app.route("/appointments")
def show_appointments():
    month = request.args.get("month", type=int, default=datetime.now().month)
    # Grouper les rdv par jour, avec un ID (= index dans la liste)
    appointments_by_day = {}
    for idx, appt in enumerate(appointments):
        appt_date = datetime.strptime(appt["date"], "%Y-%m-%d")
        if appt_date.month == month:
            day = appt_date.day
            appt_copy = appt.copy()
            appt_copy["id"] = idx
            appointments_by_day.setdefault(day, []).append(appt_copy)

    return render_template(
        "appointments.html",
        appointments_by_day=appointments_by_day,
        month=month
    )

@app.route("/available")
def show_available():
    month = request.args.get("month", type=int, default=datetime.now().month)
    from_date = date(2025, month, 1)
    slots = planner.get_available_timeslots(from_date)
    return render_template(
        "available.html",
        slots=slots,
        month=month
    )

@app.route("/reschedule/<int:appt_id>")
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

    print(appointment)

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
                        'date',
                        f"2025-{int(month_str):02d}-{int(day_str):02d}"
                    )
                    appointments.append(appt_copy)
    elif isinstance(raw, list):
        appointments = raw
    else:
        raise ValueError("Format inattendu pour 2025.json : attendu dict de dicts ou liste.")

    flash(f"✅ Rendez-vous reprogrammé : {appt_data['date']} à {appt_data['start_time']}")
    return redirect(url_for("show_appointments", month=appointment.date.month))

if __name__ == "__main__":
    app.run(debug=True)