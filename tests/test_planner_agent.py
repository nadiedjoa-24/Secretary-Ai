from datetime import date, time

import pytest

from secretary_ai.agents import planner_agent
from secretary_ai.agents.planner_agent import PlannerAgent, RescheduleDecision
from secretary_ai.agents.planner_controller import Appointment, PlannerController
from secretary_ai.ai.base_model import Message

TODAY = date(2025, 3, 10)


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


def make_appointment(day=date(2025, 3, 20), start=time(10), doctor="Dr Claire Morel"):
    return Appointment(name="Alice", surname="Martin", date=day, mail="alice@example.com", start_time=start,
                       doctor=doctor)


@pytest.fixture(autouse=True)
def today(monkeypatch):
    monkeypatch.setattr(planner_agent, "current_date", lambda: TODAY)


@pytest.fixture
def controller(tmp_path):
    return PlannerController(path=tmp_path)


@pytest.fixture
def agent(controller):
    # No AI client or microphone is needed to compute free slots.
    return PlannerAgent(client=object(), controller=controller, audio=object())


def test_slots_cover_the_rest_of_the_month_and_the_next_one(agent):
    slots = agent.get_available_timeslots(date(2025, 3, 20))

    assert {day.month for day in slots} == {3, 4}
    assert min(slots) == date(2025, 3, 20)
    assert sum(day.month == 4 for day in slots) == 21  # working days of April 2025, Easter Monday excluded


def test_december_rolls_over_to_january_of_the_next_year(agent):
    slots = agent.get_available_timeslots(date(2025, 12, 30))

    assert {(day.year, day.month) for day in slots} == {(2025, 12), (2026, 1)}


def test_booked_slot_is_excluded_for_its_doctor_only(agent):
    agent.controller.add_appointment(make_appointment(day=date(2025, 3, 21), start=time(8)))

    assert "08:00" not in agent.get_available_timeslots(date(2025, 3, 20), "Dr Claire Morel")[date(2025, 3, 21)]
    assert "08:00" in agent.get_available_timeslots(date(2025, 3, 20), "Dr Julien Roux")[date(2025, 3, 21)]


def test_dates_are_written_the_french_way():
    assert planner_agent.french_date(date(2026, 10, 1)) == "jeudi 1er octobre 2026"
    assert planner_agent.french_date(date(2026, 9, 29)) == "mardi 29 septembre 2026"


def test_free_time_is_summarized_as_periods(agent):
    agent.controller.add_appointment(make_appointment(day=date(2025, 3, 21), start=time(9)))

    lines = agent.describe_free_time(date(2025, 3, 20), "Dr Claire Morel").splitlines()

    assert lines[0] == "jeudi 20 mars 2025: 08:00-12:00, 14:00-18:00"
    assert lines[1] == "vendredi 21 mars 2025: 08:00-09:00, 09:30-12:00, 14:00-18:00"
    assert len(lines) == 8 + 21  # remaining working days of March, then April


def test_prompt_starts_from_today_with_the_free_time_of_the_same_doctor(controller):
    appointment = make_appointment()
    controller.add_appointment(appointment)
    controller.add_appointment(make_appointment(day=date(2025, 3, 11), start=time(8), doctor="Dr Julien Roux"))
    agent = PlannerAgent(client=ScriptedClient(), controller=controller, audio=object())

    conversation, _ = agent.start_rescheduling(appointment)
    prompt = conversation.messages[0].content

    assert "Today is lundi 10 mars 2025" in prompt
    assert "with Dr Claire Morel" in prompt
    assert "lundi 10 mars 2025:" not in prompt  # slots start tomorrow
    assert "mardi 11 mars 2025: 08:00-12:00" in prompt  # Dr Roux's booking does not matter


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
    moved = controller.get_day_appointments(date(2025, 3, 25))[0]
    assert (moved.start_time, moved.doctor) == (time(14), "Dr Claire Morel")


@pytest.mark.parametrize("new_date, new_time", [
    (date(2025, 3, 22), time(10)),  # Saturday
    (date(2025, 3, 5), time(10)),  # in the past
])
def test_unavailable_slot_is_refused_and_the_conversation_goes_on(controller, new_date, new_time):
    appointment = make_appointment()
    controller.add_appointment(appointment)
    decision = RescheduleDecision(new_date=new_date, new_time=new_time, final=True)
    agent = PlannerAgent(client=ScriptedClient([decision]), controller=controller, audio=object())

    conversation, _ = agent.start_rescheduling(appointment)
    agent.handle_patient_message(conversation, "Ce jour-là à 10h")

    assert not conversation.done
    assert controller.get_day_appointments(date(2025, 3, 20)) == [appointment]
    assert "not available" in conversation.messages[-2].content


def test_slot_taken_by_the_same_doctor_is_refused(controller):
    appointment = make_appointment()
    controller.add_appointment(appointment)
    controller.add_appointment(make_appointment(day=date(2025, 3, 24), start=time(9)))
    decision = RescheduleDecision(new_date=date(2025, 3, 24), new_time=time(9), final=True)
    agent = PlannerAgent(client=ScriptedClient([decision]), controller=controller, audio=object())

    conversation, _ = agent.start_rescheduling(appointment)
    agent.handle_patient_message(conversation, "Lundi 24 à 9h")

    assert not conversation.done


def test_finished_conversation_rejects_new_messages(controller):
    appointment = make_appointment()
    controller.add_appointment(appointment)
    confirm = RescheduleDecision(new_date=date(2025, 3, 24), new_time=time(9), final=True)
    agent = PlannerAgent(client=ScriptedClient([confirm]), controller=controller, audio=object())
    conversation, _ = agent.start_rescheduling(appointment)
    agent.handle_patient_message(conversation, "Lundi 24 à 9h, parfait")

    with pytest.raises(ValueError):
        agent.handle_patient_message(conversation, "Encore une chose")
