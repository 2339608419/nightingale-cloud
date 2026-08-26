from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    AuthorRole,
    ClinicalEntityType,
    Highlight,
    HighlightStatus,
    Patient,
    RiskLevel,
    TimelineEntry,
    TimelineEntryType,
)
from app.services.importance_service import calculate_importance_score


SYNTHETIC_PATIENT_ID = "patient-demo-001"
DEMO_REFERENCE_TIME = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)


def _normalize_legacy_demo_data(db: Session) -> None:
    """Bring the one Phase 1 demo-only entry type into the constrained vocabulary."""
    db.execute(
        text(
            "UPDATE timeline_entries SET type = :current_type "
            "WHERE id = :entry_id AND type = :legacy_type"
        ),
        {
            "current_type": TimelineEntryType.STAFF_NOTE.value,
            "entry_id": "entry-demo-003",
            "legacy_type": "patient_insight",
        },
    )


def seed_demo_data(db: Session) -> None:
    _normalize_legacy_demo_data(db)
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
                "home readings were lower than the April baseline. Nurse follow-up remains unresolved."
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
                "Penicillin allergy remains active. Lisinopril increased from 10 mg to 20 mg daily. "
                "Continue recording blood pressure twice daily before the next appointment."
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
            content=(
                "Lab order for renal function and potassium remains pending. Synthetic home "
                "blood-pressure log received and attached to the longitudinal record."
            ),
            provenance_pointer="synthetic://upload/bp-log-2026-08-25",
        ),
    ]
    for entry in entries:
        db.merge(entry)

    entry_timestamps = {entry.id: entry.timestamp for entry in entries}
    highlight_specs = [
        {
            "id": "highlight-demo-allergy",
            "entry_id": "entry-demo-006",
            "source_span": "Penicillin allergy remains active.",
            "text": "Penicillin allergy",
            "risk_level": RiskLevel.HIGH,
            "risk_reason": "Active antibiotic allergy; verify before prescribing.",
            "status": HighlightStatus.ACCEPTED,
            "clinician_confirmed": True,
            "unresolved_action": False,
            "clinical_entity_type": ClinicalEntityType.ALLERGY,
        },
        {
            "id": "highlight-demo-medication",
            "entry_id": "entry-demo-006",
            "source_span": "Lisinopril increased from 10 mg to 20 mg daily.",
            "text": "Lisinopril increased to 20 mg daily",
            "risk_level": RiskLevel.MODERATE,
            "risk_reason": "Recent dose change requires tolerance and blood-pressure review.",
            "status": HighlightStatus.ACCEPTED,
            "clinician_confirmed": True,
            "unresolved_action": False,
            "clinical_entity_type": ClinicalEntityType.MEDICATION,
        },
        {
            "id": "highlight-demo-lab",
            "entry_id": "entry-demo-007",
            "source_span": "Lab order for renal function and potassium remains pending.",
            "text": "Renal function and potassium labs pending",
            "risk_level": RiskLevel.MODERATE,
            "risk_reason": "Pending safety monitoring after an antihypertensive dose change.",
            "status": HighlightStatus.SUGGESTED,
            "clinician_confirmed": False,
            "unresolved_action": True,
            "clinical_entity_type": ClinicalEntityType.LAB,
        },
        {
            "id": "highlight-demo-follow-up",
            "entry_id": "entry-demo-004",
            "source_span": "Nurse follow-up remains unresolved.",
            "text": "Nurse follow-up unresolved",
            "risk_level": RiskLevel.LOW,
            "risk_reason": "Open follow-up action may delay review of home readings.",
            "status": HighlightStatus.SUGGESTED,
            "clinician_confirmed": False,
            "unresolved_action": True,
            "clinical_entity_type": ClinicalEntityType.FOLLOW_UP,
        },
    ]
    for spec in highlight_specs:
        entry_id = spec["entry_id"]
        db.merge(
            Highlight(
                **spec,
                patient_id=SYNTHETIC_PATIENT_ID,
                provenance_pointer=f"timeline-entry-{entry_id}",
                importance_score=calculate_importance_score(
                    source_timestamp=entry_timestamps[entry_id],
                    risk_level=spec["risk_level"],
                    unresolved_action=spec["unresolved_action"],
                    clinical_entity_type=spec["clinical_entity_type"],
                    clinician_confirmed=spec["clinician_confirmed"],
                    as_of=DEMO_REFERENCE_TIME,
                ),
                created_at=DEMO_REFERENCE_TIME,
            )
        )
    db.commit()
