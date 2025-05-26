# common/data_models/work_hours.py

from pydantic import BaseModel, Field, root_validator
from typing import List, Optional
from pathlib import Path
import json
from datetime import date, time, timedelta



class TimeSlot(BaseModel):
    start: time = Field(..., description="Heure de début du créneau")
    end:   time = Field(..., description="Heure de fin du créneau")

    def __str__(self) -> str:
        # Format "HH:MM-HH:MM"
        return f"{self.start.strftime('%H:%M')}-{self.end.strftime('%H:%M')}"

    __repr__ = __str__


class WorkDay(BaseModel):
    day: date              = Field(..., description="Date du jour de travail")
    slots: List[TimeSlot]  = Field(..., description="Liste des créneaux horaires")


class WorkHours(BaseModel):
    doctor_id: int            = Field(..., description="Identifiant du médecin")
    year:      int            = Field(..., description="Année de référence")
    items:     List[WorkDay]  = Field(default_factory=list, description="Jours et créneaux")
    directory: Path           = Field(default=Path("."), description="Répertoire de stockage JSON")

    @root_validator(pre=True)
    def set_default_items(cls, values):
        # Génère par défaut lun–ven 8-12 / 14-18 si pas d'items passés
        if not values.get("items"):
            y = values["year"]
            default_slots = [
                TimeSlot(start=time(8,0), end=time(12,0)),
                TimeSlot(start=time(14,0), end=time(18,0)),
            ]
            items: List[WorkDay] = []
            current = date(y,1,1)
            end_date = date(y,12,31)
            while current <= end_date:
                if current.weekday() < 5:  # 0=lundi … 4=vendredi
                    items.append(WorkDay(day=current, slots=default_slots))
                current += timedelta(days=1)
            values["items"] = items
        return values

    @classmethod
    def load(cls, doctor_id: int, year: int, directory: str = ".") -> "WorkHours":
        dir_path  = Path(directory)
        file_path = dir_path / f"{doctor_id}_{year}_work_hours.json"
        if not file_path.exists():
            # renvoie un objet avec la racine default_generator du root_validator
            return cls(doctor_id=doctor_id, year=year, directory=dir_path)

        data = json.loads(file_path.read_text(encoding="utf-8"))
        raw  = data.get("items", [])
        items = [WorkDay.parse_obj(d) for d in raw]
        return cls(doctor_id=doctor_id, year=year, items=items, directory=dir_path)

    def save_to_file(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / f"{self.doctor_id}_{self.year}_work_hours.json"
        file_path.write_text(self.model_dump_json(indent=4, ensure_ascii=False), encoding="utf-8")

    def set_workday(self, workday: WorkDay) -> None:
        """
        Ajoute ou met à jour la plage horaire pour workday.day, puis sauvegarde.
        """
        self.items = [wd for wd in self.items if wd.day != workday.day]
        self.items.append(workday)
        self.items.sort(key=lambda wd: wd.day)
        self.save_to_file()

    def delete_workday(self, day: date) -> None:
        """
        Supprime les WorkDay pour la date donnée, puis sauvegarde.
        """
        self.items = [wd for wd in self.items if wd.day != day]
        self.save_to_file()

    def get_day(self, day: date) -> Optional[WorkDay]:
        """
        Renvoie les créneaux du jour, ou None s’ils n’existent pas.
        """
        for wd in self.items:
            if wd.day == day:
                return wd
        return None

    def get_week(self, day: date) -> List[Optional[WorkDay]]:
        """
        Renvoie la liste de 7 WorkDay (ou None) pour la semaine contenant `day`.
        """
        start = day - timedelta(days=day.weekday())
        return [self.get_day(start + timedelta(days=i)) for i in range(7)]

    def get_month(self, day: date) -> List[List[Optional[WorkDay]]]:
        """
        Calendrier mensuel : liste de semaines → liste de WorkDay (ou None).
        """
        first = day.replace(day=1)
        if first.month == 12:
            next_month = first.replace(year=first.year + 1, month=1, day=1)
        else:
            next_month = first.replace(month=first.month + 1, day=1)
        last = next_month - timedelta(days=1)

        weeks: List[List[Optional[WorkDay]]] = []
        current_week: List[Optional[WorkDay]] = []

        for offset in range((last - first).days + 1):
            current_day = first + timedelta(days=offset)
            if current_day.weekday() == 0 and current_week:
                weeks.append(current_week)
                current_week = []
            current_week.append(self.get_day(current_day))

        if current_week:
            weeks.append(current_week)
        return weeks