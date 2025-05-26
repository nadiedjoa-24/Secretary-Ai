# common/data_models/appointment.py

from datetime import date, time, datetime, timedelta
from typing import Optional
from pydantic import BaseModel, Field

class Appointment(BaseModel):
    id: int = Field(..., description="Identifiant unique du RDV")
    patient_id: int = Field(..., description="Référence au Patient.id")
    appointment_date: date = Field(..., description="Date du rendez-vous")   # <— renommé
    start_time: time = Field(..., description="Heure de début")
    duration: int = Field(..., description="Durée en minutes")
    reason: Optional[str] = Field(None, description="Motif")

    @property
    def end_time(self) -> time:
        """Retourne appointment_date + start_time + duration."""
        dt_start = datetime.combine(self.appointment_date, self.start_time)
        dt_end = dt_start + timedelta(minutes=self.duration)
        return dt_end.time()