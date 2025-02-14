import json
from datetime import datetime, timedelta
from typing import Literal
from pydantic import BaseModel, field_validator
import re

class Appointment(BaseModel):
    last_name: str
    first_name: str 
    date_of_birth: str 
    month: int
    day: int 
    time: str 
    duration: str
    doctor: Literal["John", "Smith", "Robert"] 

    def are_fields_filled(self) -> bool:
        if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', self.time):
            return False
        if not re.match(r'^[0-9][0-9]$', self.duration):
            return False
        # Vérifie si tous les champs nécessaires sont remplis
        else:
            return all(
                [self.last_name, self.first_name, self.date_of_birth, 
                self.month, self.day, self.time, self.doctor, self.duration]
            )
    
    # @field_validator('time')
    # def validate_time_format(cls, value):
    #     # Vérification du format HH:MM
    #     if not re.match(r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$', value):
    #         raise ValueError("Invalid time format. Expected HH:MM (e.g., '08:30', '13:45').")
    #     return value

    

class Planning:

    def __init__(self, year: int):
        self.year = year
        self.planning = None
        self.rplanning = None 
        self._path = str(year) + "_planning.json"
        self._rpath = str(year) + "_rplanning.json"
        self.load_from_file()



    def save_to_file(self):
        L = [(self._path, 'planning'), (self._rpath, 'rplanning')]
        for file_path, planning_attr in L:
            planning = getattr(self, planning_attr)
            with open(file_path, 'w') as f:
                json.dump(planning, f)


    def load_from_file(self):
        L = [(self._path, 'planning'), (self._rpath, 'rplanning')]
        for file_path, planning_attr in L:
            with open(file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    self.initialize_full_year()
                else:
                    setattr(self, planning_attr, json.loads(content))
                    print('success')


    def initialize_full_year(self):
        self.planning = {}
        self.rplanning = {}
        for month in range(1, 13):
            days_in_month = (datetime(self.year, month % 12 + 1, 1) - timedelta(days=1)).day
            self.planning[str(month)] = {}
            self.rplanning[str(month)] = {}
            for day in range(1, days_in_month + 1):
                self.planning[str(month)][str(day)] = {"John": [], "Smith": [], "Robert": []}
                self.rplanning[str(month)][str(day)] = {"John": [["08:00", "12:00"], ["13:30", "18:00"]], "Smith": [["08:00", "12:00"], ["13:30", "18:00"]], "Robert": [["08:00", "12:00"], ["13:30", "18:00"]]}
        self.save_to_file()


    def is_available(self, appointment: Appointment):
        month = str(appointment.month)
        day = str(appointment.day)
        doctor = appointment.doctor
        time_start = appointment.time
        if month in self.planning and day in self.planning[month]:
            for existing_appointment in self.planning[month][day][doctor]:
                if existing_appointment['time'] == time_start:
                    return True
        return False
    

    def add(self, appointment: Appointment):
        month = str(appointment.month)
        day = str(appointment.day)
        doctor = appointment.doctor
        beginning = datetime.strptime(appointment.time, "%H:%M").time()
        ending = (datetime.combine(datetime.today(), beginning) + timedelta(minutes=int(appointment.duration))).time()

        if not self.is_available(appointment):
            self.planning[month][day][doctor].append(appointment.model_dump())
            L = self.rplanning[month][day][doctor]
            A = L.copy()
            for i in range(len(L)):
                l = L[i]
                # print(l)
                begin = datetime.strptime(l[0], "%H:%M").time()
                end = datetime.strptime(l[1], "%H:%M").time()
                if begin < beginning and end > ending:
                    print(1)
                    A.remove(l)
                    A = A[:i] + [[begin.strftime("%H:%M"), beginning.strftime("%H:%M")],[ending.strftime("%H:%M"), end.strftime("%H:%M")]] + A[i:]
                elif begin==beginning and end > ending:
                    print(2)
                    A.remove(l)
                    A = A[:i] + [[ending.strftime("%H:%M"), end.strftime("%H:%M")]] + A[i:]
                elif begin<beginning and end==ending:
                    print(3)
                    A.remove(l)
                    A = A[:i] + [[begin.strftime("%H:%M"), beginning.strftime("%H:%M")]] + A[i:]
                elif begin==beginning and end==ending:
                    print(4)
                    A.remove(l)
                    A = A[:i] + A[i:]
                print(A)

                self.rplanning[month][day][doctor] = A
            print(f"Rendez-vous ajouté : {appointment}")
            self.save_to_file()
        else:
            print("Le rendez-vous existe déjà dans le planning.")


    def delete(self, appointment: Appointment):
        month = str(appointment.month)
        day = str(appointment.day)
        doctor = appointment.doctor
        time_start = appointment.time

        if month in self.planning and day in self.planning[month]:
            for existing_appointment in self.planning[month][day][doctor]:
                if existing_appointment['time'] == time_start:
                    self.planning[month][day][doctor].remove(existing_appointment)
                    print(f"Rendez-vous supprimé : {existing_appointment}")
                    self.save_to_file()
                    return
        print("Le rendez-vous n'a pas été trouvé dans le planning.")

                                



                    






if __name__ == "__main__":
    # Exemple de planning chargé
    pla = Planning(2025)

    # Exemple d'utilisation de l'objet Appointment
    appointment_example1 = Appointment(
        last_name="Dupont",
        first_name="Alice",
        date_of_birth="1999-05-28",
        month=2,
        day=15,
        time="09:00",
        duration="30",
        doctor="Smith"
    )

    appointment_example2 = Appointment(
        last_name="Dupont",
        first_name="Alice",
        date_of_birth="1999-05-28",
        month=2,
        day=15,
        time="09:30",
        duration="30",
        doctor="Smith"
    )

    appointment_example3 = Appointment(
        last_name="Dupont",
        first_name="Alice",
        date_of_birth="1999-05-28",
        month=2,
        day=15,
        time="10:30",
        duration="30",
        doctor="Smith"
    )

    appointment_example4 = Appointment(
        last_name="Dupont",
        first_name="Alice",
        date_of_birth="1999-05-28",
        month=2,
        day=15,
        time="11:30",
        duration="30",
        doctor="Smith"
    )

    appointment_example5 = Appointment(
        last_name="Dupont",
        first_name="Alice",
        date_of_birth="1999-05-28",
        month=2,
        day=15,
        time="13:30",
        duration="60",
        doctor="Smith"
    )

    pla.add(appointment_example1)
    pla.add(appointment_example2)
    pla.add(appointment_example3)
    pla.add(appointment_example4)
    pla.add(appointment_example5)

    print(pla.rplanning["2"]["15"]["Smith"])
    print(pla.rplanning["2"]["15"]["Robert"])

