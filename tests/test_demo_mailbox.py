import pytest

from secretary_ai.agents.demo_mailbox import SAMPLE_EMAILS, DemoMailHandler


def test_inbox_starts_with_the_sample_emails():
    assert len(DemoMailHandler().get_unread_emails()) == len(SAMPLE_EMAILS)


def test_moved_email_leaves_the_inbox():
    handler = DemoMailHandler()
    handler.get_unread_emails()

    handler.move_email("1", "Rendez-vous")

    assert "1" not in [email.id for email in handler.get_unread_emails()]


def test_moving_to_the_inbox_keeps_the_email():
    handler = DemoMailHandler()
    handler.get_unread_emails()

    handler.move_email("1", "INBOX")

    assert len(handler.get_unread_emails()) == len(SAMPLE_EMAILS)


def test_unknown_folder_is_rejected():
    with pytest.raises(ValueError):
        DemoMailHandler().move_email("1", "Vacances")


def test_inbox_refills_once_everything_is_sorted():
    handler = DemoMailHandler()
    for email in handler.get_unread_emails():
        handler.move_email(email.id, "Administratif")

    assert len(handler.get_unread_emails()) == len(SAMPLE_EMAILS)
