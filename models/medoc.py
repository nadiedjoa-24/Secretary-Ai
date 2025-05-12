from typing import List, Dict
from pydantic import BaseModel 

class Medication(BaseModel):
    name: str
    quantity: str
    treatment_duration: str
    posology: str

