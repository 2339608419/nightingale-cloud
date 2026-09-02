"""Independent database-level clinic scope for patient-linked objects.

Routes keep their existing authorization/RBAC guard, then must use these queries
before returning content, creating links, or mutating state. Every linked-object
lookup joins back to Patient.clinic_id instead of trusting an already-loaded object.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    AuditLog,
    Comment,
    ConflictRecord,
    ConflictStatus,
    EntryVersion,
    Highlight,
    HighlightStatus,
    Patient,
    PatientDelivery,
    PatientInstructionApproval,
    TaskAssignment,
    TaskStatus,
    TimelineEntry,
)


GLANCE_LIMIT = 5


def get_patient_in_clinic(
    db: Session, patient_id: str, clinic_id: str
) -> Patient | None:
    return db.scalar(
        select(Patient).where(
            Patient.id == patient_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_patient_entries_in_clinic(
    db: Session, patient_id: str, clinic_id: str
) -> list[TimelineEntry]:
    statement = (
        select(TimelineEntry)
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            TimelineEntry.patient_id == patient_id,
            Patient.clinic_id == clinic_id,
        )
        .order_by(TimelineEntry.timestamp.desc(), TimelineEntry.id.desc())
    )
    return list(db.scalars(statement))


def get_entry_in_clinic(
    db: Session, entry_id: str, clinic_id: str
) -> TimelineEntry | None:
    return db.scalar(
        select(TimelineEntry)
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            TimelineEntry.id == entry_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_entry_versions_in_clinic(
    db: Session, entry_id: str, clinic_id: str
) -> list[EntryVersion]:
    statement = (
        select(EntryVersion)
        .join(TimelineEntry, EntryVersion.entry_id == TimelineEntry.id)
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            EntryVersion.entry_id == entry_id,
            Patient.clinic_id == clinic_id,
        )
        .order_by(EntryVersion.version_number.desc())
    )
    return list(db.scalars(statement))


def get_entry_version_in_clinic(
    db: Session, entry_id: str, version_number: int, clinic_id: str
) -> EntryVersion | None:
    return db.scalar(
        select(EntryVersion)
        .join(TimelineEntry, EntryVersion.entry_id == TimelineEntry.id)
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            EntryVersion.entry_id == entry_id,
            EntryVersion.version_number == version_number,
            Patient.clinic_id == clinic_id,
        )
    )


def get_entry_audit_logs_in_clinic(
    db: Session, entry_id: str, clinic_id: str
) -> list[AuditLog]:
    statement = (
        select(AuditLog)
        .join(
            TimelineEntry,
            (AuditLog.entity_type == "timeline_entry")
            & (AuditLog.entity_id == TimelineEntry.id),
        )
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            TimelineEntry.id == entry_id,
            Patient.clinic_id == clinic_id,
        )
        .order_by(AuditLog.timestamp.desc(), AuditLog.id.desc())
    )
    return list(db.scalars(statement))


def get_patient_highlights_in_clinic(
    db: Session, patient_id: str, clinic_id: str
) -> list[Highlight]:
    statement = (
        select(Highlight)
        .join(Patient, Highlight.patient_id == Patient.id)
        .where(
            Highlight.patient_id == patient_id,
            Patient.clinic_id == clinic_id,
            Highlight.status != HighlightStatus.REJECTED,
        )
        .order_by(
            Highlight.importance_score.desc(),
            Highlight.created_at.desc(),
            Highlight.id.desc(),
        )
        .limit(GLANCE_LIMIT)
    )
    return list(db.scalars(statement))


def get_highlight_in_clinic(
    db: Session, highlight_id: str, clinic_id: str
) -> Highlight | None:
    return db.scalar(
        select(Highlight)
        .join(Patient, Highlight.patient_id == Patient.id)
        .where(
            Highlight.id == highlight_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_entry_comments_in_clinic(
    db: Session, entry_id: str, clinic_id: str
) -> list[Comment]:
    statement = (
        select(Comment)
        .join(TimelineEntry, Comment.entry_id == TimelineEntry.id)
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            Comment.entry_id == entry_id,
            Patient.clinic_id == clinic_id,
        )
        .order_by(Comment.created_at.asc(), Comment.id.asc())
    )
    return list(db.scalars(statement))


def get_comment_in_clinic(
    db: Session, comment_id: str, clinic_id: str
) -> Comment | None:
    return db.scalar(
        select(Comment)
        .join(TimelineEntry, Comment.entry_id == TimelineEntry.id)
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            Comment.id == comment_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_patient_assignments_in_clinic(
    db: Session,
    patient_id: str,
    clinic_id: str,
    task_status: TaskStatus | None = None,
) -> list[TaskAssignment]:
    statement = (
        select(TaskAssignment)
        .join(Patient, TaskAssignment.patient_id == Patient.id)
        .where(
            TaskAssignment.patient_id == patient_id,
            Patient.clinic_id == clinic_id,
        )
    )
    if task_status is not None:
        statement = statement.where(TaskAssignment.status == task_status)
    statement = statement.order_by(TaskAssignment.created_at.asc(), TaskAssignment.id.asc())
    return list(db.scalars(statement))


def get_assignment_in_clinic(
    db: Session, assignment_id: str, clinic_id: str
) -> TaskAssignment | None:
    return db.scalar(
        select(TaskAssignment)
        .join(Patient, TaskAssignment.patient_id == Patient.id)
        .where(
            TaskAssignment.id == assignment_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_patient_conflicts_in_clinic(
    db: Session,
    patient_id: str,
    clinic_id: str,
    conflict_status: ConflictStatus | None = None,
) -> list[ConflictRecord]:
    statement = (
        select(ConflictRecord)
        .join(Patient, ConflictRecord.patient_id == Patient.id)
        .where(
            ConflictRecord.patient_id == patient_id,
            Patient.clinic_id == clinic_id,
        )
    )
    if conflict_status is not None:
        statement = statement.where(ConflictRecord.status == conflict_status)
    return list(
        db.scalars(statement.order_by(ConflictRecord.created_at.desc(), ConflictRecord.id))
    )


def get_conflict_in_clinic(
    db: Session, conflict_id: str, clinic_id: str
) -> ConflictRecord | None:
    return db.scalar(
        select(ConflictRecord)
        .join(Patient, ConflictRecord.patient_id == Patient.id)
        .where(
            ConflictRecord.id == conflict_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_patient_instruction_approval_in_clinic(
    db: Session, entry_id: str, clinic_id: str
) -> PatientInstructionApproval | None:
    return db.scalar(
        select(PatientInstructionApproval)
        .join(TimelineEntry, PatientInstructionApproval.entry_id == TimelineEntry.id)
        .join(Patient, TimelineEntry.patient_id == Patient.id)
        .where(
            PatientInstructionApproval.entry_id == entry_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_patient_deliveries_in_clinic(
    db: Session, patient_id: str, clinic_id: str
) -> list[PatientDelivery]:
    statement = (
        select(PatientDelivery)
        .join(Patient, PatientDelivery.patient_id == Patient.id)
        .where(
            PatientDelivery.patient_id == patient_id,
            PatientDelivery.clinic_id == clinic_id,
            Patient.clinic_id == clinic_id,
        )
        .order_by(PatientDelivery.created_at.desc(), PatientDelivery.id.desc())
    )
    return list(db.scalars(statement))


def get_delivery_in_clinic(
    db: Session, delivery_id: str, clinic_id: str
) -> PatientDelivery | None:
    return db.scalar(
        select(PatientDelivery)
        .join(Patient, PatientDelivery.patient_id == Patient.id)
        .where(
            PatientDelivery.id == delivery_id,
            PatientDelivery.clinic_id == clinic_id,
            Patient.clinic_id == clinic_id,
        )
    )


def get_active_entry_deliveries_in_clinic(
    db: Session,
    entry_id: str,
    patient_id: str,
    clinic_id: str,
    statuses: list,
) -> list[PatientDelivery]:
    statement = (
        select(PatientDelivery)
        .join(Patient, PatientDelivery.patient_id == Patient.id)
        .where(
            PatientDelivery.entry_id == entry_id,
            PatientDelivery.patient_id == patient_id,
            PatientDelivery.clinic_id == clinic_id,
            Patient.clinic_id == clinic_id,
            PatientDelivery.status.in_(statuses),
        )
    )
    return list(db.scalars(statement))
