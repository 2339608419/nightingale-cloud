from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    PatientFacingStatus,
    PatientInstructionApproval,
    TimelineEntry,
    TimelineEntryType,
)
from app.services.audit_service import add_trust_action_audit


def set_patient_instruction_status(
    db: Session,
    *,
    entry: TimelineEntry,
    new_status: PatientFacingStatus,
    actor: CurrentUser,
) -> TimelineEntry:
    approval = db.get(PatientInstructionApproval, entry.id)
    if entry.type != TimelineEntryType.INSTRUCTION or approval is None or not approval.ai_derived:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Entry is not an AI-derived patient-facing instruction",
        )
    if new_status == PatientFacingStatus.APPROVED:
        source = db.get(TimelineEntry, approval.source_entry_id)
        expected_pointer = f"timeline-entry-{approval.source_entry_id}"
        if (
            source is None
            or source.patient_id != entry.patient_id
            or not source.provenance_pointer
            or entry.provenance_pointer != expected_pointer
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Needs review: patient-facing provenance cannot be resolved",
            )
    if approval.patient_facing_status == new_status:
        return entry

    previous_status = approval.patient_facing_status
    approval.patient_facing_status = new_status
    if new_status == PatientFacingStatus.APPROVED:
        approval.approved_by = actor.user_id
        approval.approved_at = datetime.now(timezone.utc)
    else:
        approval.approved_by = None
        approval.approved_at = None
    add_trust_action_audit(
        db,
        actor=actor,
        action=(
            "patient_instruction.approved"
            if new_status == PatientFacingStatus.APPROVED
            else "patient_instruction.rejected"
        ),
        entity_type="timeline_entry",
        entity_id=entry.id,
        from_status=previous_status.value,
        to_status=new_status.value,
    )
    db.commit()
    db.refresh(entry)
    return entry
