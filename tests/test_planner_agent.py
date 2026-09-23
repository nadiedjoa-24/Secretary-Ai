from datetime import date, time

import pytest

from secretary_ai.agents.planner_agent import PlannerAgent
from secretary_ai.agents.planner_controller import Appointment, PlannerController


@pytest.fixture
def agent(tmp_path):
    # No AI client or microphone is needed to compute free slots.
    return PlannerAgent(client=object(), controller=PlannerController(year=2025, path=tmp_path), audio=object())


def test_slots_cover_the_rest_of_the_month_and_the_next_one(agent):
    slots = agent.get_available_timeslots(date(2025, 3, 20))

    assert sorted(slots) == [3, 4]
    assert min(slots[3]) == 20
    assert len(slots[4]) == 22  # weekdays of April 2025


def test_november_rolls_over_to_december(agent):
    slots = agent.get_available_timeslots(date(2025, 11, 28))

    assert sorted(slots) == [11, 12]


def test_december_rolls_over_to_january(agent):
    slots = agent.get_available_timeslots(date(2025, 12, 30))

    assert sorted(slots) == [1, 12]


def test_booked_slot_is_excluded(agent):
    agent.controller.add_appointment(Appointment(
        name="Alice", surname="Martin", date=date(2025, 3, 21), mail="alice@example.com", start_time=time(8)))

    slots = agent.get_available_timeslots(date(2025, 3, 20))

    assert "08:00" not in slots[3][21]
    assert "08:00" in slots[3][20]
