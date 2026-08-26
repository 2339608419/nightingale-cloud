from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class PatientRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinic_id: str
    name: str
    date_of_birth: date
    created_at: datetime

