from flask import Flask, render_template, request
import os
import sys

# Ajoute le dossier racine du projet au sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from main.agents.email_agent.mail_agent.mail_agent import Mail_Agent

app = Flask(__name__)

# Instancie l'agent (la clé API doit être dans l'environnement ou passée ici)
mail_agent = Mail_Agent()  # ou Mail_Agent(API_KEY="sk-...")

@app.route('/')
def home():
    summaries = mail_agent.summarize_mailbox()
    return render_template('summaries.html', summaries=summaries)

@app.route('/summarize', methods=['GET'])
def summarize():
    summaries = mail_agent.summarize_mailbox()
    return render_template('summaries.html', summaries=summaries)

if __name__ == '__main__':
    app.run(debug=True)