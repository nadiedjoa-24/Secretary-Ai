import imaplib
import logging
import smtplib
from datetime import datetime, timedelta
from email import policy
from email.header import decode_header
from email.message import EmailMessage
from email.mime.text import MIMEText
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from typing import List, Optional

from pydantic import BaseModel

from common.config import require_env

logger = logging.getLogger(__name__)


class ReceivedEmail(BaseModel):
    id: str
    content: str
    subject: str
    sender: str
    date: str


class OutgoingEmail(BaseModel):
    recipient: str
    content: str
    subject: Optional[str] = None


def _decode_subject(message: EmailMessage) -> str:
    parts = decode_header(message["Subject"] or "")
    if not parts:
        return ""
    subject, encoding = parts[0]
    if isinstance(subject, bytes):
        subject = subject.decode(encoding or "utf-8", errors="ignore")
    return subject


def _plain_text_body(message: EmailMessage) -> str:
    if not message.is_multipart():
        payload = message.get_payload(decode=True)
        return payload.decode(message.get_content_charset() or "utf-8", errors="ignore") if payload else ""
    body = ""
    for part in message.walk():
        if part.get_content_type() == "text/plain" and not part.get_content_disposition():
            payload = part.get_payload(decode=True)
            if payload:
                body += payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
    return body


class MailHandler:
    """Reads, moves and sends Gmail messages over IMAP and SMTP."""

    IMAP_SERVER = "imap.gmail.com"
    IMAP_PORT = 993
    SMTP_SERVER = "smtp.gmail.com"

    def __init__(self, address: Optional[str] = None, app_password: Optional[str] = None):
        self.address = address or require_env("GMAIL_ADDRESS")
        self.app_password = app_password or require_env("GMAIL_APP_PASSWORD")
        self.mailbox: Optional[imaplib.IMAP4_SSL] = None
        self._connect()

    def _connect(self) -> None:
        try:
            self.mailbox = imaplib.IMAP4_SSL(host=self.IMAP_SERVER, port=self.IMAP_PORT)
            self.mailbox.login(self.address, self.app_password)
        except imaplib.IMAP4.error as error:
            raise ConnectionError(f"Could not log in to the mailbox: {error}") from error

    def disconnect(self) -> None:
        try:
            self.mailbox.logout()
        except imaplib.IMAP4.error as error:
            logger.warning("Logout failed: %s", error)

    def _fetch_message(self, uid: bytes) -> Optional[EmailMessage]:
        # BODY.PEEK does not mark the email as read, unlike RFC822.
        status, fetched = self.mailbox.uid("FETCH", uid, "(BODY.PEEK[])")
        if status != "OK" or not fetched or not isinstance(fetched[0], tuple):
            return None
        return BytesParser(policy=policy.default).parsebytes(fetched[0][1])

    def get_unread_emails(self) -> List[ReceivedEmail]:
        # Reconnect: the IMAP session may have timed out between two web requests.
        self._connect()
        self.mailbox.select("INBOX")
        status, data = self.mailbox.uid("SEARCH", None, "UNSEEN")
        if status != "OK":
            logger.error("Could not search the inbox for unread emails.")
            return []

        emails = []
        for uid in data[0].split():
            message = self._fetch_message(uid)
            if message is None:
                continue
            emails.append(ReceivedEmail(
                id=uid.decode(),
                content=_plain_text_body(message),
                subject=_decode_subject(message),
                sender=message.get("From", ""),
                date=message.get("Date", ""),
            ))
        return emails

    def get_folders(self) -> List[str]:
        try:
            status, folders = self.mailbox.list()
        except imaplib.IMAP4.error as error:
            logger.error("Could not list mailbox folders: %s", error)
            return []
        if status != "OK":
            return []
        return [folder.decode().split(' "/" ')[-1].strip('"') for folder in folders]

    def move_email(self, email_id: str, target_folder: str) -> None:
        """Move an email, identified by its IMAP UID, from the inbox to `target_folder`."""
        folders = self.get_folders()
        if target_folder not in folders:
            raise ValueError(f"Folder {target_folder!r} does not exist. Available folders: {folders}")
        self.mailbox.select("INBOX")
        status, _ = self.mailbox.uid("COPY", email_id, f'"{target_folder}"')
        if status != "OK":
            raise RuntimeError(f"Could not copy email {email_id} to {target_folder!r}.")
        self.mailbox.uid("STORE", email_id, "+FLAGS", "(\\Deleted)")
        self.mailbox.expunge()

    def delete_old_emails(self, max_age_days: int = 30) -> None:
        self.mailbox.select("INBOX")
        status, data = self.mailbox.uid("SEARCH", None, "ALL")
        if status != "OK":
            logger.error("Could not search the inbox.")
            return

        for uid in data[0].split():
            message = self._fetch_message(uid)
            if message is None:
                continue
            try:
                sent_at = parsedate_to_datetime(message.get("Date"))
            except (TypeError, ValueError):
                continue
            if sent_at < datetime.now(sent_at.tzinfo) - timedelta(days=max_age_days):
                self.mailbox.uid("STORE", uid, "+FLAGS", "(\\Deleted)")
        self.mailbox.expunge()

    def send_email(self, email: OutgoingEmail) -> None:
        message = MIMEText(email.content, "plain", "utf-8")
        if email.subject:
            message["Subject"] = email.subject
        message["From"] = self.address
        message["To"] = email.recipient

        try:
            with smtplib.SMTP_SSL(self.SMTP_SERVER, 465, timeout=10) as smtp:
                smtp.login(self.address, self.app_password)
                smtp.send_message(message)
            return
        except (OSError, smtplib.SMTPException) as ssl_error:
            logger.warning("SMTP over SSL failed (%s), retrying with STARTTLS.", ssl_error)

        with smtplib.SMTP(self.SMTP_SERVER, 587, timeout=10) as smtp:
            smtp.starttls()
            smtp.login(self.address, self.app_password)
            smtp.send_message(message)


if __name__ == "__main__":
    handler = MailHandler()
    for received in handler.get_unread_emails():
        print(f"{received.date} | {received.sender} | {received.subject}")
    print("Folders:", handler.get_folders())
    handler.disconnect()
