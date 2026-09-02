from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import PatientFacingStatus, TimelineEntry
from app.schemas import (
    AuditLogRead,
    EntryVersionRead,
    RevertRequest,
    TimelineEntryRead,
    TimelineEntryUpdate,
)
from app.services.authorization_service import (
    require_entry_collaboration_access,
    require_entry_edit_access,
    require_patient_access,
    require_patient_instruction_approval_access,
)
from app.services.patient_service import get_entry, get_patient
from app.services.clinic_scope_service import (
    get_entry_audit_logs_in_clinic,
    get_entry_in_clinic,
    get_entry_versions_in_clinic,
)
from app.services.patient_instruction_service import set_patient_instruction_status
from app.services.conflict_service import detect_conflicts_for_entry
from app.services.revision_service import (
    VersionConflictError,
    revert_entry_to_version,
    update_entry_with_version,
)

router = APIRouter(prefix="/entries", tags=["entries"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


def _version_conflict_detail(
    db: Session,
    *,
    entry_id: str,
    clinic_id: str,
    expected_version: int,
    current_version: int,
) -> dict:
    current = get_entry_in_clinic(db, entry_id, clinic_id)
    if current is None:
        return {
            "error_code": "entry_version_conflict",
            "entry_id": entry_id,
            "expected_version": expected_version,
            "current_version": current_version,
        }
    return {
        "error_code": "entry_version_conflict",
        "entry_id": entry_id,
        "expected_version": expected_version,
        "current_version": current_version,
        "current_content": current.content,
        "current_provenance_pointer": current.provenance_pointer,
    }


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
    scoped_entry = get_entry_in_clinic(db, entry_id, user.clinic_id)
    if scoped_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    require_entry_edit_access(user, scoped_entry)
    provenance_pointer = (
        payload.provenance_pointer
        if "provenance_pointer" in payload.model_fields_set
        else scoped_entry.provenance_pointer
    )
    try:
        updated = update_entry_with_version(
            db,
            scoped_entry,
            user,
            content=payload.content,
            provenance_pointer=provenance_pointer,
            expected_version=payload.expected_version,
        )
    except VersionConflictError as conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_version_conflict_detail(
                db,
                entry_id=entry_id,
                clinic_id=user.clinic_id,
                expected_version=payload.expected_version,
                current_version=conflict.current_version,
            ),
        ) from conflict
    detect_conflicts_for_entry(db, updated)
    return TimelineEntryRead.model_validate(updated)


def _decide_patient_instruction(
    entry_id: str,
    decision: PatientFacingStatus,
    db: Session,
    user: CurrentUser,
) -> TimelineEntryRead:
    entry = get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    patient = get_patient(db, entry.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    scoped_entry = get_entry_in_clinic(db, entry_id, user.clinic_id)
    if scoped_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    require_patient_instruction_approval_access(user)
    updated = set_patient_instruction_status(
        db,
        entry=scoped_entry,
        new_status=decision,
        actor=user,
        clinic_id=user.clinic_id,
    )
    return TimelineEntryRead.model_validate(updated)


@router.post("/{entry_id}/patient-facing/approve", response_model=TimelineEntryRead)
def approve_patient_instruction(
    entry_id: str, db: DbSession, user: Identity
) -> TimelineEntryRead:
    return _decide_patient_instruction(
        entry_id, PatientFacingStatus.APPROVED, db, user
    )


@router.post("/{entry_id}/patient-facing/reject", response_model=TimelineEntryRead)
def reject_patient_instruction(
    entry_id: str, db: DbSession, user: Identity
) -> TimelineEntryRead:
    return _decide_patient_instruction(
        entry_id, PatientFacingStatus.REJECTED, db, user
    )


def _authorized_entry(entry_id: str, db: Session, user: CurrentUser) -> TimelineEntry:
    entry = get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    patient = get_patient(db, entry.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    scoped_entry = get_entry_in_clinic(db, entry_id, user.clinic_id)
    if scoped_entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    require_entry_collaboration_access(user, scoped_entry)
    return scoped_entry


@router.get("/{entry_id}/versions", response_model=list[EntryVersionRead])
def read_versions(entry_id: str, db: DbSession, user: Identity) -> list[EntryVersionRead]:
    _authorized_entry(entry_id, db, user)
    return [
        EntryVersionRead.model_validate(item)
        for item in get_entry_versions_in_clinic(db, entry_id, user.clinic_id)
    ]


@router.get("/{entry_id}/audit", response_model=list[AuditLogRead])
def read_audit(entry_id: str, db: DbSession, user: Identity) -> list[AuditLogRead]:
    _authorized_entry(entry_id, db, user)
    return [
        AuditLogRead.model_validate(item)
        for item in get_entry_audit_logs_in_clinic(db, entry_id, user.clinic_id)
    ]


@router.post("/{entry_id}/revert/{version_number}", response_model=TimelineEntryRead)
def revert_note(
    entry_id: str,
    version_number: int,
    payload: RevertRequest,
    db: DbSession,
    user: Identity,
) -> TimelineEntryRead:
    entry = _authorized_entry(entry_id, db, user)
    require_entry_edit_access(user, entry)
    try:
        reverted = revert_entry_to_version(
            db,
            entry,
            user,
            target_version=version_number,
            expected_version=payload.expected_version,
        )
    except VersionConflictError as conflict:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_version_conflict_detail(
                db,
                entry_id=entry_id,
                clinic_id=user.clinic_id,
                expected_version=payload.expected_version,
                current_version=conflict.current_version,
            ),
        ) from conflict
    if reverted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Version not found")
    return TimelineEntryRead.model_validate(reverted)
