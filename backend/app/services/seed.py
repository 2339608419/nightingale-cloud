from datetime import date, datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models import (
    AuthorRole,
    ClinicalEntityType,
    CollaborationRole,
    Comment,
    Highlight,
    HighlightStatus,
    Patient,
    RiskLevel,
    TimelineEntry,
    TimelineEntryType,
    TaskAssignment,
    TaskStatus,
    EntryVersion,
)
from app.services.importance_service import evaluate_importance


SYNTHETIC_PATIENT_ID = "patient-demo-001"
OTHER_CLINIC_PATIENT_ID = "patient-demo-other-clinic"
DEMO_REFERENCE_TIME = datetime(2026, 8, 26, 8, 0, tzinfo=timezone.utc)


def _normalize_legacy_demo_data(db: Session) -> None:
    """Keep fixed synthetic seed rows compatible with earlier prototype phases."""
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
    db.execute(
        text(
            "UPDATE timeline_entries SET author_role = :system_role "
            "WHERE id IN (:doctor_id, :nurse_id, :patient_session_id)"
        ),
        {
            "system_role": AuthorRole.SYSTEM.value,
            "doctor_id": "entry-demo-002",
            "nurse_id": "entry-demo-004",
            "patient_session_id": "entry-demo-005",
        },
    )
    db.execute(
        text(
            "UPDATE entry_versions SET changed_by_role = :system_role "
            "WHERE entry_id IN (:doctor_id, :nurse_id, :patient_session_id) "
            "AND version_number = 1"
        ),
        {
            "system_role": AuthorRole.SYSTEM.value,
            "doctor_id": "entry-demo-002",
            "nurse_id": "entry-demo-004",
            "patient_session_id": "entry-demo-005",
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
    db.merge(
        Patient(
            id=OTHER_CLINIC_PATIENT_ID,
            clinic_id="clinic-demo-002",
            name="Jordan Lee (Synthetic)",
            date_of_birth=date(1978, 11, 2),
            created_at=datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
        )
    )
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
            author_role=AuthorRole.SYSTEM,
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
            author_role=AuthorRole.SYSTEM,
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
            author_role=AuthorRole.SYSTEM,
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
        TimelineEntry(
            id="entry-demo-008",
            patient_id=SYNTHETIC_PATIENT_ID,
            author_role=AuthorRole.SYSTEM,
            author_id="ai-scribe:deterministic-mock",
            timestamp=datetime(2026, 8, 25, 11, 15, tzinfo=timezone.utc),
            type=TimelineEntryType.SYSTEM_EVENT,
            content=(
                "AI-derived care coordination summary: home readings are improving, but nurse "
                "follow-up remains unresolved before the medication safety review."
            ),
            provenance_pointer="synthetic://ai-scribe/nurse-handoff-2026-08-25#transcript",
        ),
    ]
    for entry in entries:
        if db.get(TimelineEntry, entry.id) is None:
            db.add(entry)
    db.flush()
    for entry_spec in entries:
        entry = db.get(TimelineEntry, entry_spec.id)
        if entry is not None and db.query(EntryVersion).filter_by(entry_id=entry.id).first() is None:
            db.add(
                EntryVersion(
                    id=f"version-{entry.id}-001",
                    entry_id=entry.id,
                    version_number=1,
                    content=entry.content,
                    provenance_pointer=entry.provenance_pointer,
                    changed_by=entry.author_id,
                    changed_by_role=entry.author_role.value,
                    created_at=entry.timestamp,
                )
            )

    db.merge(
        Comment(
            id="comment-demo-001",
            entry_id="entry-demo-007",
            author_id="clinician-demo-001",
            author_role=CollaborationRole.CLINICIAN,
            content="@nurse_amy please arrange repeat blood test next week.",
            parent_comment_id=None,
            resolved=False,
            created_at=datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
        )
    )
    db.flush()
    db.merge(
        Comment(
            id="comment-demo-002",
            entry_id="entry-demo-007",
            author_id="staff-demo-001",
            author_role=CollaborationRole.STAFF,
            content="Booked for Tuesday morning; awaiting patient confirmation.",
            parent_comment_id="comment-demo-001",
            resolved=True,
            created_at=datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
        )
    )

    assignments = [
        TaskAssignment(
            id="assignment-demo-lab",
            patient_id=SYNTHETIC_PATIENT_ID,
            entry_id="entry-demo-007",
            title="Arrange pending renal function and potassium labs",
            assigned_role=CollaborationRole.STAFF,
            assigned_user_id="staff-demo-001",
            status=TaskStatus.OPEN,
            created_at=datetime(2026, 8, 25, 8, 5, tzinfo=timezone.utc),
            resolved_at=None,
        ),
        TaskAssignment(
            id="assignment-demo-nurse",
            patient_id=SYNTHETIC_PATIENT_ID,
            entry_id="entry-demo-004",
            title="Complete nurse follow-up on home readings",
            assigned_role=CollaborationRole.STAFF,
            assigned_user_id="nurse_amy",
            status=TaskStatus.OPEN,
            created_at=datetime(2026, 8, 25, 8, 10, tzinfo=timezone.utc),
            resolved_at=None,
        ),
        TaskAssignment(
            id="assignment-demo-review",
            patient_id=SYNTHETIC_PATIENT_ID,
            entry_id="entry-demo-006",
            title="Clinician review after medication dose change",
            assigned_role=CollaborationRole.CLINICIAN,
            assigned_user_id="clinician-demo-001",
            status=TaskStatus.OPEN,
            created_at=datetime(2026, 8, 25, 8, 15, tzinfo=timezone.utc),
            resolved_at=None,
        ),
        TaskAssignment(
            id="assignment-demo-resolved",
            patient_id=SYNTHETIC_PATIENT_ID,
            entry_id="entry-demo-003",
            title="Medication reconciliation call completed",
            assigned_role=CollaborationRole.STAFF,
            assigned_user_id="staff-demo-001",
            status=TaskStatus.COMPLETED,
            created_at=datetime(2026, 2, 6, 8, 30, tzinfo=timezone.utc),
            resolved_at=datetime(2026, 2, 6, 8, 45, tzinfo=timezone.utc),
        ),
    ]
    for assignment in assignments:
        db.merge(assignment)

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
            "entry_id": "entry-demo-008",
            "source_span": "nurse follow-up remains unresolved",
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
        evaluation = evaluate_importance(
            source_timestamp=entry_timestamps[entry_id],
            risk_level=spec["risk_level"],
            unresolved_action=spec["unresolved_action"],
            clinical_entity_type=spec["clinical_entity_type"],
            clinician_confirmed=spec["clinician_confirmed"],
            learned_adjustment=0.0,
            context=" ".join((spec["text"], spec["risk_reason"], spec["source_span"])),
            as_of=DEMO_REFERENCE_TIME,
        )
        db.merge(
            Highlight(
                **{**spec, "risk_level": evaluation.final_risk},
                patient_id=SYNTHETIC_PATIENT_ID,
                provenance_pointer=f"timeline-entry-{entry_id}",
                importance_score=evaluation.final_score,
                created_at=DEMO_REFERENCE_TIME,
            )
        )
    db.commit()
