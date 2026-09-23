import logging
from typing import List, Optional

from common.ai.api_client import APIClient
from common.ai.model.base_model import BaseAIModel, Message
from main.agents.email_agent.mail_handler.mail_handler import MailHandler, OutgoingEmail, ReceivedEmail

logger = logging.getLogger(__name__)


class MailAgent:
    """Summarizes, sorts and answers the emails of the medical office inbox."""

    def __init__(self, handler: Optional[MailHandler] = None, client: Optional[BaseAIModel] = None):
        self.handler = handler or MailHandler()
        self.client = client or APIClient()

    def _ask(self, prompt: str) -> str:
        return self.client.basic([Message(role="user", content=prompt)]).content.strip()

    def summarize_email(self, email: ReceivedEmail) -> str:
        return self._ask(
            "Summarize the following email in two or three sentences, in French, "
            f"keeping only the key information.\n\nEmail:\n{email.content}"
        )

    def summarize_mailbox(self) -> List[str]:
        return [self.summarize_email(email) for email in self.handler.get_unread_emails()]

    def classify_email(self, email: ReceivedEmail, folders: List[str]) -> str:
        answer = self._ask(
            f"Pick the most suitable folder for this email among: {folders}. "
            f"Answer with the exact folder name only.\n\nEmail:\n{email.content}"
        )
        return answer.strip("\"'` ")

    def classify_mailbox(self) -> List[str]:
        """Move every unread email to the folder chosen by the model. Returns the destination folders."""
        folders = self.handler.get_folders()
        destinations = []
        for email in self.handler.get_unread_emails():
            folder = self.classify_email(email, folders)
            if folder not in folders:
                logger.warning("Model suggested unknown folder %r for email %s, leaving it in the inbox.", folder, email.id)
                continue
            self.handler.move_email(email.id, folder)
            destinations.append(folder)
        return destinations

    def respond_to_email(self, email: ReceivedEmail) -> str:
        reply = self._ask(
            "Write a short, polite reply in French to the following email, on behalf of the medical office.\n\n"
            f"Email:\n{email.content}"
        )
        self.handler.send_email(OutgoingEmail(recipient=email.sender, subject=f"Re: {email.subject}", content=reply))
        return reply

    def send_email(self, recipient: str, subject: str, content: str) -> None:
        self.handler.send_email(OutgoingEmail(recipient=recipient, subject=subject, content=content))


if __name__ == "__main__":
    agent = MailAgent()
    for summary in agent.summarize_mailbox():
        print(f"- {summary}")
