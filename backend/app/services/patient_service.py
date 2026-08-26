from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Patient, TimelineEntry


def get_patient(db: Session, patient_id: str) -> Patient | None:
    return db.get(Patient, patient_id)


def get_patient_entries(db: Session, patient_id: str) -> list[TimelineEntry] | None:
    if db.get(Patient, patient_id) is None:
        return None
    statement = (
        select(TimelineEntry)
        .where(TimelineEntry.patient_id == patient_id)
        .order_by(TimelineEntry.timestamp.desc())
    )
    return list(db.scalars(statement))

