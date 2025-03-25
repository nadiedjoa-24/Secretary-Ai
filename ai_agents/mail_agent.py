import openai
import imaplib
import os
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import Literal

class MailBox(BaseModel):
    MailBox: Literal["RDV", "IMPORTANT", "SPAM", ]

load_dotenv()

class Mail_Agent:

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993 
    EMAIL = os.getenv("EMAIL")
    PASSWORD = os.getenv("MDP") # MDP application du compte google et pas le mdp du compte (double authentification nécessaire)
    API_KEY = os.getenv("OPENAI_API_KEY2")

    mail = imaplib.IMAP4_SSL(host=IMAP_SERVER, port=IMAP_PORT)
    mail.login(EMAIL, PASSWORD)


    def __init__(self):
        self.client = openai.OpenAI(api_key = self.API_KEY)
        self.mails = []
        self.mail = imaplib.IMAP4_SSL(host=self.IMAP_SERVER, port=self.IMAP_PORT)
        self.mail.login(self.EMAIL, self.PASSWORD)
    

    def get_unread_emails(self):
        """Ouvre la boîte mail et récupère tous les emails non lus."""
        self.mail.select("INBOX") 
        status, messages = self.mail.search(None, 'UNSEEN') 

        if status != "OK":
            print("Erreur lors de la récupération des emails.")
            return

        email_ids = messages[0].split()
        for e_id in email_ids:
            status, data = self.mail.fetch(e_id, "(RFC822)") 
            if status == "OK":
                self.mails.append((e_id, data[0][1])) 


    def process_emails(self, content):
        """Traite le contenu d'un mail pour évaluer sa catégorie."""

        prompt = f"""
        Tu es un assistant intelligent qui classe les emails dans les catégories suivantes :
        - RDV : si l'email concerne un rendez-vous
        - INBOX : si l'email n'est pas catégorisable et doit rester dans la boîte principale
        - SPAM : si l'email est une publicité ou semble frauduleux
        - ARCHIVE : si l'email est ancien ou informatif
        Voici le contenu d'un email :

        {content}
        """

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format = MailBox
        )

        category = response.choices[0].message.parsed
        return MailBox(MailBox=category)


    def move_email(self, email_id, mailbox):
        """Déplace un email vers une boîte spécifique."""
        self.mail.store(email_id, '+FLAGS', '\\Seen')  
        self.mail.copy(email_id, mailbox) 
        self.mail.store(email_id, '+FLAGS', '\\Deleted')
        self.mail.expunge() 


    def process_unread_mails(self):
        """Traite tous les emails non lus et les classe automatiquement."""
        self.get_unread_emails()
        for email_id, content in self.mails:
            category = self.process_emails(content).MailBox
            self.move_email(email_id, category)
            print(f"Email {email_id} déplacé vers {category}")

        self.mails.clear() 




if __name__ == "__main__":
    agent = Mail_Agent()
    agent.process_unread_mails()