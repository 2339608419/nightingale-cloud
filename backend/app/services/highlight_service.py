from sqlalchemy import select
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import Highlight, HighlightStatus, Patient, TimelineEntry
from app.schemas.highlight import HighlightSuggestionCreate
from app.services.adaptive_importance_service import learned_bonus, record_feedback
from app.services.importance_service import ImportanceEvaluation, evaluate_importance
from app.services.audit_service import add_trust_action_audit
from app.services.highlight_provenance_service import bind_highlight_to_current_version


GLANCE_LIMIT = 5


def get_patient_highlights(db: Session, patient_id: str) -> list[Highlight] | None:
    if db.get(Patient, patient_id) is None:
        return None
    statement = (
        select(Highlight)
        .where(
            Highlight.patient_id == patient_id,
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


def create_highlight_suggestion(
    db: Session,
    *,
    patient: Patient,
    entry: TimelineEntry,
    payload: HighlightSuggestionCreate,
) -> tuple[Highlight, ImportanceEvaluation, list[str]]:
    bonus, explanation = learned_bonus(
        db,
        clinic_id=patient.clinic_id,
        entity_type=payload.clinical_entity_type,
        entry_type=entry.type,
    )
    evaluation = evaluate_importance(
        source_timestamp=entry.timestamp,
        risk_level=payload.risk_level,
        unresolved_action=payload.unresolved_action,
        clinical_entity_type=payload.clinical_entity_type,
        clinician_confirmed=False,
        learned_adjustment=bonus,
        context=" ".join((payload.text, payload.risk_reason, payload.source_span)),
    )
    if evaluation.safety_floor_rule:
        explanation.append(
            f"Safety floor {evaluation.safety_floor_rule}: "
            f"{evaluation.safety_floor:.1f} / {evaluation.safety_floor_risk.value}; "
            f"applied={evaluation.floor_applied}"
        )
    highlight = Highlight(
        id=str(uuid4()),
        patient_id=patient.id,
        entry_id=entry.id,
        source_span=payload.source_span,
        text=payload.text,
        importance_score=evaluation.final_score,
        risk_level=evaluation.final_risk,
        risk_reason=payload.risk_reason,
        status=HighlightStatus.SUGGESTED,
        provenance_pointer="pending-immutable-binding",
        created_at=datetime.now(timezone.utc),
        clinician_confirmed=False,
        unresolved_action=payload.unresolved_action,
        clinical_entity_type=payload.clinical_entity_type,
    )
    db.add(highlight)
    db.flush()
    bind_highlight_to_current_version(
        db,
        highlight=highlight,
        entry=entry,
        source_span=payload.source_span,
        expected_source_version=payload.expected_source_version,
    )
    db.commit()
    db.refresh(highlight)
    return highlight, evaluation, explanation


def set_highlight_status(
    db: Session,
    *,
    highlight: Highlight,
    patient: Patient,
    new_status: HighlightStatus,
    actor: CurrentUser,
) -> Highlight:
    previous_status = highlight.status
    if previous_status == new_status:
        return highlight
    record_feedback(
        db,
        clinic_id=patient.clinic_id,
        entity_type=highlight.clinical_entity_type,
        entry_type=highlight.entry.type,
        previous_status=previous_status.value,
        new_status=new_status.value,
    )
    if previous_status != HighlightStatus.ACCEPTED and new_status == HighlightStatus.ACCEPTED:
        highlight.importance_score += 15.0
    elif previous_status == HighlightStatus.ACCEPTED and new_status != HighlightStatus.ACCEPTED:
        highlight.importance_score -= 15.0
    highlight.status = new_status
    highlight.clinician_confirmed = new_status == HighlightStatus.ACCEPTED
    add_trust_action_audit(
        db,
        actor=actor,
        action=(
            "highlight.accepted"
            if new_status == HighlightStatus.ACCEPTED
            else "highlight.rejected"
        ),
        entity_type="highlight",
        entity_id=highlight.id,
        from_status=previous_status.value,
        to_status=new_status.value,
    )
    db.commit()
    db.refresh(highlight)
    return highlight
