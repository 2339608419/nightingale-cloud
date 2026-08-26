from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuthorRole, Patient, TimelineEntry, TimelineEntryType


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
    db.commit()
    db.refresh(entry)
    return entry


def update_entry(
    db: Session,
    entry: TimelineEntry,
    *,
    content: str,
    provenance_pointer: str | None,
) -> TimelineEntry:
    entry.content = content
    entry.provenance_pointer = provenance_pointer
    db.commit()
    db.refresh(entry)
    return entry
