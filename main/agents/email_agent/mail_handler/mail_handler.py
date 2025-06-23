import os
import imaplib
from email import policy
from email.parser import BytesParser
from email.header import decode_header
import smtplib
from datetime import datetime, timedelta
from email.utils import parsedate_to_datetime
from email.mime.text import MIMEText
from pydantic import BaseModel
from typing import Optional, List, Literal

class eMail(BaseModel):
    """
    Class representing an email.
    """
    id: str
    content: str
    subject: str
    sender: str
    date: str

    def __str__(self):
        return f"Email ID: {self.id},\n Subject: {self.subject},\n Sender: {self.sender},\n Date: {self.date}"
    
class EMail(BaseModel):
    recipient: str
    content: str
    subject: Optional[str] = None

    def __str__(self):
        return f"Recipient: {self.recipient},\n Subject: {self.subject},\n Content: {self.content}." 

    

class MailBox(BaseModel):
    """
    Class representing available folders for mail processing.
    """
    folder: Literal["RDV", "[Gmail]/IMPORTANT", "SPAM", "JSP"]


class MAIL_HANDLER:

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self, 
                EMAIL: str = "arthisow@gmail.com",
                PASSWORD: str = "wbvtovmwbfkkwdde" ,
                ):
        self.EMAIL = EMAIL
        self.PASSWORD = PASSWORD
        if not self.EMAIL:
            try:
                self.EMAIL = os.getenv("EMAIL")
            except KeyError as e:
                raise ValueError(f"EMAIL is required for IMAP connection, please provide one at instanciation or in environment :{e}")
        if not self.PASSWORD:
            try:
                self.PASSWORD = os.getenv("PASSWORD")
            except KeyError as e:
                raise ValueError(f"PASSWORD is required for IMAP connection, please provide one at instanciation or in environment :{e}")
        
        self.mailbox = None

        try:
            self._connect()
            print("Connexion established with server.")
        except ValueError as e:
            print(f"Connexion error : {e}")
            raise

        self.mails: List[eMail] = []

    def _connect(self):
        """
        Connect client to the IMAP server associated with the EMAIL and PASSWORD.
        """
        try:
            self.mailbox = imaplib.IMAP4_SSL(host=self.IMAP_SERVER, port=self.IMAP_PORT)
            self.mailbox.login(self.EMAIL, self.PASSWORD)
        except imaplib.IMAP4.error as e:
            raise ValueError(f"Erreur de connexion à la boîte mail : {e}")

    def _disconnect(self):
        try :
            self.mailbox.logout()
            print("Déconnexion réussie de la boîte mail.")
        except imaplib.IMAP4.error as e:
            print(f"Erreur de déconnexion de la boîte mail : {e}")


    def get_unread_emails(self) -> List[eMail]:
        """
        Open inbox folder and retrieve all unread emails as eMail objects.
        """
        unread_emails = []
        self._connect()
        self.mailbox.select("INBOX")
        status, messages = self.mailbox.search(None, 'UNSEEN')
        print(f"test: {messages[0]}")
        if status != "OK":
            print("Erreur lors de la récupération des emails.")
            return

        email_ids = messages[0].split()
        for e_id in email_ids:
            status, data = self.mailbox.fetch(e_id, "(RFC822)")
            if status == "OK":
                raw_email = data[0][1]
                msg = BytesParser(policy=policy.default).parsebytes(raw_email)

                dh = decode_header(msg["Subject"] or "")
                subject, encoding = dh[0] if dh else ("", None)
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")

                sender = msg.get("From", "")
                date = msg.get("Date", "")

                content = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" and not part.get_content_disposition():
                            payload = part.get_payload(decode=True)
                            charset = part.get_content_charset() or "utf-8"
                            content += payload.decode(charset, errors="ignore")
                else:
                    payload = msg.get_payload(decode=True)
                    charset = msg.get_content_charset() or "utf-8"
                    content = payload.decode(charset, errors="ignore") if payload else ""

                email_obj = eMail(
                    id=e_id.decode(),
                    content=content,
                    subject=subject,
                    sender=sender,
                    date=date
                )
                unread_emails.append(email_obj)

        return unread_emails


    def move_email(self, email_id, target_folder):
        """
        Move an email according to its ID to the target folder.
        """
        if target_folder in self.get_folders():
            self.mailbox.copy(email_id, target_folder)
            self.mailbox.store(email_id, '+FLAGS', '\\Deleted')
            self.mailbox.expunge()
        else:
            print(f"Folder {target_folder} does not exist. Please choose one of the following: {self.get_folders()}")


    def get_folders(self):
        """
        Return all available folders in the mailbox.
        """
        try:
            status, folders = self.mailbox.list()
            if status != "OK":
                print("Error retrieving mailbox's folders.")
                return []
            return [folder.decode().split(' "/" ')[-1] for folder in folders]
        except imaplib.IMAP4.error as e:
            print(f"Error retrieving mailbox's folders: {e}")
            return []
        

    def delete_old_emails(self):
        """
        Delete all emails older than 30 days.
        """
        self.mailbox.select("INBOX")
        status, messages = self.mailbox.search(None, 'ALL')
        if status != "OK":
            print("Error retrieving old emails")
            return

        email_ids = messages[0].split()
        for e_id in email_ids:
            status, data = self.mailbox.fetch(e_id, "(RFC822)")
            if status == "OK":
                raw_email = data[0][1]
                msg = BytesParser(policy=policy.default).parsebytes(raw_email)
                date_header = msg.get("Date")
                try:
                    email_date = parsedate_to_datetime(date_header)
                except Exception:
                    continue

                cutoff = datetime.now(email_date.tzinfo) - timedelta(days=30)
                if email_date < cutoff:
                    self.mailbox.store(e_id, '+FLAGS', '\\Deleted')
                    print(f"Deleted email {e_id.decode()} dated {email_date.isoformat()}")

        self.mailbox.expunge()
    


    def send_email(self, email_to_send: EMail):
        """
        Send an email to the recipient via SMTP.
        """
        print(email_to_send)
        msg = MIMEText(email_to_send.content, "plain", "utf-8")
        if email_to_send.subject:
            msg["Subject"] = email_to_send.subject
        msg["From"] = self.EMAIL
        msg["To"] = email_to_send.recipient

        try:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as smtp:
                smtp.login(self.EMAIL, self.PASSWORD)
                smtp.send_message(msg)
            print("Email sent via SSL port 465.")
            return
        except Exception as e1:
            print(f"Port 465 failed ({e1}), trying STARTTLS on port 587...")

        # Second attempt: STARTTLS on port 587
        try:
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.ehlo()
                smtp.login(self.EMAIL, self.PASSWORD)
                smtp.send_message(msg)
            print("Email sent via STARTTLS port 587.")
        except Exception as e2:
            raise ValueError(f"Failed to send email on port 465 ({e1}) and port 587 ({e2})")



    


     
 # Test example

if __name__ == "__main__":
 
    EMAIL = "arthisow@gmail.com"
    PASSWORD = "wbvtovmwbfkkwdde" 
    mail_handler = MAIL_HANDLER(EMAIL, PASSWORD)

    mail_handler.get_unread_emails()
    
    for e in mail_handler.mails:
        print(e)

    folders = mail_handler.get_folders()
    print(f"Available folders: {folders}")
    try:
        mail_handler.move_email(mail_handler.mails[0].id, "test")
    except IndexError:
        print("[ERROR] : No emails to move.")
    
    mail_handler._disconnect()

    print("== Test envoi email ==")
    email = EMail(
        recipient="yanic.rothlingshofer@gmail.com",
        content="Ceci est un test d'envoi d'email depuis le MAIL_HANDLER.",
        subject="Test Email")
    try:
        mail_handler.send_email(email)
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")