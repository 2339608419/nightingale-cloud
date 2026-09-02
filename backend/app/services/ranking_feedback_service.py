from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import distinct, select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    ClinicalEntityType,
    FeedbackDecision,
    Highlight,
    HighlightExposure,
    HighlightFeedback,
    HighlightStatus,
    ImportancePreference,
    RiskLevel,
)
from app.services.audit_service import add_trust_action_audit


NEGATIVE_INDEPENDENT_CLINICIAN_THRESHOLD = 2
POSITIVE_ENTITY_WEIGHT = 5.0
NEGATIVE_ENTITY_WEIGHT = 2.0
MIN_TOTAL_BONUS = -10.0
MAX_TOTAL_BONUS = 25.0


def _active_category_rows(
    db: Session, clinic_id: str, category_value: str, *, category_type: str = "entity"
) -> list[HighlightFeedback]:
    category_column = (
        HighlightFeedback.category_value
        if category_type == "entity"
        else HighlightFeedback.entry_type_value
    )
    return list(db.scalars(select(HighlightFeedback).where(
        HighlightFeedback.clinic_id == clinic_id,
        category_column == category_value,
        HighlightFeedback.decision != FeedbackDecision.UNDONE,
    )))


def _sync_preference(
    db: Session, clinic_id: str, category_type: str, category_value: str
) -> tuple[int, int, bool]:
    rows = _active_category_rows(
        db, clinic_id, category_value, category_type=category_type
    )
    accepted = sum(row.decision == FeedbackDecision.ACCEPTED for row in rows)
    rejecting_actors = {row.actor_id for row in rows if row.decision == FeedbackDecision.REJECTED}
    negative_applied = len(rejecting_actors) >= NEGATIVE_INDEPENDENT_CLINICIAN_THRESHOLD
    rejected = len(rejecting_actors) if negative_applied else 0
    preference = db.scalar(select(ImportancePreference).where(
        ImportancePreference.clinic_id == clinic_id,
        ImportancePreference.category_type == category_type,
        ImportancePreference.category_value == category_value,
    ))
    if preference is None:
        preference = ImportancePreference(
            id=str(uuid4()), clinic_id=clinic_id, category_type=category_type,
            category_value=category_value, accepted_count=0, rejected_count=0,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(preference)
    preference.accepted_count = accepted
    preference.rejected_count = rejected
    preference.updated_at = datetime.now(timezone.utc)
    return accepted, len(rejecting_actors), negative_applied


def record_actor_feedback(
    db: Session, *, highlight: Highlight, clinic_id: str, actor: CurrentUser,
    decision: FeedbackDecision,
) -> tuple[bool, str]:
    row = db.scalar(select(HighlightFeedback).where(
        HighlightFeedback.clinic_id == clinic_id,
        HighlightFeedback.highlight_id == highlight.id,
        HighlightFeedback.actor_id == actor.user_id,
    ))
    previous = row.decision if row is not None else FeedbackDecision.UNDONE
    if previous == decision:
        return False, "no_change"
    now = datetime.now(timezone.utc)
    if row is None:
        row = HighlightFeedback(
            id=str(uuid4()), clinic_id=clinic_id, highlight_id=highlight.id,
            actor_id=actor.user_id, actor_role=actor.role.value, decision=decision,
            category_type="entity", category_value=highlight.clinical_entity_type.value,
            entry_type_value=highlight.entry.type.value,
            created_at=now, updated_at=now,
        )
        db.add(row)
    else:
        row.decision = decision
        row.updated_at = now
    db.flush()
    _, rejectors, negative_applied = _sync_preference(
        db, clinic_id, "entity", highlight.clinical_entity_type.value
    )
    _sync_preference(db, clinic_id, "entry_type", highlight.entry.type.value)
    active_for_highlight = list(db.scalars(select(HighlightFeedback).where(
        HighlightFeedback.clinic_id == clinic_id,
        HighlightFeedback.highlight_id == highlight.id,
        HighlightFeedback.decision != FeedbackDecision.UNDONE,
    )))
    old_status = highlight.status
    if any(item.decision == FeedbackDecision.ACCEPTED for item in active_for_highlight):
        highlight.status = HighlightStatus.ACCEPTED
        highlight.clinician_confirmed = True
    elif active_for_highlight:
        highlight.status = HighlightStatus.REJECTED
        highlight.clinician_confirmed = False
    else:
        highlight.status = HighlightStatus.SUGGESTED
        highlight.clinician_confirmed = False
    if old_status != HighlightStatus.ACCEPTED and highlight.status == HighlightStatus.ACCEPTED:
        highlight.importance_score += 15.0
    elif old_status == HighlightStatus.ACCEPTED and highlight.status != HighlightStatus.ACCEPTED:
        highlight.importance_score -= 15.0
    action = {
        FeedbackDecision.ACCEPTED: "highlight.accepted",
        FeedbackDecision.REJECTED: "highlight.rejected",
        FeedbackDecision.UNDONE: "highlight.feedback_undone",
    }[decision]
    add_trust_action_audit(
        db, actor=actor, action=action, entity_type="highlight", entity_id=highlight.id,
        from_status=old_status.value, to_status=highlight.status.value,
    )
    db.commit()
    db.refresh(highlight)
    state = "applied" if negative_applied else (
        f"suppressed_until_{NEGATIVE_INDEPENDENT_CLINICIAN_THRESHOLD}_independent_clinicians"
        if rejectors else "not_applicable"
    )
    return True, state


def record_exposure(
    db: Session, *, highlight: Highlight, clinic_id: str, actor: CurrentUser,
    display_reference: str,
) -> bool:
    existing = db.scalar(select(HighlightExposure.id).where(
        HighlightExposure.clinic_id == clinic_id,
        HighlightExposure.highlight_id == highlight.id,
        HighlightExposure.display_reference == display_reference,
    ))
    if existing is not None:
        return False
    db.add(HighlightExposure(
        id=str(uuid4()), clinic_id=clinic_id, highlight_id=highlight.id,
        actor_id=actor.user_id, actor_role=actor.role.value,
        display_reference=display_reference, created_at=datetime.now(timezone.utc),
    ))
    db.commit()
    return True


def feedback_policy(db: Session, clinic_id: str, entity_type: ClinicalEntityType | str) -> dict:
    entity_value = entity_type.value if isinstance(entity_type, ClinicalEntityType) else entity_type
    rows = _active_category_rows(db, clinic_id, entity_value)
    rejectors = {row.actor_id for row in rows if row.decision == FeedbackDecision.REJECTED}
    state = "applied" if len(rejectors) >= NEGATIVE_INDEPENDENT_CLINICIAN_THRESHOLD else "suppressed"
    return {
        "positive_weight": POSITIVE_ENTITY_WEIGHT,
        "negative_weight": NEGATIVE_ENTITY_WEIGHT,
        "negative_independent_clinician_threshold": NEGATIVE_INDEPENDENT_CLINICIAN_THRESHOLD,
        "minimum_adjustment": MIN_TOTAL_BONUS,
        "maximum_adjustment": MAX_TOTAL_BONUS,
        "negative_feedback_state": state,
        "explanation": [
            "Positive active clinician decisions contribute immediately.",
            f"Negative learning requires {NEGATIVE_INDEPENDENT_CLINICIAN_THRESHOLD} independent clinicians per category.",
            "Clinical safety floors are applied after the eligible learned adjustment.",
        ],
    }


def trust_metrics(db: Session, clinic_id: str, patient_id: str) -> dict:
    candidates = list(db.scalars(select(Highlight).where(Highlight.patient_id == patient_id)))
    candidate_ids = {item.id for item in candidates}
    exposed_ids = set(db.scalars(select(distinct(HighlightExposure.highlight_id)).where(
        HighlightExposure.clinic_id == clinic_id,
        HighlightExposure.highlight_id.in_(candidate_ids),
    ))) if candidate_ids else set()
    feedback = list(db.scalars(select(HighlightFeedback).where(
        HighlightFeedback.clinic_id == clinic_id,
        HighlightFeedback.highlight_id.in_(candidate_ids),
    ))) if candidate_ids else []
    active = [item for item in feedback if item.decision != FeedbackDecision.UNDONE]
    decided_ids = {item.highlight_id for item in active}
    categories = {item.clinical_entity_type.value for item in candidates}
    suppressed = applied = 0
    for category in categories:
        rejectors = {
            item.actor_id for item in active
            if item.category_value == category and item.decision == FeedbackDecision.REJECTED
        }
        if rejectors:
            if len(rejectors) >= NEGATIVE_INDEPENDENT_CLINICIAN_THRESHOLD:
                applied += 1
            else:
                suppressed += 1
    floor_count = sum(
        item.clinical_entity_type == ClinicalEntityType.ALLERGY
        and item.risk_level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        for item in candidates
    )
    return {
        "eligible_candidate_count": len(candidates),
        "exposed_count": len(exposed_ids),
        "unexposed_count": len(candidate_ids - exposed_ids),
        "decided_count": len(decided_ids),
        "undecided_exposed_count": len(exposed_ids - decided_ids),
        "feedback_undone_count": sum(item.decision == FeedbackDecision.UNDONE for item in feedback),
        "negative_feedback_suppressed_count": suppressed,
        "negative_feedback_applied_count": applied,
        "safety_floor_protected_count": floor_count,
        "metric_purpose": "Exposure-bias diagnostics only; not clinical model accuracy.",
    }
