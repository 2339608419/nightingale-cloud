from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import ConflictRecord, ConflictStatus
from app.schemas import ConflictRecordRead
from app.services.authorization_service import (
    require_conflict_resolution_access,
    require_conflict_review_access,
    require_patient_access,
)
from app.services.conflict_service import (
    conflict_authority_policy,
    get_patient_conflicts,
    resolve_conflict,
)
from app.services.patient_service import get_entry, get_patient


router = APIRouter(tags=["conflicts"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


def _read(db: Session, conflict: ConflictRecord) -> ConflictRecordRead:
    authoritative_entry = get_entry(db, conflict.authoritative_entry_id)
    conflicting_entry = get_entry(db, conflict.conflicting_entry_id)
    if authoritative_entry is None or conflicting_entry is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict source entry cannot be resolved",
        )
    authority_policy = conflict_authority_policy(authoritative_entry, conflicting_entry)
    return ConflictRecordRead.model_validate(
        {
            **conflict.__dict__,
            "authoritative_provenance_pointer": (
                f"timeline-entry-{conflict.authoritative_entry_id}"
            ),
            "conflicting_provenance_pointer": f"timeline-entry-{conflict.conflicting_entry_id}",
            "authoritative_role": authoritative_entry.author_role,
            "conflicting_role": conflicting_entry.author_role,
            "authority_policy": authority_policy,
            "requires_clinician_review": (
                authority_policy.value == "clinician_review_required"
            ),
        }
    )


@router.get("/patients/{patient_id}/conflicts", response_model=list[ConflictRecordRead])
def read_conflicts(
    patient_id: str,
    db: DbSession,
    user: Identity,
    conflict_status: Annotated[
        ConflictStatus | None, Query(alias="status")
    ] = ConflictStatus.OPEN,
) -> list[ConflictRecordRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_conflict_review_access(user)
    return [_read(db, item) for item in get_patient_conflicts(db, patient_id, conflict_status)]


@router.post("/conflicts/{conflict_id}/resolve", response_model=ConflictRecordRead)
def mark_conflict_resolved(
    conflict_id: str, db: DbSession, user: Identity
) -> ConflictRecordRead:
    conflict = db.get(ConflictRecord, conflict_id)
    if conflict is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conflict not found")
    patient = get_patient(db, conflict.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_conflict_resolution_access(user)
    return _read(db, resolve_conflict(db, conflict, user))
