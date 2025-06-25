from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_from_directory
import os
import sys
import threading

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ai_agents.ordo_agent import OrdoAgent
from main.agents.email_agent.mail_agent.mail_agent import Mail_Agent

app = Flask(__name__)
app.secret_key = "supersecretkey"
stop_flag = threading.Event()
mail_agent = Mail_Agent()

@app.route("/")
def home():
    return render_template("home.html")

# --- Ordonnance ---
@app.route("/ordonnance", methods=["GET", "POST"])
def ordonnance():
    if request.method == "POST":
        agent = OrdoAgent()
        flash("Veuillez dicter l'ordonnance après le bip...", "info")
        transcript = agent.reconnaitre_voix()
        infos = agent.extraire_infos_ordonnance(transcript)
        if infos:
            chemin_pdf = agent.generer_ordonnance(infos)
            if chemin_pdf:
                flash("Ordonnance générée avec succès !", "success")
                flash(f"Fichier généré : {os.path.basename(chemin_pdf)}", "file")
            else:
                flash("Erreur lors de la génération du fichier.", "danger")
        else:
            flash("Impossible d'extraire les informations de l'ordonnance.", "danger")
        return redirect(url_for("ordonnance"))
    return render_template("ordonnance.html")

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
@app.route('/mails', methods=['GET', 'POST'])
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
    return render_template("auto_sort.html", mails=mails, folders=folders, mode=mode, message=message, messages=messages)

if __name__ == "__main__":
    app.run(debug=True)