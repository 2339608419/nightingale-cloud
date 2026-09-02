from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    AuthorRole,
    DeliveryChannel,
    DeliveryFailureReason,
    DeliveryPurpose,
    DeliveryStatus,
    EntryVersion,
    PatientDelivery,
    PatientFacingStatus,
    TimelineEntry,
    TimelineEntryType,
)
from app.services.audit_service import add_trust_action_audit
from app.services.clinic_scope_service import (
    get_delivery_in_clinic,
    get_active_entry_deliveries_in_clinic,
    get_entry_version_in_clinic,
    get_patient_instruction_approval_in_clinic,
)
from app.services.revision_service import ensure_initial_version, get_versions


ALLOWED_TRANSITIONS = {
    DeliveryStatus.CREATED: {DeliveryStatus.QUEUED},
    DeliveryStatus.QUEUED: {DeliveryStatus.SIMULATED_SENT, DeliveryStatus.FAILED},
    DeliveryStatus.SIMULATED_SENT: {DeliveryStatus.SIMULATED_DELIVERED},
}


def _approved_version_number(db: Session, entry: TimelineEntry, clinic_id: str) -> int:
    if entry.type != TimelineEntryType.INSTRUCTION:
        raise HTTPException(status_code=422, detail="Only patient instructions can be delivered")
    approval = get_patient_instruction_approval_in_clinic(db, entry.id, clinic_id)
    if approval is not None:
        if (
            approval.patient_facing_status != PatientFacingStatus.APPROVED
            or approval.approved_version_number is None
        ):
            raise HTTPException(status_code=422, detail="Instruction is not currently approved")
        return approval.approved_version_number
    if entry.author_role != AuthorRole.CLINICIAN:
        raise HTTPException(status_code=422, detail="Instruction is not currently approved")
    ensure_initial_version(db, entry)
    return get_versions(db, entry.id)[0].version_number


def create_delivery(
    db: Session,
    *,
    entry: TimelineEntry,
    actor: CurrentUser,
    masked_destination: str,
    channel: DeliveryChannel,
    purpose: DeliveryPurpose,
    replaces_delivery_id: str | None,
) -> PatientDelivery:
    version_number = _approved_version_number(db, entry, actor.clinic_id)
    version = get_entry_version_in_clinic(db, entry.id, version_number, actor.clinic_id)
    if version is None:
        raise HTTPException(status_code=409, detail="Approved immutable version cannot be resolved")
    replaced = None
    if replaces_delivery_id is not None:
        replaced = get_delivery_in_clinic(db, replaces_delivery_id, actor.clinic_id)
        if (
            replaced is None
            or replaced.patient_id != entry.patient_id
            or replaced.entry_id != entry.id
        ):
            raise HTTPException(status_code=422, detail="Replacement delivery does not match instruction")
        if replaced.status != DeliveryStatus.CORRECTION_REQUIRED:
            raise HTTPException(status_code=409, detail="Only correction-required delivery can be replaced")
        if purpose != DeliveryPurpose.CORRECTION:
            raise HTTPException(status_code=422, detail="Replacement must use correction purpose")
    now = datetime.now(timezone.utc)
    delivery = PatientDelivery(
        id=str(uuid4()),
        clinic_id=actor.clinic_id,
        patient_id=entry.patient_id,
        entry_id=entry.id,
        approved_version_number=version_number,
        channel=channel,
        purpose=purpose,
        masked_destination=masked_destination,
        status=DeliveryStatus.CREATED,
        actor_id=actor.user_id,
        actor_role=actor.role.value,
        provider_message_reference=f"mock_msg_{uuid4().hex}",
        replaces_delivery_id=replaces_delivery_id,
        failure_reason_code=None,
        created_at=now,
        updated_at=now,
    )
    db.add(delivery)
    add_trust_action_audit(
        db,
        actor=actor,
        action="patient_delivery.created",
        entity_type="patient_delivery",
        entity_id=delivery.id,
        from_status="none",
        to_status=DeliveryStatus.CREATED.value,
    )
    if replaced is not None:
        previous = replaced.status
        replaced.status = DeliveryStatus.SUPERSEDED
        replaced.updated_at = now
        add_trust_action_audit(
            db,
            actor=actor,
            action="patient_delivery.superseded",
            entity_type="patient_delivery",
            entity_id=replaced.id,
            from_status=previous.value,
            to_status=DeliveryStatus.SUPERSEDED.value,
        )
    db.commit()
    db.refresh(delivery)
    return delivery


def transition_delivery(
    db: Session,
    delivery: PatientDelivery,
    actor: CurrentUser,
    new_status: DeliveryStatus,
    failure_reason_code: DeliveryFailureReason | None = None,
) -> PatientDelivery:
    if new_status == DeliveryStatus.FAILED and failure_reason_code is None:
        raise HTTPException(status_code=422, detail="Failed delivery requires a safe reason code")
    if new_status != DeliveryStatus.FAILED and failure_reason_code is not None:
        raise HTTPException(
            status_code=422,
            detail="Failure reason is only valid for failed delivery status",
        )
    if new_status == delivery.status:
        return delivery
    if new_status not in ALLOWED_TRANSITIONS.get(delivery.status, set()):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid delivery state transition")
    previous = delivery.status
    delivery.status = new_status
    delivery.failure_reason_code = failure_reason_code if new_status == DeliveryStatus.FAILED else None
    delivery.updated_at = datetime.now(timezone.utc)
    add_trust_action_audit(
        db,
        actor=actor,
        action=f"patient_delivery.{new_status.value}",
        entity_type="patient_delivery",
        entity_id=delivery.id,
        from_status=previous.value,
        to_status=new_status.value,
    )
    db.commit()
    db.refresh(delivery)
    return delivery


def invalidate_deliveries_after_content_change(
    db: Session, entry: TimelineEntry, actor: CurrentUser
) -> None:
    deliveries = get_active_entry_deliveries_in_clinic(
        db,
        entry.id,
        entry.patient_id,
        actor.clinic_id,
        [
            DeliveryStatus.CREATED,
            DeliveryStatus.QUEUED,
            DeliveryStatus.SIMULATED_SENT,
            DeliveryStatus.SIMULATED_DELIVERED,
        ],
    )
    now = datetime.now(timezone.utc)
    for delivery in deliveries:
        previous = delivery.status
        if previous in {DeliveryStatus.CREATED, DeliveryStatus.QUEUED}:
            delivery.status = DeliveryStatus.SUPERSEDED
        else:
            delivery.status = DeliveryStatus.CORRECTION_REQUIRED
        delivery.updated_at = now
        add_trust_action_audit(
            db,
            actor=actor,
            action=f"patient_delivery.{delivery.status.value}",
            entity_type="patient_delivery",
            entity_id=delivery.id,
            from_status=previous.value,
            to_status=delivery.status.value,
        )
