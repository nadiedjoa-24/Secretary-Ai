from pydantic import BaseModel, field_validator
from typing import List, Optional
from datetime import datetime, date, time
from uuid import UUID



class Appoint(BaseModel):
    date: date
    time: time
    patient_id: UUID

    @field_validator('date', pre=True)
    def parse_date(cls, v):
        if isinstance(v, str):
            dt = datetime.strptime(v, '%m/%d')
            return dt.replace(year=datetime.now().year).date()
        return v

    @field_validator('time', pre=True)
    def parse_time(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v, '%H:%M').time()
        return v