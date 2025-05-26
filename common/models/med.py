from pydantic import BaseModel, Field
from typing import Optional


class Posologie(BaseModel):
    dose: str = Field(..., description="Dose prescrite (ex. '500 mg')")
    frequency: str = Field(..., description="Fréquence d'administration (ex. '2 fois par jour')")
    duration: str = Field(..., description="Durée du traitement (ex. '7 jours')")
    route: Optional[str] = Field(None, description="Voie d'administration (ex. 'orale')")

class Medication(BaseModel):
    id: int = Field(..., description="Identifiant unique du médicament")
    name: str = Field(..., description="Nom commercial ou générique")
    posologie: Posologie = Field(..., description="Posologie détaillée du médicament")