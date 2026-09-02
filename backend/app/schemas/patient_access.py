from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class PhoneAccessRequest(BaseModel):
    phone: str = Field(min_length=8, max_length=32)
    clinic_id: str = Field(min_length=1, max_length=36)
    synthetic: Literal[True]


class PhoneAccessChallengeRead(BaseModel):
    accepted: Literal[True] = True
    mode: Literal["synthetic_local_mock"] = "synthetic_local_mock"
    challenge_id: str
    masked_destination: str
    expires_at: datetime
    mock_access_token: str
    warning: str = "If this synthetic number is available, mock verification was initiated."


class PhoneAccessExchange(BaseModel):
    access_token: str = Field(min_length=32, max_length=256)


class PatientSessionRead(BaseModel):
    mode: Literal["synthetic_local_mock"] = "synthetic_local_mock"
    patient_id: str
    session_token: str
    expires_at: datetime
