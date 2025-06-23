import json
from pathlib import Path
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime, date, time, timedelta
from pydantic import BaseModel, validator
import calendar


class Doctor(str, Enum):
    SMITH = "Smith"
    JOHNSON = "Johnson"


class Appointment(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    date: date
    mail: str
    phone: Optional[str] = None
    description: Optional[str] = None
    doctor: Doctor
    start_time: time


class PlannerController():

    APPOINTMENT_DURATION = timedelta(minutes=30)

    def __init__(self, year, path: str = "./planning_json/"):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.year = year
        self.planning: Dict[int, Dict[int, Dict[str, List[Appointment]]]] = {}
        self._load(year)


    def _init_year(self, year: int):
        """Initialize the planning for a given year with empty days and both doctors."""
        # Build empty planning structure for all months, days, and doctors
        self.planning = {}
        for month in range(1, 13):
            num_days = calendar.monthrange(year, month)[1]
            self.planning[month] = {}
            for day in range(1, num_days + 1):
                # Initialize an empty list of appointments for each doctor
                self.planning[month][day] = {doc.value: [] for doc in Doctor}
        # Persist the initialized year to disk
        self._save(year)

    def _load(self, year: int):
        file_path = self.path / f"{year}.json"
        if not file_path.exists():
            self._init_year(year)
            return

        with file_path.open("r") as f:
            data = json.load(f)
        self.planning = {}
        for month_str, days in data.items():
            month = int(month_str)
            self.planning[month] = {}
            for day_str, doctors in days.items():
                day = int(day_str)
                self.planning[month][day] = {}
                for doctor_name, rdv_list in doctors.items():
                    self.planning[month][day][doctor_name] = [
                        Appointment(
                            name=item.get("name"),
                            surname=item.get("surname"),
                            date=date.fromisoformat(item["date"]),
                            mail=item["mail"],
                            phone=item.get("phone"),
                            description=item.get("description"),
                            doctor=Doctor(item["doctor"]),
                            start_time=time.fromisoformat(item["start_time"])
                        )
                        for item in rdv_list
                    ]

    def _save(self, year: int):
        file_path = self.path / f"{year}.json"
        data: Dict[str, Dict[str, Dict[str, List[Dict]]]] = {}
        for month, days in self.planning.items():
            data[str(month)] = {}
            for day, doctors in days.items():
                data[str(month)][str(day)] = {}
                for doc_name, rdvs in doctors.items():
                    data[str(month)][str(day)][doc_name] = [
                        {
                            "name": rdv.name,
                            "surname": rdv.surname,
                            "date": rdv.date.isoformat(),
                            "mail": rdv.mail,
                            "phone": rdv.phone,
                            "description": rdv.description,
                            "doctor": rdv.doctor.value,
                            "start_time": rdv.start_time.isoformat()
                        }
                        for rdv in rdvs
                    ]
        with file_path.open("w") as f:
            json.dump(data, f, indent=4)

    def add_rdv(self, appointment: Appointment):
        month = appointment.date.month
        day = appointment.date.day
        doctor_name = appointment.doctor.value
        self.planning.setdefault(month, {}).setdefault(day, {}).setdefault(doctor_name, [])
        new_start = datetime.combine(appointment.date, appointment.start_time)
        new_end = new_start + self.APPOINTMENT_DURATION
        for existing in self.planning[month][day][doctor_name]:
            ex_start = datetime.combine(existing.date, existing.start_time)
            ex_end = ex_start + self.APPOINTMENT_DURATION
            if not (new_end <= ex_start or new_start >= ex_end):
                raise ValueError("Overlapping appointment")
        self.planning[month][day][doctor_name].append(appointment)
        self._save(self.year)

    def get_day_rdv(self, date: datetime) -> List[Appointment]:
        """ Return a list of all appointments for the given date across all doctors, sorted by start time. Work-hours : 8:00 to 12:00 and 14:00 to 18:00. """
        day_planning = self.planning.get(date.month, {}).get(date.day, {})
        # Flatten appointments from all doctors
        appts = []
        for doc_appts in day_planning.values():
            appts.extend(doc_appts)
        # Sort by start_time
        return sorted(appts, key=lambda a: a.start_time)

    def get_day_available_timeslots(self, date: datetime) -> List[datetime]:
        """
        Return a list of available 30-minute timeslot start datetimes for the given date,
        assuming working hours 08:00 to 12:00 and 14:00 to 18:00, where no appointment exists.
        """
        slots = []
        slot_duration = self.APPOINTMENT_DURATION
        # Gather booked intervals with fixed duration
        booked = [
            (
                datetime.combine(a.date, a.start_time),
                datetime.combine(a.date, a.start_time) + slot_duration
            )
            for a in self.get_day_rdv(date)
        ]
        # Morning slots: 08:00 to 12:00
        current = datetime.combine(date.date(), time(hour=8))
        morning_end = datetime.combine(date.date(), time(hour=12))
        while current + slot_duration <= morning_end:
            next_slot = current + slot_duration
            if not any(b_start < next_slot and current < b_end for b_start, b_end in booked):
                slots.append(current)
            current = next_slot
        # Afternoon slots: 14:00 to 18:00
        current = datetime.combine(date.date(), time(hour=14))
        afternoon_end = datetime.combine(date.date(), time(hour=18))
        while current + slot_duration <= afternoon_end:
            next_slot = current + slot_duration
            if not any(b_start < next_slot and current < b_end for b_start, b_end in booked):
                slots.append(current)
            current = next_slot
        return slots

    def get_week_rdv(self, date: datetime) -> List[List[Appointment]]:
        # Compute start of week (Monday)
        start = date - timedelta(days=date.weekday())
        week = []
        for i in range(7):
            day = start + timedelta(days=i)
            week.append(self.get_day_rdv(datetime.combine(day.date(), time())))
        return week

    def get_week_available_timeslots(self, date: datetime) -> List[List[datetime]]:
        # Compute start of week (Monday)
        start = date - timedelta(days=date.weekday())
        week_slots = []
        for i in range(7):
            day = start + timedelta(days=i)
            week_slots.append(self.get_day_available_timeslots(datetime.combine(day.date(), time())))
        return week_slots
    
    def get_month_rdv(self, date: datetime) -> List[List[List[Appointment]]]:
        year = date.year
        month = date.month
        cal = calendar.monthcalendar(year, month)
        month_rdv = []
        for week in cal:
            week_rdv = []
            for day in week:
                if day == 0:
                    week_rdv.append([])
                else:
                    week_date = datetime(year, month, day)
                    week_rdv.append(self.get_day_rdv(datetime.combine(week_date.date(), time())))
            month_rdv.append(week_rdv)
        return month_rdv

    def get_month_available_timeslots(self, date: datetime) -> List[List[List[datetime]]]:
        year = date.year
        month = date.month
        cal = calendar.monthcalendar(year, month)
        month_slots = []
        for week in cal:
            week_slots = []
            for day in week:
                if day == 0:
                    week_slots.append([])
                else:
                    week_date = datetime(year, month, day)
                    week_slots.append(self.get_day_available_timeslots(datetime.combine(week_date.date(), time())))
            month_slots.append(week_slots)
        return month_slots

    def delete_rdv(self, appointment: Appointment):
        """" Delete an appointment from the planning and save the planning. """
        month = appointment.date.month
        day = appointment.date.day
        doctor_name = appointment.doctor.value
        try:
            self.planning[month][day][doctor_name].remove(appointment)
            # Clean up empty containers
            if not self.planning[month][day][doctor_name]:
                del self.planning[month][day][doctor_name]
            if not self.planning[month][day]:
                del self.planning[month][day]
            if not self.planning[month]:
                del self.planning[month]
            self._save(self.year)
        except (KeyError, ValueError):
            raise ValueError("Appointment not found")
    


# Test
if __name__ == "__main__":

    test_dir = Path("./planning_json_test/")
    if test_dir.exists():
        for f in test_dir.iterdir():
            if f.is_file():
                f.unlink()
        test_dir.rmdir()

    controller = PlannerController(year=2025)

    appt = Appointment(
        name="Alice",
        surname="Smith",
        date=date(2025, 1, 1),
        mail="alice@example.com",
        phone="555-0001",
        description="Checkup",
        doctor=Doctor.SMITH,
        duration=timedelta(minutes=45),
        start_time=time(hour=10, minute=0)
    )
    try: 
        controller.add_rdv(appt)
    except ValueError as e:
        print(f"Failed to add appointment: {e}")

    controller._load(2025)
    loaded = controller.planning[7][1][Doctor.SMITH.value][0]

    # controller.delete_rdv(appt)

    # try:
    #     controller.delete_rdv(appt)
    #     raise AssertionError("Deleting non-existent appointment did not raise")
    # except ValueError as e:
    #     assert str(e) == "Appointment not found", f"Unexpected delete error message: {e}"

    print("All tests passed successfully.")
    
    # Generic test: retrieve appointments and available timeslots for a given day
    test_date = date(2025, 1, 1)
    # Fetch all appointments for the test date
    day_appts = controller.get_day_rdv(datetime.combine(test_date, time()))
    assert len(day_appts) > 0, f"Expected at least one appointment on {test_date}, got {len(day_appts)}"
    print(f"Found {len(day_appts)} appointments on {test_date}: {[a.start_time.isoformat() for a in day_appts]}")
    # Fetch available timeslots for the same date
    slots = controller.get_day_available_timeslots(datetime.combine(test_date, time()))
    slot_times = [slot.time() for slot in slots]
    # Verify that no appointment start time appears in available slots
    for appt in day_appts:
        assert appt.start_time not in slot_times, f"Slot {appt.start_time} should be marked occupied"
    print(f"Available timeslots on {test_date}: {[t.isoformat() for t in slot_times]}")
    print("Generic test passed: get_day_rdv and get_day_available_timeslots for a given day")

    # Test: week appointments and available timeslots for week of test_date
    week_rdv = controller.get_week_rdv(datetime.combine(test_date, time()))
    assert len(week_rdv) == 7, f"Expected 7 days in week_rdv, got {len(week_rdv)}"
    week_slots = controller.get_week_available_timeslots(datetime.combine(test_date, time()))
    assert len(week_slots) == 7, f"Expected 7 lists in week_slots, got {len(week_slots)}"
    # Verify each day's appointments and slots match daily methods
    start_week = test_date - timedelta(days=test_date.weekday())
    for i in range(7):
        day = start_week + timedelta(days=i)
        day_dt = datetime.combine(day, time())
        expected_appts = controller.get_day_rdv(day_dt)
        assert week_rdv[i] == expected_appts, f"get_week_rdv mismatch on {day.date()}"
        expected_slots = controller.get_day_available_timeslots(day_dt)
        assert week_slots[i] == expected_slots, f"get_week_available_timeslots mismatch on {day.date()}"
    print(f"Week tests passed for the week of {test_date}")

    # Test: month appointments and available timeslots for month of test_date
    month_rdv = controller.get_month_rdv(datetime.combine(test_date, time()))
    month_slots = controller.get_month_available_timeslots(datetime.combine(test_date, time()))
    year = test_date.year
    month = test_date.month
    cal = calendar.monthcalendar(year, month)
    # Verify each week/day cell matches daily methods or is empty for padding
    for w_idx, week in enumerate(cal):
        for d_idx, day in enumerate(week):
            if day == 0:
                assert month_rdv[w_idx][d_idx] == [], f"Expected empty appointments for placeholder at week {w_idx}, day {d_idx}"
                assert month_slots[w_idx][d_idx] == [], f"Expected empty slots for placeholder at week {w_idx}, day {d_idx}"
            else:
                day_dt = datetime(year, month, day)
                expected_appts = controller.get_day_rdv(datetime.combine(day_dt.date(), time()))
                assert month_rdv[w_idx][d_idx] == expected_appts, f"get_month_rdv mismatch on {day_dt.date()}"
                expected_slots = controller.get_day_available_timeslots(datetime.combine(day_dt.date(), time()))
                assert month_slots[w_idx][d_idx] == expected_slots, f"get_month_available_timeslots mismatch on {day_dt.date()}"
    print(f"Month tests passed for {month}/{year}")
    

      

 
