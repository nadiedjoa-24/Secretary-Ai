import calendar
import json
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel

from secretary_ai.config import PLANNING_DIR

WORKING_HOURS = [(time(8), time(12)), (time(14), time(18))]


class Appointment(BaseModel):
    name: Optional[str]
    surname: Optional[str]
    date: date
    mail: str
    phone: Optional[str] = None
    description: Optional[str] = None
    start_time: time


def _naive(moment: datetime) -> datetime:
    return moment.replace(tzinfo=None)


class PlannerController:
    """Stores a year of appointments in a JSON file and computes free time slots."""

    APPOINTMENT_DURATION = timedelta(minutes=30)

    def __init__(self, year: int, path: Path = PLANNING_DIR):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.year = year
        self.planning: Dict[int, Dict[int, List[Appointment]]] = {}
        self._load()

    @property
    def _file(self) -> Path:
        return self.path / f"{self.year}.json"

    def _load(self) -> None:
        if not self._file.exists():
            self.planning = {
                month: {day: [] for day in range(1, calendar.monthrange(self.year, month)[1] + 1)}
                for month in range(1, 13)
            }
            self._save()
            return

        data = json.loads(self._file.read_text(encoding="utf-8"))
        self.planning = {
            int(month): {
                int(day): [Appointment.model_validate(item) for item in appointments]
                for day, appointments in days.items()
            }
            for month, days in data.items()
        }

    def _save(self) -> None:
        data = {
            str(month): {
                str(day): [appointment.model_dump(mode="json") for appointment in appointments]
                for day, appointments in days.items()
            }
            for month, days in self.planning.items()
        }
        self._file.write_text(json.dumps(data, indent=4, ensure_ascii=False), encoding="utf-8")

    def _interval(self, appointment: Appointment) -> tuple[datetime, datetime]:
        start = _naive(datetime.combine(appointment.date, appointment.start_time))
        return start, start + self.APPOINTMENT_DURATION

    def add_appointment(self, appointment: Appointment) -> None:
        appointment.start_time = appointment.start_time.replace(tzinfo=None)
        day_appointments = self.planning.setdefault(appointment.date.month, {}).setdefault(appointment.date.day, [])
        new_start, new_end = self._interval(appointment)
        for existing in day_appointments:
            start, end = self._interval(existing)
            if new_start < end and start < new_end:
                raise ValueError("Overlapping appointment")
        day_appointments.append(appointment)
        self._save()

    def delete_appointment(self, appointment: Appointment) -> None:
        try:
            self.planning[appointment.date.month][appointment.date.day].remove(appointment)
        except (KeyError, ValueError):
            raise ValueError("Appointment not found") from None
        self._save()

    def all_appointments(self) -> List[Appointment]:
        """Every appointment of the year, in chronological order."""
        appointments = [a for days in self.planning.values() for day in days.values() for a in day]
        return sorted(appointments, key=lambda a: (a.date, a.start_time.replace(tzinfo=None)))

    def get_day_appointments(self, day: date) -> List[Appointment]:
        appointments = self.planning.get(day.month, {}).get(day.day, [])
        return sorted(appointments, key=lambda appointment: appointment.start_time)

    def get_day_available_timeslots(self, day: date) -> List[datetime]:
        """Free 30-minute slots within working hours: weekdays, 08:00-12:00 and 14:00-18:00."""
        if day.weekday() >= 5:
            return []
        booked = [self._interval(appointment) for appointment in self.get_day_appointments(day)]
        slots = []
        for opening, closing in WORKING_HOURS:
            current = datetime.combine(day, opening)
            end = datetime.combine(day, closing)
            while current + self.APPOINTMENT_DURATION <= end:
                slot_end = current + self.APPOINTMENT_DURATION
                if not any(start < slot_end and current < stop for start, stop in booked):
                    slots.append(current)
                current = slot_end
        return slots

    def get_week_appointments(self, day: date) -> List[List[Appointment]]:
        monday = day - timedelta(days=day.weekday())
        return [self.get_day_appointments(monday + timedelta(days=offset)) for offset in range(7)]

    def get_week_available_timeslots(self, day: date) -> List[List[datetime]]:
        monday = day - timedelta(days=day.weekday())
        return [self.get_day_available_timeslots(monday + timedelta(days=offset)) for offset in range(7)]

    def get_month_appointments(self, day: date) -> List[List[List[Appointment]]]:
        """Appointments laid out as calendar weeks; days outside the month are empty lists."""
        return [
            [self.get_day_appointments(date(day.year, day.month, d)) if d else [] for d in week]
            for week in calendar.monthcalendar(day.year, day.month)
        ]

    def get_month_available_timeslots(self, day: date) -> List[List[List[datetime]]]:
        """Free slots laid out as calendar weeks; days outside the month are empty lists."""
        return [
            [self.get_day_available_timeslots(date(day.year, day.month, d)) if d else [] for d in week]
            for week in calendar.monthcalendar(day.year, day.month)
        ]
