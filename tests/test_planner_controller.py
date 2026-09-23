from datetime import date, datetime, time

import pytest

from secretary_ai.agents.planner_controller import (
    Appointment,
    PlannerController,
    french_public_holidays,
)

DAY = date(2025, 3, 5)


def make_appointment(start: time, day: date = DAY, doctor=None) -> Appointment:
    return Appointment(id=f"{day}-{start}-{doctor}", name="Alice", surname="Martin", date=day,
                       mail="alice@example.com", start_time=start, doctor=doctor)


@pytest.fixture
def controller(tmp_path):
    return PlannerController(path=tmp_path)


def test_new_calendar_file_is_created_empty(controller, tmp_path):
    assert (tmp_path / "calendar.json").exists()
    assert controller.all_appointments() == []


def test_added_appointment_is_persisted(controller, tmp_path):
    controller.add_appointment(make_appointment(time(10), doctor="Dr Claire Morel"))

    reloaded = PlannerController(path=tmp_path)
    assert reloaded.get_day_appointments(DAY) == [make_appointment(time(10), doctor="Dr Claire Morel")]


def test_overlapping_appointment_is_rejected(controller):
    controller.add_appointment(make_appointment(time(10)))

    with pytest.raises(ValueError, match="Overlapping"):
        controller.add_appointment(make_appointment(time(10, 15)))


def test_back_to_back_appointments_are_allowed(controller):
    controller.add_appointment(make_appointment(time(10)))
    controller.add_appointment(make_appointment(time(10, 30)))

    assert [a.start_time for a in controller.get_day_appointments(DAY)] == [time(10), time(10, 30)]


def test_delete_appointment(controller):
    appointment = make_appointment(time(9))
    controller.add_appointment(appointment)

    controller.delete_appointment(appointment)

    assert controller.get_day_appointments(DAY) == []
    with pytest.raises(ValueError, match="not found"):
        controller.delete_appointment(appointment)


def test_all_appointments_are_sorted_chronologically(controller):
    later = make_appointment(time(9), day=date(2025, 6, 1))
    earlier = make_appointment(time(16))
    controller.add_appointment(later)
    controller.add_appointment(earlier)

    assert controller.all_appointments() == [earlier, later]


def test_free_day_has_sixteen_slots_within_working_hours(controller):
    slots = controller.get_day_available_timeslots(DAY)

    assert len(slots) == 16
    assert slots[0] == datetime(2025, 3, 5, 8)
    assert slots[-1] == datetime(2025, 3, 5, 17, 30)
    assert datetime(2025, 3, 5, 12) not in slots


def test_booked_slot_is_not_available(controller):
    controller.add_appointment(make_appointment(time(14)))

    slots = controller.get_day_available_timeslots(DAY)

    assert datetime(2025, 3, 5, 14) not in slots
    assert datetime(2025, 3, 5, 14, 30) in slots


def test_week_views_start_on_monday(controller):
    controller.add_appointment(make_appointment(time(11)))

    week = controller.get_week_appointments(DAY)

    assert len(week) == 7
    assert week[DAY.weekday()] == [make_appointment(time(11))]


def test_appointments_are_found_by_id(controller):
    appointment = make_appointment(time(10))
    controller.add_appointment(appointment)

    assert controller.find(appointment.id) is appointment
    assert controller.find("unknown") is None


def test_calendar_spans_several_years(controller):
    controller.add_appointment(make_appointment(time(10), day=date(2026, 12, 30)))
    controller.add_appointment(make_appointment(time(10), day=date(2027, 1, 4)))

    assert list(controller.months().values()) == [1, 1]
    assert [m.year for m in controller.months()] == [2026, 2027]


def test_doctors_have_separate_agendas(controller):
    controller.add_appointment(make_appointment(time(10), doctor="Dr Claire Morel"))
    controller.add_appointment(make_appointment(time(10), doctor="Dr Julien Roux"))

    with pytest.raises(ValueError, match="Overlapping"):
        controller.add_appointment(make_appointment(time(10), doctor="Dr Julien Roux"))
    assert datetime(2025, 3, 5, 10) not in controller.get_day_available_timeslots(DAY, "Dr Claire Morel")
    assert datetime(2025, 3, 5, 10) in controller.get_day_available_timeslots(DAY, "Marc Lefort")


def test_no_slots_on_weekends(controller):
    assert controller.get_day_available_timeslots(date(2025, 3, 8)) == []
    assert controller.get_day_available_timeslots(date(2025, 3, 9)) == []


def test_no_slots_on_public_holidays(controller):
    assert date(2026, 4, 6) in french_public_holidays(2026)  # Easter Monday
    assert date(2027, 5, 6) in french_public_holidays(2027)  # Ascension
    assert controller.get_day_available_timeslots(date(2026, 11, 11)) == []


def test_month_view_follows_calendar_weeks(controller):
    month = controller.get_month_available_timeslots(date(2025, 3, 1))

    # March 2025 starts on a Saturday: five padding days, then the first weekend.
    assert month[0] == [[], [], [], [], [], [], []]
    assert [len(day) for day in month[1]] == [16, 16, 16, 16, 16, 0, 0]
