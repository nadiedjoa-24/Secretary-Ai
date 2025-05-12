from pydantic import BaseModel
from typing import List, Optional
import json
from pathlib import Path
from models.rdv import Appoint
from datetime import datetime



class Planning(BaseModel):
    items: List[dict] = []
    year: int
    directory: Path = Path(".")

    @classmethod
    def load(cls, year: int, directory: str = ".") -> "Planning":
        dir_path = Path(directory)
        file_path = dir_path / f"{year}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(items=data.get("items", []), year=year, directory=dir_path)

    def save_to_file(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / f"{self.year}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(self.model_dump_json(indent=4, ensure_ascii=False))


    def add_appoint(appoint: Appoint) -> None:
        """
        Add an appointment tot the planning and save the planning.
        """
    def delete_appoint(appoint: Appoint) -> None:
        """
        Delete an appointment from de planning and save the planning
        """

    def get_day_appoints(self, date: datetime.date) -> List[Appoint]:
        """
        Return the list of appointments for the day of a given date.
        """
        return [appoint for appoint in self.items if appoint.date.date() == date]

    def get_week_appoints(self, date: datetime.date) -> List[List[Appoint]]:
        """
        Return a list of lists of appointments for each day in the week containing the given date.
        """
        start_of_week = date - datetime.timedelta(days=date.weekday())
        return [[appoint for appoint in self.items if appoint.date.date() == (start_of_week + datetime.timedelta(days=i))] for i in range(7)]

    def get_month_appoints(self, date: datetime.date) -> List[List[List[Appoint]]]:
        """
        Return a list of lists (weeks) of lists (days) of appointments for each day in the month containing the given date.
        """
        first_day = date.replace(day=1)
        last_day = (date.replace(day=1) + datetime.timedelta(days=32)).replace(day=1) - datetime.timedelta(days=1)
        days_in_month = (last_day - first_day).days + 1
        weeks = []

        current_week = []
        for i in range(days_in_month):
            current_date = first_day + datetime.timedelta(days=i)
            if current_date.weekday() == 0 and current_week:
                weeks.append(current_week)
                current_week = []

            day_appointments = [appoint for appoint in self.items if appoint.date.date() == current_date]
            current_week.append(day_appointments)

        if current_week:
            weeks.append(current_week)

        return weeks


# Test

# if __name__ == "__main__":
    