from datetime import date
from email.utils import parsedate_to_datetime

import pytest

from secretary_ai.agents.demo_mailbox import DemoMailHandler, sample_emails

SAMPLE_COUNT = len(sample_emails(date.today()))


def test_inbox_starts_with_the_sample_emails():
    assert len(DemoMailHandler().get_unread_emails()) == SAMPLE_COUNT


def test_sample_emails_follow_the_date_of_the_visit():
    emails = sample_emails(date(2026, 9, 23))

    received = sorted(parsedate_to_datetime(email.date).date() for email in emails)
    assert received[0] == date(2026, 9, 21) and received[-1] == date(2026, 9, 22)
    assert "jeudi 24 septembre" in emails[0].content
    assert emails[3].subject == "Facture n°2026-0142"


def test_moved_email_leaves_the_inbox():
    handler = DemoMailHandler()
    handler.get_unread_emails()

    handler.move_email("1", "Rendez-vous")

    assert "1" not in [email.id for email in handler.get_unread_emails()]


def test_moving_to_the_inbox_keeps_the_email():
    handler = DemoMailHandler()
    handler.get_unread_emails()

    handler.move_email("1", "INBOX")

    assert len(handler.get_unread_emails()) == SAMPLE_COUNT


def test_unknown_folder_is_rejected():
    with pytest.raises(ValueError):
        DemoMailHandler().move_email("1", "Vacances")


def test_inbox_refills_once_everything_is_sorted():
    handler = DemoMailHandler()
    for email in handler.get_unread_emails():
        handler.move_email(email.id, "Administratif")

    assert len(handler.get_unread_emails()) == SAMPLE_COUNT
