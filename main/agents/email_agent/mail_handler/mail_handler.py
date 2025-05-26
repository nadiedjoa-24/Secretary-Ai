import os
import imaplib
from email import policy
from email.parser import BytesParser
from email.header import decode_header
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
    

class MailBox(BaseModel):
    """
    Class representing available folders for mail processing.
    """
    folder: Literal["RDV", "[Gmail]/IMPORTANT", "SPAM", "JSP"]


class MAIL_HANDLER:

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993

    def __init__(self, 
                EMAIL: str = None,
                PASSWORD: str = None,
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
        
        self.mail = None

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
            self.mail = imaplib.IMAP4_SSL(host=self.IMAP_SERVER, port=self.IMAP_PORT)
            self.mail.login(self.EMAIL, self.PASSWORD)
        except imaplib.IMAP4.error as e:
            raise ValueError(f"Erreur de connexion à la boîte mail : {e}")

    def _disconnect(self):
        try :
            self.mail.logout()
            print("Déconnexion réussie de la boîte mail.")
        except imaplib.IMAP4.error as e:
            print(f"Erreur de déconnexion de la boîte mail : {e}")


    def get_unread_emails(self):
        """
        Open inbox folder and retrieve all unread emails as eMail objects.
        """
        self._connect()
        self.mail.select("INBOX")
        status, messages = self.mail.search(None, 'UNSEEN')

        if status != "OK":
            print("Erreur lors de la récupération des emails.")
            return

        email_ids = messages[0].split()
        for e_id in email_ids:
            status, data = self.mail.fetch(e_id, "(RFC822)")
            if status == "OK":
                raw_email = data[0][1]
                msg = BytesParser(policy=policy.default).parsebytes(raw_email)

                # Decode subject header
                dh = decode_header(msg["Subject"] or "")
                subject, encoding = dh[0] if dh else ("", None)
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")

                # Extract sender and date
                sender = msg.get("From", "")
                date = msg.get("Date", "")

                # Extract plain text body
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

                # Create and store eMail instance
                email_obj = eMail(
                    id=e_id.decode(),
                    content=content,
                    subject=subject,
                    sender=sender,
                    date=date
                )
                self.mails.append(email_obj)


    def move_email(self, email_id, target_folder):
        """
        Move an email according to its ID to the target folder.
        """
        if target_folder in self.get_folders():
            self.mail.copy(email_id, target_folder)
            self.mail.store(email_id, '+FLAGS', '\\Deleted')
            self.mail.expunge()
        else:
            print(f"Folder {target_folder} does not exist. Please choose one of the following: {self.get_folders()}")


    def get_folders(self):
        """
        Return all available folders in the mailbox.
        """
        try:
            status, folders = self.mail.list()
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
        self.mail.select("INBOX")
        status, messages = self.mail.search(None, 'ALL')
        if status != "OK":
            print("Error retrieving old emails")
            return

        email_ids = messages[0].split()
        for e_id in email_ids:
            status, data = self.mail.fetch(e_id, "(RFC822)")
            if status == "OK":
                # Récupérer la date de l'email mais jsp comment faire
                pass

        self.mail.expunge()

    


     
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