from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import Patient, TimelineEntry


SYNTHETIC_PATIENT_ID = "patient-demo-001"


def seed_demo_data(db: Session) -> None:
    if db.get(Patient, SYNTHETIC_PATIENT_ID) is not None:
        return

    patient = Patient(
        id=SYNTHETIC_PATIENT_ID,
        clinic_id="clinic-demo-001",
        name="Maya Chen (Synthetic)",
        date_of_birth=date(1984, 3, 12),
        created_at=datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
    )
    patient.entries = [
        TimelineEntry(
            id="entry-demo-001",
            author_role="clinician",
            author_id="clinician-demo-001",
            timestamp=datetime(2026, 8, 21, 9, 30, tzinfo=timezone.utc),
            type="clinician_note",
            content="Reviewed synthetic blood-pressure log; continue home monitoring.",
            provenance_pointer="synthetic://visit/2026-08-21#assessment",
        ),
        TimelineEntry(
            id="entry-demo-002",
            author_role="staff",
            author_id="staff-demo-001",
            timestamp=datetime(2026, 8, 23, 3, 15, tzinfo=timezone.utc),
            type="staff_note",
            content="Synthetic follow-up appointment confirmed for next week.",
            provenance_pointer="synthetic://scheduling/appointment-001",
        ),
        TimelineEntry(
            id="entry-demo-003",
            author_role="patient",
            author_id=SYNTHETIC_PATIENT_ID,
            timestamp=datetime(2026, 8, 25, 11, 0, tzinfo=timezone.utc),
            type="patient_insight",
            content="Reports improved sleep and no new symptoms in this synthetic record.",
            provenance_pointer="synthetic://patient-message/message-001",
        ),
    ]
    db.add(patient)
    db.commit()

