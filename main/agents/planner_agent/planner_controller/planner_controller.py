import json
from pathlib import Path
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime, date, time, timedelta
from pydantic import BaseModel


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


class PlannerController():

    def __init__(self, year, path: str = "./planning_json/"):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.year = year
        self.planning: Dict[int, Dict[int, Dict[str, List[Appointment]]]] = {}
        self._load(year)


    def _init_year(self, year: int):
        """Initialize the planning for a given year if it does not exist."""
        file_path = self.path / f"{year}.json"
        if not file_path.exists():
            # create an empty planning file for this year
            with file_path.open("w") as f:
                json.dump({}, f, indent=4)
        self.planning = {}

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
        """ Return a list of appointments for a day at a given date."""
        pass

    def get_day_available_timeslots(self, date: datetime) -> List[datetime]:
        """ Return a list of available timesolts for a day at a given date and according to work hours of the doctor at the given date. """
        pass

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
    from pathlib import Path
        # Prepare a clean test directory
    test_dir = Path("./planning_json_test/")
    if test_dir.exists():
        for f in test_dir.iterdir():
            if f.is_file():
                f.unlink()
        test_dir.rmdir()

        # Initialize controller and verify empty planning
    controller = PlannerController(year=2025, path=test_dir)
    assert controller.planning == {}, "Planning should be empty on init"

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
    # After adding, the entry should exist
    assert 7 in controller.planning, "Month key missing after add"
    assert 1 in controller.planning[7], "Day key missing after add"
    assert controller.planning[7][1][Doctor.SMITH.value][0] == appt, "Appointment not stored correctly"


        # Test persistence via _load
    controller._load(2025)
    loaded = controller.planning[7][1][Doctor.SMITH.value][0]
    assert loaded == appt, "Loaded appointment does not match saved"

        # Test delete_rdv
    controller.delete_rdv(appt)
    assert controller.planning == {}, "Planning should be empty after delete"

        # Test deleting a non-existent appointment
    try:
        controller.delete_rdv(appt)
        raise AssertionError("Deleting non-existent appointment did not raise")
    except ValueError as e:
        assert str(e) == "Appointment not found", f"Unexpected delete error message: {e}"

    print("All tests passed successfully.")
    

      

 
