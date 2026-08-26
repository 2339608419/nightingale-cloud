from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import PatientRead, TimelineEntryRead
from app.services.patient_service import get_patient, get_patient_entries

router = APIRouter(prefix="/patients", tags=["patients"])
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/{patient_id}", response_model=PatientRead)
def read_patient(patient_id: str, db: DbSession) -> PatientRead:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientRead.model_validate(patient)


@router.get("/{patient_id}/entries", response_model=list[TimelineEntryRead])
def read_patient_entries(patient_id: str, db: DbSession) -> list[TimelineEntryRead]:
    entries = get_patient_entries(db, patient_id)
    if entries is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return [TimelineEntryRead.model_validate(entry) for entry in entries]

