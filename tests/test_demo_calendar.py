from datetime import date

from secretary_ai.agents.demo_calendar import generate, shift_months
from secretary_ai.agents.planner_controller import DOCTORS, is_working_day

TODAY = date(2026, 9, 23)


def test_calendar_covers_twenty_months_back_and_four_ahead():
    appointments = generate(TODAY)

    assert appointments[0].date.replace(day=1) == date(2025, 1, 1)
    assert appointments[-1].date.replace(day=1) == date(2027, 1, 1)


def test_generation_is_reproducible():
    assert generate(TODAY) == generate(TODAY)


def test_appointments_fit_the_rules_of_the_office():
    appointments = generate(TODAY)
    bookings = [(a.doctor, a.date, a.start_time) for a in appointments]

    assert len(set(bookings)) == len(bookings)  # no double booking
    assert all(is_working_day(a.date) and a.doctor in DOCTORS for a in appointments)
    assert all(a.start_time.minute in (0, 30) for a in appointments)


def test_past_is_busier_than_the_future():
    appointments = generate(TODAY)
    september_2025 = sum(a.date.replace(day=1) == date(2025, 9, 1) for a in appointments)
    december_2026 = sum(a.date.replace(day=1) == date(2026, 12, 1) for a in appointments)

    assert september_2025 > 3 * december_2026 > 0


def test_shift_months_crosses_years():
    assert shift_months(date(2026, 9, 23), -20) == date(2025, 1, 1)
    assert shift_months(date(2026, 9, 23), 4) == date(2027, 1, 1)
