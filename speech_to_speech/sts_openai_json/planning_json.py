from pydantic import BaseModel
from typing import List
import json
from pathlib import Path
from datetime import datetime, date, time


class Appoint(BaseModel):
    date: str     # format YYYY-MM-DD
    start: str    # format HH:MM
    available: bool = True
    name: str = ""


class Planning(BaseModel):
    items: List[Appoint]
    year: int
    directory: Path = Path(".")

    @classmethod
    def load(cls, year: int, directory: str = ".") -> "Planning":
        dir_path = Path(directory)
        file_path = dir_path / f"{year}.json"
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        appoints = [Appoint(**item) for item in data.get("items", [])]
        return cls(items=appoints, year=year, directory=dir_path)

    def save_to_file(self) -> None:
        self.directory.mkdir(parents=True, exist_ok=True)
        file_path = self.directory / f"{self.year}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump({"year": self.year, "items": [item.dict() for item in self.items]}, f, indent=4, ensure_ascii=False)

    def find_slot(self, day: int, t: time) -> Appoint | None:
        for item in self.items:
            d = datetime.strptime(item.date, "%Y-%m-%d")
            if d.weekday() == day and item.start == t.strftime("%H:%M") and item.available:
                return item
        return None

    def book_slot(self, appoint: Appoint, name: str) -> None:
        for item in self.items:
            if item.date == appoint.date and item.start == appoint.start:
                item.available = False
                item.name = name
                break
        self.save_to_file()