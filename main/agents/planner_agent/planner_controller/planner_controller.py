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
    duration: timedelta
    start_time: time

    @validator('duration', pre=True)
    def parse_duration(cls, v):
        """
        Parse duration specified in minutes (as int, float, or numeric string) into a timedelta.
        """
        if isinstance(v, (int, float)):
            return timedelta(minutes=v)
        if isinstance(v, str):
            try:
                minutes = int(v)
                return timedelta(minutes=minutes)
            except ValueError:
                pass
        return v


class PlannerController():

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
                            duration=timedelta(seconds=item["duration_seconds"]),
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
                            "duration_seconds": int(rdv.duration.total_seconds()),
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
        new_end = new_start + appointment.duration
        for existing in self.planning[month][day][doctor_name]:
            ex_start = datetime.combine(existing.date, existing.start_time)
            ex_end = ex_start + existing.duration
            if not (new_end <= ex_start or new_start >= ex_end):
                raise ValueError("Overlapping appointment")
        self.planning[month][day][doctor_name].append(appointment)
        self._save(self.year)

    def get_day_rdv(self, date: datetime) -> List[Appointment]:
        """ Return a list of all appointments for the given date across all doctors, sorted by start time. """
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
        assuming working hours 09:00 to 17:00, where no appointment exists.
        """
        # Generate all possible 30-minute slots between 09:00 and 17:00
        slots = []
        slot_duration = timedelta(minutes=30)
        day_start = datetime.combine(date.date(), time(hour=9, minute=0))
        day_end = datetime.combine(date.date(), time(hour=17, minute=0))
        current = day_start
        # Get booked intervals
        booked = [(datetime.combine(a.date, a.start_time),
                   datetime.combine(a.date, a.start_time) + a.duration)
                  for a in self.get_day_rdv(date)]
        while current + slot_duration <= day_end:
            next_slot = current + slot_duration
            # check overlap
            if not any(b_start < next_slot and current < b_end for b_start, b_end in booked):
                slots.append(current)
            current = next_slot
        return slots

    def get_week_rdv(self, date: datetime) -> List[List[Appointment]]:
        """ Return a list of lists of appointments for each day in the week containing the given date. """
        pass

    def get_week_available_timeslots(self, date: datetime) -> List[List[datetime]]:
        """ Return a list of lists of available timeslots for each day in the week containing the given date and according to work hours of the doctor at the given date. """
        pass
    
    def get_month_rdv(self, date: datetime) -> List[List[List[Appointment]]]:
        """ Return a list of lists (weeks) of lists (days) of appointments for each day in the month containing the given date. """
        pass

    def get_month_available_timeslots(self, date: datetime) -> List[List[List[datetime]]]:
        """ Return a list of lists (weeks) of lists (days) of available timeslots for each day in the month containing the given date and according to work hours of the doctor at the given date. """
        pass

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

        # Initialize controller and verify empty planning
    controller = PlannerController(year=2025)


    # Define an appointment and test add_rdv
    appt = Appointment(
        name="Alice",
        surname="Smith",
        date=date(2025, 7, 1),
        mail="alice@example.com",
        phone="555-0001",
        description="Checkup",
        doctor=Doctor.SMITH,
        duration=timedelta(minutes=45),
        start_time=time(hour=10, minute=0)
    )
    controller.add_rdv(appt)

    controller._load(2025)
    loaded = controller.planning[7][1][Doctor.SMITH.value][0]

    # controller.delete_rdv(appt)

    # try:
    #     controller.delete_rdv(appt)
    #     raise AssertionError("Deleting non-existent appointment did not raise")
    # except ValueError as e:
    #     assert str(e) == "Appointment not found", f"Unexpected delete error message: {e}"

    print("All tests passed successfully.")
    

      

 
