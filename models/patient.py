from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID, uuid4

class Dob(BaseModel):
    day: int
    month: int
    year: int


class PatientInfo(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    surname: str
    forname: str
    age: Optional[int] = None
    dob: Dob 
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
