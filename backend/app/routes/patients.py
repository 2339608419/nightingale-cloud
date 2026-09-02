from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import (
    DataDecayPreviewRead,
    HighlightRead,
    InternalCommentRead,
    PatientRead,
    TimelineEntryCreate,
    TimelineEntryRead,
)
from app.services.authorization_service import (
    AI_ENTRY_TYPES,
    author_role_for_new_entry,
    filter_visible_entries,
    filter_visible_highlights,
    require_internal_comments_access,
    require_patient_access,
)
from app.services.evidence_confidence_service import highlight_read
from app.services.conflict_service import detect_conflicts_for_entry
from app.services.data_decay_service import build_decay_preview
from app.services.patient_service import (
    create_patient_entry,
    get_patient,
)
from app.services.clinic_scope_service import (
    get_entry_in_clinic,
    get_patient_entries_in_clinic,
    get_patient_highlights_in_clinic,
    get_patient_in_clinic,
)

router = APIRouter(prefix="/patients", tags=["patients"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/{patient_id}", response_model=PatientRead)
def read_patient(patient_id: str, db: DbSession, user: Identity) -> PatientRead:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    scoped_patient = get_patient_in_clinic(db, patient_id, user.clinic_id)
    if scoped_patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return PatientRead.model_validate(scoped_patient)


@router.get("/{patient_id}/entries", response_model=list[TimelineEntryRead])
def read_patient_entries(patient_id: str, db: DbSession, user: Identity) -> list[TimelineEntryRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    if get_patient_in_clinic(db, patient_id, user.clinic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    entries = get_patient_entries_in_clinic(db, patient_id, user.clinic_id)
    visible_entries = filter_visible_entries(user, entries)
    return [TimelineEntryRead.model_validate(entry) for entry in visible_entries]


@router.get("/{patient_id}/decay-preview", response_model=list[DataDecayPreviewRead])
def read_decay_preview(
    patient_id: str, db: DbSession, user: Identity
) -> list[DataDecayPreviewRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    if get_patient_in_clinic(db, patient_id, user.clinic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    entries = get_patient_entries_in_clinic(db, patient_id, user.clinic_id)
    highlights = get_patient_highlights_in_clinic(db, patient_id, user.clinic_id)
    visible_entries = filter_visible_entries(user, entries)
    visible_ids = {entry.id for entry in visible_entries}
    visible_highlights = [item for item in filter_visible_highlights(user, highlights) if item.entry_id in visible_ids]
    return build_decay_preview(visible_entries, visible_highlights)


@router.get("/{patient_id}/highlights", response_model=list[HighlightRead])
def read_patient_highlights(patient_id: str, db: DbSession, user: Identity) -> list[HighlightRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    if get_patient_in_clinic(db, patient_id, user.clinic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    highlights = get_patient_highlights_in_clinic(db, patient_id, user.clinic_id)
    visible_highlights = filter_visible_highlights(user, highlights)
    return [
        highlight_read(db, highlight, user.clinic_id)
        for highlight in visible_highlights
    ]


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
    scoped_patient = get_patient_in_clinic(db, patient_id, user.clinic_id)
    if scoped_patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    author_role = author_role_for_new_entry(user, payload.type)
    source_entry = None
    if payload.ai_derived:
        source_entry = get_entry_in_clinic(
            db, payload.source_entry_id or "", user.clinic_id
        )
        if (
            source_entry is None
            or source_entry.patient_id != patient_id
            or source_entry.type not in AI_ENTRY_TYPES
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="AI-derived instruction source must resolve to an AI entry for this patient",
            )
        expected_pointer = f"timeline-entry-{source_entry.id}"
        if payload.provenance_pointer not in {None, expected_pointer}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="AI-derived instruction provenance must identify its source entry",
            )
    entry = create_patient_entry(
        db,
        patient_id=scoped_patient.id,
        author_role=author_role,
        author_id=user.user_id,
        entry_type=payload.type,
        content=payload.content,
        provenance_pointer=(
            f"timeline-entry-{source_entry.id}" if source_entry else payload.provenance_pointer
        ),
        ai_derived=payload.ai_derived,
        source_entry_id=source_entry.id if source_entry else None,
    )
    detect_conflicts_for_entry(db, entry)
    return TimelineEntryRead.model_validate(entry)


@router.get("/{patient_id}/internal-comments", response_model=list[InternalCommentRead])
def read_internal_comments(patient_id: str, db: DbSession, user: Identity) -> list[InternalCommentRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    if get_patient_in_clinic(db, patient_id, user.clinic_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_internal_comments_access(user)
    return []
