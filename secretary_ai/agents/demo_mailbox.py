"""In-memory mailbox used by the public demo instead of a real Gmail account."""
import logging
import threading
from typing import List

from secretary_ai.agents.mail_handler import OutgoingEmail, ReceivedEmail

logger = logging.getLogger(__name__)

FOLDERS = ["INBOX", "Rendez-vous", "Ordonnances", "Administratif", "Spam"]

SAMPLE_EMAILS = [
    ReceivedEmail(
        id="1",
        sender="Claire Dubois <claire.dubois@example.com>",
        date="Mon, 6 Jan 2025 08:12:00 +0100",
        subject="Report de mon rendez-vous",
        content=(
            "Bonjour,\n\nJ'ai rendez-vous avec le docteur jeudi 9 janvier à 10h30 mais j'ai un empêchement "
            "professionnel. Serait-il possible de le décaler au début de la semaine suivante, de préférence le "
            "matin ?\n\nMerci d'avance,\nClaire Dubois"
        ),
    ),
    ReceivedEmail(
        id="2",
        sender="Marc Durand <marc.durand@example.com>",
        date="Mon, 6 Jan 2025 09:47:00 +0100",
        subject="Renouvellement d'ordonnance",
        content=(
            "Bonjour,\n\nMon traitement pour la tension arrive à sa fin la semaine prochaine. Le docteur peut-il "
            "renouveler mon ordonnance d'amlodipine 5 mg sans consultation, comme la dernière fois ? Je peux passer "
            "la récupérer au cabinet.\n\nCordialement,\nMarc Durand"
        ),
    ),
    ReceivedEmail(
        id="3",
        sender="Laboratoire BioAnalyses <resultats@bioanalyses.example.com>",
        date="Mon, 6 Jan 2025 11:03:00 +0100",
        subject="Résultats disponibles : Mme Hélène Petit",
        content=(
            "Madame, Monsieur,\n\nLes résultats du bilan sanguin de Mme Hélène Petit, prélevé le 3 janvier, sont "
            "disponibles sur votre espace professionnel. Une valeur de CRP élevée a été signalée.\n\n"
            "Laboratoire BioAnalyses"
        ),
    ),
    ReceivedEmail(
        id="4",
        sender="Fournitures Médicales Pro <contact@fmp.example.com>",
        date="Tue, 7 Jan 2025 07:30:00 +0100",
        subject="Facture n°2025-0142",
        content=(
            "Bonjour,\n\nVeuillez trouver ci-joint la facture n°2025-0142 de 318,40 euros pour la commande de "
            "gants et de compresses livrée le 2 janvier. Règlement attendu sous 30 jours.\n\nLe service comptabilité"
        ),
    ),
    ReceivedEmail(
        id="5",
        sender="Offres Santé <promo@offres-sante.example.com>",
        date="Tue, 7 Jan 2025 10:15:00 +0100",
        subject="-70% sur votre tensiomètre connecté, offre limitée !",
        content=(
            "Profitez de notre offre exceptionnelle : le tensiomètre connecté à -70% aujourd'hui seulement. "
            "Cliquez vite sur le lien pour en profiter avant la fin de l'offre !"
        ),
    ),
]


class DemoMailHandler:
    """Drop-in replacement for MailHandler that keeps sample emails in memory."""

    def __init__(self):
        self._lock = threading.Lock()
        self.inbox: List[ReceivedEmail] = []
        self.sent: List[OutgoingEmail] = []

    def get_unread_emails(self) -> List[ReceivedEmail]:
        with self._lock:
            # Refill once every sample has been sorted, so each visitor has something to try.
            if not self.inbox:
                self.inbox = [email.model_copy() for email in SAMPLE_EMAILS]
            return list(self.inbox)

    def get_folders(self) -> List[str]:
        return list(FOLDERS)

    def move_email(self, email_id: str, target_folder: str) -> None:
        if target_folder not in FOLDERS:
            raise ValueError(f"Folder {target_folder!r} does not exist. Available folders: {FOLDERS}")
        if target_folder == "INBOX":
            return
        with self._lock:
            self.inbox = [email for email in self.inbox if email.id != email_id]

    def send_email(self, email: OutgoingEmail) -> None:
        logger.info("Demo mode, email to %s not sent.", email.recipient)
        self.sent.append(email)
