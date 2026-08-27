from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuthorRole,
    Patient,
    PatientFacingStatus,
    PatientInstructionApproval,
    TimelineEntry,
    TimelineEntryType,
)
from app.services.revision_service import ensure_initial_version


def get_patient(db: Session, patient_id: str) -> Patient | None:
    return db.get(Patient, patient_id)


def get_patient_entries(db: Session, patient_id: str) -> list[TimelineEntry] | None:
    if db.get(Patient, patient_id) is None:
        return None
    statement = (
        select(TimelineEntry)
        .where(TimelineEntry.patient_id == patient_id)
        .order_by(TimelineEntry.timestamp.desc(), TimelineEntry.id.desc())
    )
    return list(db.scalars(statement))


def get_entry(db: Session, entry_id: str) -> TimelineEntry | None:
    return db.get(TimelineEntry, entry_id)


def create_patient_entry(
    db: Session,
    *,
    patient_id: str,
    author_role: AuthorRole,
    author_id: str,
    entry_type: TimelineEntryType,
    content: str,
    provenance_pointer: str | None,
    ai_derived: bool = False,
    source_entry_id: str | None = None,
) -> TimelineEntry:
    entry = TimelineEntry(
        id=str(uuid4()),
        patient_id=patient_id,
        author_role=author_role,
        author_id=author_id,
        timestamp=datetime.now(timezone.utc),
        type=entry_type,
        content=content,
        provenance_pointer=provenance_pointer,
    )
    db.add(entry)
    db.flush()
    if ai_derived:
        if entry_type != TimelineEntryType.INSTRUCTION or source_entry_id is None:
            raise ValueError("AI-derived content requires an instruction and source entry")
        db.add(
            PatientInstructionApproval(
                entry_id=entry.id,
                patient_facing_status=PatientFacingStatus.DRAFT,
                ai_derived=True,
                source_entry_id=source_entry_id,
                approved_by=None,
                approved_at=None,
            )
        )
        db.flush()
    ensure_initial_version(db, entry)
    db.commit()
    db.refresh(entry)
    return entry
