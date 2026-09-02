from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    AuditLog,
    EntryVersion,
    PatientFacingStatus,
    PatientInstructionApproval,
    TimelineEntry,
)
from app.services.audit_service import add_trust_action_audit


class VersionConflictError(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version


def get_versions(db: Session, entry_id: str) -> list[EntryVersion]:
    statement = (
        select(EntryVersion)
        .where(EntryVersion.entry_id == entry_id)
        .order_by(EntryVersion.version_number.desc())
    )
    return list(db.scalars(statement))


def get_audit_logs(db: Session, entry_id: str) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .where(AuditLog.entity_type == "timeline_entry", AuditLog.entity_id == entry_id)
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    )
    return list(db.scalars(statement))


def ensure_initial_version(db: Session, entry: TimelineEntry) -> EntryVersion:
    versions = get_versions(db, entry.id)
    if versions:
        return versions[-1]
    snapshot = EntryVersion(
        id=str(uuid4()),
        entry_id=entry.id,
        version_number=1,
        content=entry.content,
        provenance_pointer=entry.provenance_pointer,
        changed_by=entry.author_id,
        changed_by_role=entry.author_role.value,
        created_at=entry.timestamp,
    )
    db.add(snapshot)
    db.flush()
    return snapshot


def _current_version(db: Session, entry: TimelineEntry) -> int:
    ensure_initial_version(db, entry)
    return get_versions(db, entry.id)[0].version_number


def _record_change(
    db: Session,
    entry: TimelineEntry,
    user: CurrentUser,
    *,
    version_number: int,
    action: str,
    metadata: dict,
) -> None:
    now = datetime.now(timezone.utc)
    db.add(
        EntryVersion(
            id=str(uuid4()),
            entry_id=entry.id,
            version_number=version_number,
            content=entry.content,
            provenance_pointer=entry.provenance_pointer,
            changed_by=user.user_id,
            changed_by_role=user.role.value,
            created_at=now,
        )
    )
    db.add(
        AuditLog(
            id=str(uuid4()),
            actor_id=user.user_id,
            actor_role=user.role.value,
            action=action,
            entity_type="timeline_entry",
            entity_id=entry.id,
            timestamp=now,
            metadata_json=metadata,
        )
    )


def _invalidate_patient_instruction_approval(
    db: Session,
    entry: TimelineEntry,
    user: CurrentUser,
    *,
    new_content: str,
) -> None:
    if new_content == entry.content:
        return
    if entry.type.value == "instruction":
        from app.services.delivery_service import invalidate_deliveries_after_content_change

        invalidate_deliveries_after_content_change(db, entry, user)
    approval = db.get(PatientInstructionApproval, entry.id)
    if approval is None or approval.patient_facing_status != PatientFacingStatus.APPROVED:
        return
    approval.patient_facing_status = PatientFacingStatus.DRAFT
    approval.approved_by = None
    approval.approved_at = None
    approval.approved_version_number = None
    add_trust_action_audit(
        db,
        actor=user,
        action="patient_instruction.approval_invalidated",
        entity_type="timeline_entry",
        entity_id=entry.id,
        from_status=PatientFacingStatus.APPROVED.value,
        to_status=PatientFacingStatus.DRAFT.value,
    )


def update_entry_with_version(
    db: Session,
    entry: TimelineEntry,
    user: CurrentUser,
    *,
    content: str,
    provenance_pointer: str | None,
    expected_version: int,
) -> TimelineEntry:
    current = _current_version(db, entry)
    if expected_version != current:
        db.rollback()
        raise VersionConflictError(current)
    _invalidate_patient_instruction_approval(
        db, entry, user, new_content=content
    )
    entry.content = content
    entry.provenance_pointer = provenance_pointer
    next_version = current + 1
    _record_change(
        db,
        entry,
        user,
        version_number=next_version,
        action="entry.updated",
        metadata={"from_version": current, "to_version": next_version},
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        refreshed = get_versions(db, entry.id)
        raise VersionConflictError(refreshed[0].version_number if refreshed else current) from error
    db.refresh(entry)
    return entry


def revert_entry_to_version(
    db: Session,
    entry: TimelineEntry,
    user: CurrentUser,
    *,
    target_version: int,
    expected_version: int,
) -> TimelineEntry | None:
    current = _current_version(db, entry)
    if expected_version != current:
        db.rollback()
        raise VersionConflictError(current)
    target = db.scalar(
        select(EntryVersion).where(
            EntryVersion.entry_id == entry.id,
            EntryVersion.version_number == target_version,
        )
    )
    if target is None:
        return None
    _invalidate_patient_instruction_approval(
        db, entry, user, new_content=target.content
    )
    entry.content = target.content
    entry.provenance_pointer = target.provenance_pointer
    next_version = current + 1
    _record_change(
        db,
        entry,
        user,
        version_number=next_version,
        action="entry.reverted",
        metadata={
            "from_version": current,
            "to_version": next_version,
            "reverted_to_version": target_version,
        },
    )
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        refreshed = get_versions(db, entry.id)
        raise VersionConflictError(refreshed[0].version_number if refreshed else current) from error
    db.refresh(entry)
    return entry
