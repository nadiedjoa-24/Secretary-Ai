from flask import Flask, render_template, request
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from main.agents.email_agent.mail_agent.mail_agent import Mail_Agent

app = Flask(__name__)

mail_agent = Mail_Agent()

@app.route('/', methods=['GET', 'POST'])
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
        # On recharge les mails restants à résumer
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

    return render_template('auto_sort.html', mails=mails, folders=folders, message=message, messages=messages, mode=mode)

if __name__ == '__main__':
    app.run(debug=True)