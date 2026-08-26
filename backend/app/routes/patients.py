from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import (
    HighlightRead,
    InternalCommentRead,
    PatientRead,
    TimelineEntryCreate,
    TimelineEntryRead,
)
from app.services.authorization_service import (
    author_role_for_new_entry,
    filter_visible_entries,
    filter_visible_highlights,
    require_internal_comments_access,
    require_patient_access,
)
from app.services.highlight_service import get_patient_highlights
from app.services.patient_service import create_patient_entry, get_patient, get_patient_entries

router = APIRouter(prefix="/patients", tags=["patients"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/{patient_id}", response_model=PatientRead)
def read_patient(patient_id: str, db: DbSession, user: Identity) -> PatientRead:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    return PatientRead.model_validate(patient)


@router.get("/{patient_id}/entries", response_model=list[TimelineEntryRead])
def read_patient_entries(patient_id: str, db: DbSession, user: Identity) -> list[TimelineEntryRead]:
    entries = get_patient_entries(db, patient_id)
    if entries is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    visible_entries = filter_visible_entries(user, entries)
    return [TimelineEntryRead.model_validate(entry) for entry in visible_entries]


@router.get("/{patient_id}/highlights", response_model=list[HighlightRead])
def read_patient_highlights(patient_id: str, db: DbSession, user: Identity) -> list[HighlightRead]:
    highlights = get_patient_highlights(db, patient_id)
    if highlights is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    visible_highlights = filter_visible_highlights(user, highlights)
    return [HighlightRead.model_validate(highlight) for highlight in visible_highlights]


@router.post("/{patient_id}/entries", response_model=TimelineEntryRead, status_code=201)
def create_note(
    patient_id: str,
    payload: TimelineEntryCreate,
    db: DbSession,
    user: Identity,
) -> TimelineEntryRead:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    author_role = author_role_for_new_entry(user, payload.type)
    entry = create_patient_entry(
        db,
        patient_id=patient_id,
        author_role=author_role,
        author_id=user.user_id,
        entry_type=payload.type,
        content=payload.content,
        provenance_pointer=payload.provenance_pointer,
    )
    return TimelineEntryRead.model_validate(entry)


@router.get("/{patient_id}/internal-comments", response_model=list[InternalCommentRead])
def read_internal_comments(patient_id: str, db: DbSession, user: Identity) -> list[InternalCommentRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_internal_comments_access(user)
    return []
