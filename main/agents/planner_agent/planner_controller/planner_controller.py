import os, sys
from typing import List, Optional, Literal
from pydantic import BaseModel
from datetime import datetime





class rdv(BaseModel):
    """
    Data model for an appointment.
    """
    name: Optional[str] 
    surname: Optional[str]
    date = datetime
    mail: str
    phone: Optional[str] = None
    description: str = None
 
