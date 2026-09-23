import sys
import tempfile
from datetime import date, time, timedelta
from pathlib import Path

# remonte jusqu’à la racine du projet
SCRIPT_DIR   = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

from common.data_models.planning    import Planning
from common.data_models.work_hours  import WorkHours, TimeSlot
from common.data_models.appointment import Appointment

def make_appointment(day: date, start_hour: int, end_hour: int, id_: int = 1, patient_id: int = 1):
    """
    Crée un Appointment pour le même jour de start_hour à end_hour.
    """
    start_time = time(start_hour, 0)
    duration   = (end_hour - start_hour) * 60
    return Appointment(
        id               = id_,
        patient_id       = patient_id,
        appointment_date = day,
        start_time       = start_time,
        duration         = duration
    )

def test_get_day_appoints():
    today = date(2025, 5, 20)
    a1 = make_appointment(today,  9, 10, id_=1)
    a2 = make_appointment(today, 11, 12, id_=2)
    a3 = make_appointment(today + timedelta(days=1), 9, 10, id_=3)

    pl = Planning(items=[a1, a2, a3], year=2025)
    result = pl.get_day_appoints(today)
    print(f"get_day_appoints({today}) => {result}")
    assert result == [a1, a2], f"Expected [a1, a2], got {result}"

def test_get_week_appoints():
    ref_day = date(2025, 5, 21)  # mercredi
    monday  = ref_day - timedelta(days=ref_day.weekday())
    a_mon = make_appointment(monday, 8, 9, id_=1)
    a_wed = make_appointment(monday + timedelta(days=2), 10, 11, id_=2)
    pl = Planning(items=[a_mon, a_wed], year=2025)

    week = pl.get_week_appoints(ref_day)
    print(f"get_week_appoints({ref_day}) =>")
    for i, day_list in enumerate(week):
        day = monday + timedelta(days=i)
        print(f"  {day}: {day_list}")
    assert len(week) == 7, f"Expected 7 days, got {len(week)}"
    assert week[0] == [a_mon] and week[2] == [a_wed], "Week contents mismatch"

def test_get_month_appoints():
    ref_day = date(2025, 5, 15)
    may1    = date(2025, 5, 1)
    a1 = make_appointment(may1, 9, 10, id_=1)
    pl = Planning(items=[a1], year=2025)

    month = pl.get_month_appoints(ref_day)
    print(f"get_month_appoints({ref_day}) =>")
    for w, week in enumerate(month):
        print(f"  Week {w}:")
        for d, day_list in enumerate(week):
            print(f"    Day {d}: {day_list}")
    assert all(isinstance(wk, list) and len(wk) == 7 for wk in month), "Each week must have 7 days"
    assert month[0][3] == [a1], f"1er mai should be in first week day 3, got {month[0][3]}"

def test_get_day_free_slots():
    day = date(2025, 5, 19)  # lundi
    tmp = tempfile.mkdtemp()
    wh = WorkHours.load(doctor_id=1, year=2025, directory=tmp)

    a1 = make_appointment(day,  9, 10, id_=1)
    a2 = make_appointment(day, 15, 16, id_=2)
    pl = Planning(items=[a1, a2], year=2025)

    free = pl.get_day_free_slots(day, wh)
    print(f"get_day_free_slots({day}) => {free}")
    expected = [
        TimeSlot(start=time(8,0),  end=time(9,0)),
        TimeSlot(start=time(10,0), end=time(12,0)),
        TimeSlot(start=time(14,0), end=time(15,0)),
        TimeSlot(start=time(16,0), end=time(18,0)),
    ]
    assert free == expected, f"Expected {expected}, got {free}"

def test_get_week_free_slots_consistency():
    ref_day = date(2025, 5, 19)  # lundi
    tmp = tempfile.mkdtemp()
    wh = WorkHours.load(doctor_id=1, year=2025, directory=tmp)
    pl = Planning(items=[], year=2025)

    week_free = pl.get_week_free_slots(ref_day, wh)
    print(f"get_week_free_slots({ref_day}) => {week_free}")
    assert len(week_free) == 7, f"Expected 7 days, got {len(week_free)}"
    day0 = pl.get_day_free_slots(ref_day, wh)
    assert week_free[0] == day0, f"Week[0] {week_free[0]} != day0 {day0}"

def test_get_month_free_slots_shape():
    ref_day = date(2025, 5, 15)
    tmp = tempfile.mkdtemp()
    wh = WorkHours.load(doctor_id=1, year=2025, directory=tmp)
    pl = Planning(items=[], year=2025)

    month_free = pl.get_month_free_slots(ref_day, wh)
    print(f"get_month_free_slots({ref_day}) =>")
    for w, week in enumerate(month_free):
        print(f"  Week {w}: {week}")
    assert all(isinstance(wk, list) and len(wk) == 7 for wk in month_free), "Month free slots shape bad"


def test_month_free_slots_with_appointment():

    ref_day = date(2025, 5, 15)
    rdv = make_appointment(date(2025, 5, 1), 9, 10, id_=42, patient_id=7)
    pl = Planning(items=[rdv], year=2025)
    tmp = tempfile.mkdtemp()
    wh  = WorkHours.load(doctor_id=1, year=2025, directory=tmp)

    month_free = pl.get_month_free_slots(ref_day, wh)

    slots_1er_mai = month_free[0][3]
    print(f"Créneaux libres le 1er mai : {slots_1er_mai}")

    expected = [
        TimeSlot(start=time(8,0), end=time(9,0)),
        TimeSlot(start=time(10,0),end=time(12,0)),
        TimeSlot(start=time(14,0),end=time(18,0)),
    ]
    assert slots_1er_mai == expected, f"Attendu : {expected}, obtenu : {slots_1er_mai}"


if __name__ == "__main__":
    tests = [
        test_get_day_appoints,
        test_get_week_appoints,
        test_get_month_appoints,
        test_get_day_free_slots,
        test_get_week_free_slots_consistency,
        test_get_month_free_slots_shape,
        test_month_free_slots_with_appointment,
    ]

    all_passed = True
    for t in tests:
        try:
            t()
            print(f"{t.__name__}: PASS\n")
        except AssertionError as e:
            all_passed = False
            print(f"{t.__name__}: FAIL -> {e}\n")

    if all_passed:
        print("✔︎ Tous les tests ont réussi.")
    else:
        print("✘ Certains tests ont échoué.")