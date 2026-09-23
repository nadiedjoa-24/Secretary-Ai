import calendar
import json
import uuid
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from secretary_ai.config import PLANNING_DIR

WORKING_HOURS = [(time(8), time(12)), (time(14), time(18))]
CALENDAR_FILE = "calendar.json"

# Practitioners of the fictional medical center used by the demo.
DOCTORS = {
    "Dr Claire Morel": "médecin généraliste",
    "Dr Julien Roux": "médecin généraliste",
    "Dr Sarah Benhamou": "chirurgienne-dentiste",
    "Marc Lefort": "kinésithérapeute",
}


def new_appointment_id() -> str:
    return uuid.uuid4().hex[:12]


class Appointment(BaseModel):
    # Stable identifier used in URLs: positions in the agenda change whenever an appointment moves.
    id: str = Field(default_factory=new_appointment_id)
    name: Optional[str]
    surname: Optional[str]
    date: date
    mail: str
    phone: Optional[str] = None
    description: Optional[str] = None
    start_time: time
    doctor: Optional[str] = None


def french_public_holidays(year: int) -> set[date]:
    """Days the office is closed: the eleven public holidays of metropolitan France."""
    # Anonymous Gregorian algorithm for Easter Sunday.
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    g = (8 * b + 13) // 25
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    n = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 19 * n) // 433
    month = (h + n - 7 * m + 90) // 25
    easter = date(year, month, (h + n - 7 * m + 33 * month + 19) % 32)
    fixed = [(1, 1), (5, 1), (5, 8), (7, 14), (8, 15), (11, 1), (11, 11), (12, 25)]
    return {date(year, month, day) for month, day in fixed} | {
        easter + timedelta(days=offset) for offset in (1, 39, 50)  # Easter Monday, Ascension, Whit Monday
    }


def is_working_day(day: date) -> bool:
    return day.weekday() < 5 and day not in french_public_holidays(day.year)


def _naive(moment: datetime) -> datetime:
    return moment.replace(tzinfo=None)


def _sort_key(appointment: Appointment) -> tuple[date, time]:
    return appointment.date, appointment.start_time.replace(tzinfo=None)


class PlannerController:
    """Stores the appointments in a JSON file and computes free time slots."""

    APPOINTMENT_DURATION = timedelta(minutes=30)

    def __init__(self, path: Path = PLANNING_DIR):
        self.path = Path(path)
        self.path.mkdir(parents=True, exist_ok=True)
        self.planning: Dict[date, List[Appointment]] = {}
        self._load()

    @property
    def _file(self) -> Path:
        return self.path / CALENDAR_FILE

    def _load(self) -> None:
        if not self._file.exists():
            self._save()
            return
        for item in json.loads(self._file.read_text(encoding="utf-8")):
            appointment = Appointment.model_validate(item)
            self.planning.setdefault(appointment.date, []).append(appointment)

    def _save(self) -> None:
        # One appointment per line keeps the file compact and its diffs readable.
        lines = [json.dumps(a.model_dump(mode="json", exclude_none=True), ensure_ascii=False)
                 for a in self.all_appointments()]
        self._file.write_text("[\n" + ",\n".join(lines) + "\n]\n", encoding="utf-8")

    def _interval(self, appointment: Appointment) -> tuple[datetime, datetime]:
        start = _naive(datetime.combine(appointment.date, appointment.start_time))
        return start, start + self.APPOINTMENT_DURATION

    def add_appointment(self, appointment: Appointment) -> None:
        """Book an appointment. Two appointments overlap only if they are with the same doctor."""
        appointment.start_time = appointment.start_time.replace(tzinfo=None)
        day_appointments = self.planning.setdefault(appointment.date, [])
        new_start, new_end = self._interval(appointment)
        for existing in self._with_doctor(day_appointments, appointment.doctor):
            start, end = self._interval(existing)
            if new_start < end and start < new_end:
                raise ValueError("Overlapping appointment")
        day_appointments.append(appointment)
        self._save()

    def replace_all(self, appointments: List[Appointment]) -> None:
        """Replace the whole calendar, without overlap checks. Used to generate demo data."""
        self.planning = {}
        for appointment in appointments:
            self.planning.setdefault(appointment.date, []).append(appointment)
        self._save()

    def delete_appointment(self, appointment: Appointment) -> None:
        try:
            self.planning[appointment.date].remove(appointment)
        except (KeyError, ValueError):
            raise ValueError("Appointment not found") from None
        self._save()

    def all_appointments(self) -> List[Appointment]:
        """Every appointment, in chronological order."""
        return sorted((a for day in self.planning.values() for a in day), key=_sort_key)

    def find(self, appointment_id: str) -> Optional[Appointment]:
        return next((a for day in self.planning.values() for a in day if a.id == appointment_id), None)

    def months(self, doctor: Optional[str] = None) -> Dict[date, int]:
        """Number of appointments per month, keyed by the first day of the month, in chronological order.

        With a doctor, only that doctor's appointments are counted.
        """
        counts: Dict[date, int] = {}
        for day, appointments in sorted(self.planning.items()):
            count = sum(doctor in (None, a.doctor) for a in appointments)
            if count:
                month = day.replace(day=1)
                counts[month] = counts.get(month, 0) + count
        return counts

    @staticmethod
    def _with_doctor(appointments: List[Appointment], doctor: Optional[str]) -> List[Appointment]:
        """Appointments that take `doctor`'s time. Without a doctor, every appointment counts."""
        if doctor is None:
            return appointments
        return [a for a in appointments if a.doctor in (doctor, None)]

    def get_day_appointments(self, day: date, doctor: Optional[str] = None) -> List[Appointment]:
        return sorted(self._with_doctor(self.planning.get(day, []), doctor), key=_sort_key)

    def get_day_available_timeslots(self, day: date, doctor: Optional[str] = None) -> List[datetime]:
        """Free 30-minute slots of `doctor` within working hours: working days, 08:00-12:00 and 14:00-18:00."""
        if not is_working_day(day):
            return []
        booked = [self._interval(appointment) for appointment in self.get_day_appointments(day, doctor)]
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

    def get_week_available_timeslots(self, day: date, doctor: Optional[str] = None) -> List[List[datetime]]:
        monday = day - timedelta(days=day.weekday())
        return [self.get_day_available_timeslots(monday + timedelta(days=offset), doctor) for offset in range(7)]

    def get_month_appointments(self, day: date) -> List[List[List[Appointment]]]:
        """Appointments laid out as calendar weeks; days outside the month are empty lists."""
        return [
            [self.get_day_appointments(date(day.year, day.month, d)) if d else [] for d in week]
            for week in calendar.monthcalendar(day.year, day.month)
        ]

    def get_month_available_timeslots(self, day: date, doctor: Optional[str] = None) -> List[List[List[datetime]]]:
        """Free slots laid out as calendar weeks; days outside the month are empty lists."""
        return [
            [self.get_day_available_timeslots(date(day.year, day.month, d), doctor) if d else [] for d in week]
            for week in calendar.monthcalendar(day.year, day.month)
        ]
