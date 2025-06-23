from fastapi import FastAPI
from main.agents.email_agent.mail_agent.mail_agent import Mail_Agent
app = FastAPI()
agent = Mail_Agent()

@app.get("/process")
def process():
    agent.process_unread_mails()
    return {"status": "Traitement terminé"}

@app.get("/summarize")
def summarize_mailbox():
    summaries = agent.summarize_mailbox()
    print("Résumés générés :", summaries)  # Ajoute ce print
    return {"summaries": summaries}