# common/data_models/planning.py

from pydantic import BaseModel, Field
from typing import List
import json
from pathlib import Path
from datetime import date, timedelta

from common.data_models.appointment import Appointment
from common.data_models.work_hours import WorkHours, TimeSlot

class Planning(BaseModel):
    items: List[Appointment] = Field(
        default_factory=list,
        description="Tous les rendez-vous de l'année"
    )
    year: int = Field(..., description="Année de la planification")
    directory: Path = Field(
        default=Path("."),
        description="Répertoire où sont lus/écrits les JSON"
    )

    @classmethod
    def load(cls, year: int, directory: str = ".") -> "Planning":
        dir_path = Path(directory)
        file_path = dir_path / f"{year}.json"
        if not file_path.exists():
            return cls(items=[], year=year, directory=dir_path)

        data = json.loads(file_path.read_text(encoding="utf-8"))
        raw = data.get("items", [])
        items = [Appointment.parse_obj(d) for d in raw]
        return cls(items=items, year=year, directory=dir_path)

    def save_to_file(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / f"{self.year}.json"
        file_path.write_text(self.model_dump_json(indent=4, ensure_ascii=False),
                             encoding="utf-8")

    def add_appoint(self, appoint: Appointment) -> None:
        self.items.append(appoint)
        self.save_to_file()

    def delete_appoint(self, appoint: Appointment) -> None:
        self.items = [a for a in self.items if a.id != appoint.id]
        self.save_to_file()

    def get_day_appoints(self, day: date) -> List[Appointment]:
        return [a for a in self.items if a.appointment_date == day]

    def get_week_appoints(self, day: date) -> List[List[Appointment]]:
        start = day - timedelta(days=day.weekday())
        return [
            self.get_day_appoints(start + timedelta(days=i))
            for i in range(7)
        ]

    def get_month_appoints(self, day: date) -> List[List[List[Appointment]]]:
        """
        Retourne un calendrier mensuel complet :
        - liste de semaines (toujours 7 jours),
        - chaque jour est la liste des RDV si dans le mois, sinon [].
        """
        first_day = day.replace(day=1)
        # calcul du premier jour de la semaine contenant le 1er du mois (lundi)
        start_cal = first_day - timedelta(days=first_day.weekday())

        # calcul du dernier jour du mois
        if first_day.month == 12:
            next_month = first_day.replace(year=first_day.year + 1, month=1, day=1)
        else:
            next_month = first_day.replace(month=first_day.month + 1, day=1)
        last_day = next_month - timedelta(days=1)
        # calcul du dernier jour de la semaine contenant le dernier jour du mois (dimanche)
        end_cal = last_day + timedelta(days=(6 - last_day.weekday()))

        weeks: List[List[List[Appointment]]] = []
        week: List[List[Appointment]] = []
        current = start_cal

        while current <= end_cal:
            if current.month == day.month:
                week.append(self.get_day_appoints(current))
            else:
                week.append([])  # hors du mois => pas de RDV
            # chaque fois qu'on atteint un dimanche, on clôt la semaine
            if current.weekday() == 6:
                weeks.append(week)
                week = []
            current += timedelta(days=1)

        return weeks
    
    def get_day_free_slots(self, day: date, work_hours: WorkHours) -> List[TimeSlot]:
        wd = work_hours.get_day(day)
        if wd is None:
            return []

        free: List[TimeSlot] = [slot.copy() for slot in wd.slots]
        for a in self.get_day_appoints(day):
            start = a.start_time
            end   = a.end_time
            new_free: List[TimeSlot] = []
            for slot in free:
                if end <= slot.start or start >= slot.end:
                    new_free.append(slot)
                else:
                    if start > slot.start:
                        new_free.append(TimeSlot(start=slot.start, end=start))
                    if end < slot.end:
                        new_free.append(TimeSlot(start=end,       end=slot.end))
            free = new_free

        return free

    def get_week_free_slots(self, day: date, work_hours: WorkHours) -> List[List[TimeSlot]]:
        start = day - timedelta(days=day.weekday())
        return [
            self.get_day_free_slots(start + timedelta(days=i), work_hours)
            for i in range(7)
        ]

   # common/data_models/planning.py

    def get_month_free_slots(
        self, day: date, work_hours: WorkHours
    ) -> List[List[List[TimeSlot]]]:
        """
        Calendrier mensuel des créneaux libres :
        - chaque sous-liste est une semaine complète (7 jours),
        - pour les jours hors du mois, on renvoie [].
        """
        # 1) Premier et dernier jour du mois
        first_day = day.replace(day=1)
        if first_day.month == 12:
            next_month = first_day.replace(year=first_day.year + 1, month=1, day=1)
        else:
            next_month = first_day.replace(month=first_day.month + 1, day=1)
        last_day = next_month - timedelta(days=1)

        # 2) Étendue du calendrier : du lundi de la semaine du 1er
        #    au dimanche de la semaine du dernier jour
        start_cal = first_day - timedelta(days=first_day.weekday())
        end_cal   = last_day + timedelta(days=(6 - last_day.weekday()))

        # 3) Itération jour par jour
        weeks: List[List[List[TimeSlot]]] = []
        week: List[List[TimeSlot]] = []
        current = start_cal

        while current <= end_cal:
            if current.month == day.month:
                slots = self.get_day_free_slots(current, work_hours)
            else:
                slots = []  # hors du mois
            week.append(slots)

            # dès qu'on atteint dimanche, on clôt la semaine
            if current.weekday() == 6:
                weeks.append(week)
                week = []

            current += timedelta(days=1)

        return weeks