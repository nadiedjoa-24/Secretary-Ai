from datetime import date, time

import pytest

from secretary_ai.agents import planner_agent
from secretary_ai.agents.planner_agent import PlannerAgent, RescheduleDecision
from secretary_ai.agents.planner_controller import Appointment, PlannerController
from secretary_ai.ai.base_model import Message


class ScriptedClient:
    """Fake AI client returning prepared answers in order."""

    def __init__(self, decisions=()):
        self.decisions = list(decisions)
        self.replies = 0

    def basic(self, messages):
        self.replies += 1
        return Message(role="assistant", content=f"reply {self.replies}")

    def parse(self, messages, data_model):
        return self.decisions.pop(0) if self.decisions else RescheduleDecision()


def make_appointment(day=date(2025, 3, 20), start=time(10)):
    return Appointment(name="Alice", surname="Martin", date=day, mail="alice@example.com", start_time=start)


@pytest.fixture
def controller(tmp_path):
    return PlannerController(year=2025, path=tmp_path)


@pytest.fixture
def agent(controller):
    # No AI client or microphone is needed to compute free slots.
    return PlannerAgent(client=object(), controller=controller, audio=object())


def test_slots_cover_the_rest_of_the_month_and_the_next_one(agent):
    slots = agent.get_available_timeslots(date(2025, 3, 20))

    assert sorted(slots) == [3, 4]
    assert min(slots[3]) == 20
    assert len(slots[4]) == 22  # weekdays of April 2025


def test_november_rolls_over_to_december(agent):
    slots = agent.get_available_timeslots(date(2025, 11, 28))

    assert sorted(slots) == [11, 12]


def test_slots_stop_at_the_end_of_the_planning_year(agent):
    slots = agent.get_available_timeslots(date(2025, 12, 30))

    assert sorted(slots) == [12]


def test_booked_slot_is_excluded(agent):
    agent.controller.add_appointment(make_appointment(day=date(2025, 3, 21), start=time(8)))

    slots = agent.get_available_timeslots(date(2025, 3, 20))

    assert "08:00" not in slots[3][21]
    assert "08:00" in slots[3][20]


def test_conversation_moves_the_appointment_once_the_patient_confirms(controller):
    appointment = make_appointment()
    controller.add_appointment(appointment)
    client = ScriptedClient([RescheduleDecision(), RescheduleDecision(new_date=date(2025, 3, 25), new_time=time(14), final=True)])
    agent = PlannerAgent(client=client, controller=controller, audio=object())

    conversation, first_reply = agent.start_rescheduling(appointment)
    agent.handle_patient_message(conversation, "Plutôt mardi prochain l'après-midi")
    assert not conversation.done

    agent.handle_patient_message(conversation, "Oui, mardi 25 à 14h c'est parfait")

    assert first_reply == "reply 1"
    assert conversation.done
    assert controller.get_day_appointments(date(2025, 3, 20)) == []
    assert controller.get_day_appointments(date(2025, 3, 25))[0].start_time == time(14)


def test_unavailable_slot_is_refused_and_the_conversation_goes_on(controller):
    appointment = make_appointment()
    controller.add_appointment(appointment)
    saturday = RescheduleDecision(new_date=date(2025, 3, 22), new_time=time(10), final=True)
    agent = PlannerAgent(client=ScriptedClient([saturday]), controller=controller, audio=object())

    conversation, _ = agent.start_rescheduling(appointment)
    agent.handle_patient_message(conversation, "Samedi 22 à 10h")

    assert not conversation.done
    assert controller.get_day_appointments(date(2025, 3, 20)) == [appointment]
    assert "not available" in conversation.messages[-2].content


def test_finished_conversation_rejects_new_messages(controller):
    appointment = make_appointment()
    controller.add_appointment(appointment)
    confirm = RescheduleDecision(new_date=date(2025, 3, 24), new_time=time(9), final=True)
    agent = PlannerAgent(client=ScriptedClient([confirm]), controller=controller, audio=object())
    conversation, _ = agent.start_rescheduling(appointment)
    agent.handle_patient_message(conversation, "Lundi 24 à 9h, parfait")

    with pytest.raises(ValueError):
        agent.handle_patient_message(conversation, "Encore une chose")


@pytest.mark.parametrize("today, expected", [
    (date(2026, 9, 23), "Today is Thursday 2025-03-20"),
    (date(2025, 3, 3), "Today is Monday 2025-03-03"),
])
def test_reference_date_is_today_only_within_the_planning_year(controller, monkeypatch, today, expected):
    monkeypatch.setattr(planner_agent, "current_date", lambda: today)
    appointment = make_appointment()
    controller.add_appointment(appointment)
    agent = PlannerAgent(client=ScriptedClient(), controller=controller, audio=object())

    conversation, _ = agent.start_rescheduling(appointment)

    assert expected in conversation.messages[0].content
