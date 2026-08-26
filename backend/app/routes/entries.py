from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import TimelineEntryRead, TimelineEntryUpdate
from app.services.authorization_service import require_entry_edit_access, require_patient_access
from app.services.patient_service import get_entry, get_patient, update_entry

router = APIRouter(prefix="/entries", tags=["entries"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


@router.patch("/{entry_id}", response_model=TimelineEntryRead)
def edit_note(
    entry_id: str,
    payload: TimelineEntryUpdate,
    db: DbSession,
    user: Identity,
) -> TimelineEntryRead:
    entry = get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    patient = get_patient(db, entry.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_entry_edit_access(user, entry)
    provenance_pointer = (
        payload.provenance_pointer
        if "provenance_pointer" in payload.model_fields_set
        else entry.provenance_pointer
    )
    updated = update_entry(
        db,
        entry,
        content=payload.content,
        provenance_pointer=provenance_pointer,
    )
    return TimelineEntryRead.model_validate(updated)
