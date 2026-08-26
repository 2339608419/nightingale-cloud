from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models import AuthorRole, Patient, TimelineEntry, TimelineEntryType


SYNTHETIC_PATIENT_ID = "patient-demo-001"


def seed_demo_data(db: Session) -> None:
    patient = Patient(
        id=SYNTHETIC_PATIENT_ID,
        clinic_id="clinic-demo-001",
        name="Maya Chen (Synthetic)",
        date_of_birth=date(1984, 3, 12),
        created_at=datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
    )
    db.merge(patient)
    db.flush()

    entries = [
        TimelineEntry(
            id="entry-demo-001",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.CLINICIAN,
            author_id="clinician-demo-001",
            timestamp=datetime(2025, 4, 15, 9, 30, tzinfo=timezone.utc),
            type=TimelineEntryType.CLINICIAN_NOTE,
            content=(
                "Initial hypertension review. Home readings averaged 146/92 mmHg; "
                "agreed to continue the synthetic monitoring plan and review lifestyle measures."
            ),
            provenance_pointer="synthetic://encounter/2025-04-15#assessment",
        ),
        TimelineEntry(
            id="entry-demo-002",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.CLINICIAN,
            author_id="ai-scribe-doctor-001",
            timestamp=datetime(2025, 4, 15, 10, 5, tzinfo=timezone.utc),
            type=TimelineEntryType.AI_DOCTOR_CONSULT_SUMMARY,
            content=(
                "Consult summary: elevated home blood-pressure readings without chest pain, "
                "dyspnoea, or neurological symptoms. Clinician discussed monitoring and follow-up."
            ),
            provenance_pointer="synthetic://transcript/doctor-2025-04-15#t=42-188",
        ),
        TimelineEntry(
            id="entry-demo-003",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.STAFF,
            author_id="staff-demo-001",
            timestamp=datetime(2026, 2, 6, 8, 45, tzinfo=timezone.utc),
            type=TimelineEntryType.STAFF_NOTE,
            content=(
                "Medication list reconciled by phone. Patient confirmed the synthetic follow-up "
                "appointment and will bring the home blood-pressure log."
            ),
            provenance_pointer="synthetic://telephone/2026-02-06#staff-note",
        ),
        TimelineEntry(
            id="entry-demo-004",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.STAFF,
            author_id="ai-scribe-nurse-001",
            timestamp=datetime(2026, 2, 6, 14, 20, tzinfo=timezone.utc),
            type=TimelineEntryType.AI_NURSE_CONSULT_SUMMARY,
            content=(
                "Nurse call summary: no dizziness or medication concerns reported. Recent synthetic "
                "home readings were lower than the April baseline; follow-up remains planned."
            ),
            provenance_pointer="synthetic://transcript/nurse-2026-02-06#t=18-126",
        ),
        TimelineEntry(
            id="entry-demo-005",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.PATIENT,
            author_id="ai-session-demo-001",
            timestamp=datetime(2026, 8, 20, 19, 10, tzinfo=timezone.utc),
            type=TimelineEntryType.AI_PATIENT_SESSION_SUMMARY,
            content=(
                "Patient session summary: reports improved sleep, regular walking, and no new "
                "symptoms. Asked whether monitoring can be reduced after the next review."
            ),
            provenance_pointer="synthetic://ai-patient-session/2026-08-20#summary",
        ),
        TimelineEntry(
            id="entry-demo-006",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.CLINICIAN,
            author_id="clinician-demo-001",
            timestamp=datetime(2026, 8, 24, 9, 0, tzinfo=timezone.utc),
            type=TimelineEntryType.INSTRUCTION,
            content=(
                "Continue recording blood pressure twice daily for seven days before the next "
                "appointment. Seek urgent care for severe symptoms."
            ),
            provenance_pointer="synthetic://encounter/2026-08-24#instructions",
        ),
        TimelineEntry(
            id="entry-demo-007",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.SYSTEM,
            author_id="nightingale-system",
            timestamp=datetime(2026, 8, 25, 7, 30, tzinfo=timezone.utc),
            type=TimelineEntryType.SYSTEM_EVENT,
            content="Synthetic home blood-pressure log received and attached to the longitudinal record.",
            provenance_pointer="synthetic://upload/bp-log-2026-08-25",
        ),
    ]
    for entry in entries:
        db.merge(entry)
    db.commit()
