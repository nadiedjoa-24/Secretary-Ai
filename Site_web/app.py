from flask import Flask, render_template, request
import os
import sys

# Ajoute le dossier racine du projet au sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main.agents.email_agent.mail_agent.mail_agent import Mail_Agent

app = Flask(__name__)

mail_agent = Mail_Agent()  # ou Mail_Agent(API_KEY="sk-...")

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/summarize', methods=['GET', 'POST'])
def summarize():
    unseen_emails = mail_agent.M.get_unread_emails()
    folders = mail_agent.M.get_folders()
    mails = []
    if request.method == 'POST':
        email_id = request.form['email_id']
        target_folder = request.form['target_folder']
        mail_agent.M.move_email(email_id, target_folder)
        message = "Mail déplacé avec succès !"
    else:
        message = None

    for email in unseen_emails:
        date = getattr(email, "date", "Date inconnue")
        summary = mail_agent.summarize_email(email)
        if not summary or summary.strip() == "":
            summary = "Ce message ne peut pas être résumé."
        mails.append({
            "id": email.id,
            "date": date,
            "summary": summary
        })
    return render_template('summaries.html', mails=mails, folders=folders, message=message)

@app.route('/rearrange', methods=['GET', 'POST'])
def rearrange():
    unseen_emails = mail_agent.M.get_unread_emails()
    folders = mail_agent.M.get_folders()
    if request.method == 'POST':
        email_id = request.form['email_id']
        target_folder = request.form['target_folder']
        mail_agent.M.move_email(email_id, target_folder)
        message = "Mail déplacé avec succès !"
        return render_template('rearrange.html', emails=unseen_emails, folders=folders, message=message)
    return render_template('rearrange.html', emails=unseen_emails, folders=folders)

@app.route('/summarize/auto_sort', methods=['POST'])
def auto_sort():
    classifications = mail_agent.classify_mailbox()
    # Création d'une liste de messages pour chaque mail déplacé
    if classifications:
        messages = [f"Mail déplacé avec succès dans : {folder}" for folder in classifications]
    else:
        messages = ["Aucun mail à trier."]
    # Recharge la page des résumés
    unseen_emails = mail_agent.M.get_unread_emails()
    folders = mail_agent.M.get_folders()
    mails = []
    for email in unseen_emails:
        date = getattr(email, "date", "Date inconnue")
        summary = mail_agent.summarize_email(email)
        if not summary or summary.strip() == "":
            summary = "Ce message ne peut pas être résumé."
        mails.append({
            "id": email.id,
            "date": date,
            "summary": summary
        })
    return render_template('summaries.html', mails=mails, folders=folders, messages=messages)

if __name__ == '__main__':
    app.run(debug=True)