from datetime import date
from typing import Optional
from pydantic import BaseModel, Field

class Patient(BaseModel):
    id: int = Field(..., description="Identifiant unique du patient")
    first_name: str = Field(..., description="Prénom du patient")
    last_name: str = Field(..., description="Nom de famille du patient")
    dob: date = Field(..., description="Date de naissance")
    gender: Optional[str] = Field(None, description="Genre (ex. 'M', 'F', 'Autre')")
    phone: Optional[str] = Field(None, description="Numéro de téléphone")
    email: Optional[str] = Field(None, description="Adresse e-mail")