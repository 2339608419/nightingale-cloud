from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import ClinicalEntityType, Highlight, HighlightStatus
from app.schemas import (
    HighlightRead,
    HighlightSourceSnapshotRead,
    HighlightSuggestionCreate,
    HighlightSuggestionRead,
    ImportancePreferenceRead,
    ExposureCreate,
    ExposureRead,
    FeedbackPolicyRead,
    TrustMetricsRead,
)
from app.services.adaptive_importance_service import get_preferences, preference_weight
from app.services.authorization_service import (
    require_entry_collaboration_access,
    require_highlight_decision_access,
    require_patient_access,
    can_view_entry,
)
from app.services.highlight_service import (
    create_highlight_suggestion, set_highlight_status, undo_highlight_feedback,
)
from app.services.evidence_confidence_service import highlight_read
from app.services.patient_service import get_entry, get_patient
from app.services.clinic_scope_service import (
    get_entry_in_clinic,
    get_highlight_in_clinic,
    get_highlight_provenance_in_clinic,
    get_patient_in_clinic,
    get_all_patient_highlights_in_clinic,
)
from app.services.ranking_feedback_service import (
    feedback_policy, record_exposure, trust_metrics,
)
from app.services.highlight_provenance_service import (
    HighlightSourceVersionConflict,
    resolve_highlight_provenance,
)


router = APIRouter(tags=["highlights"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


@router.post(
    "/entries/{entry_id}/highlights",
    response_model=HighlightSuggestionRead,
    status_code=201,
)
def suggest_highlight(
    entry_id: str,
    payload: HighlightSuggestionCreate,
    db: DbSession,
    user: Identity,
) -> HighlightSuggestionRead:
    entry = get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    patient = get_patient(db, entry.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    scoped_entry = get_entry_in_clinic(db, entry_id, user.clinic_id)
    scoped_patient = get_patient_in_clinic(db, patient.id, user.clinic_id)
    if scoped_entry is None or scoped_patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Entry not found")
    require_entry_collaboration_access(user, scoped_entry)
    if payload.source_span not in scoped_entry.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source span must occur in the timeline entry",
        )
    try:
        highlight, evaluation, explanation = create_highlight_suggestion(
            db,
            patient=scoped_patient,
            entry=scoped_entry,
            payload=payload,
        )
    except HighlightSourceVersionConflict as conflict:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "error_code": "highlight_source_version_conflict",
                "entry_id": scoped_entry.id,
                "expected_version": payload.expected_source_version,
                "current_version": conflict.current_version,
            },
        ) from conflict
    except ValueError as error:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(error)) from error
    return HighlightSuggestionRead(
        highlight=highlight_read(db, highlight, user.clinic_id),
        base_score=evaluation.base_score,
        learned_bonus=evaluation.learned_adjustment,
        learned_adjustment=evaluation.learned_adjustment,
        adjusted_score=evaluation.adjusted_score,
        safety_floor=evaluation.safety_floor,
        safety_floor_risk=evaluation.safety_floor_risk,
        safety_floor_rule=evaluation.safety_floor_rule,
        final_score=evaluation.final_score,
        floor_applied=evaluation.floor_applied,
        explanation=explanation,
    )


def _decide_highlight(
    highlight_id: str,
    decision: HighlightStatus,
    db: Session,
    user: CurrentUser,
) -> HighlightRead:
    highlight = db.get(Highlight, highlight_id)
    if highlight is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Highlight not found")
    patient = get_patient(db, highlight.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_highlight_decision_access(user)
    scoped_highlight = get_highlight_in_clinic(db, highlight_id, user.clinic_id)
    scoped_patient = get_patient_in_clinic(db, patient.id, user.clinic_id)
    if scoped_highlight is None or scoped_patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Highlight not found")
    updated = set_highlight_status(
        db,
        highlight=scoped_highlight,
        patient=scoped_patient,
        new_status=decision,
        actor=user,
    )
    return highlight_read(db, updated, user.clinic_id)


@router.post("/highlights/{highlight_id}/accept", response_model=HighlightRead)
def accept_highlight(highlight_id: str, db: DbSession, user: Identity) -> HighlightRead:
    return _decide_highlight(highlight_id, HighlightStatus.ACCEPTED, db, user)


@router.post("/highlights/{highlight_id}/reject", response_model=HighlightRead)
def reject_highlight(highlight_id: str, db: DbSession, user: Identity) -> HighlightRead:
    return _decide_highlight(highlight_id, HighlightStatus.REJECTED, db, user)


@router.post("/highlights/{highlight_id}/feedback/undo", response_model=HighlightRead)
def undo_feedback(highlight_id: str, db: DbSession, user: Identity) -> HighlightRead:
    highlight = db.get(Highlight, highlight_id)
    if highlight is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    patient = get_patient(db, highlight.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    require_patient_access(user, patient)
    require_highlight_decision_access(user)
    scoped_highlight = get_highlight_in_clinic(db, highlight_id, user.clinic_id)
    scoped_patient = get_patient_in_clinic(db, patient.id, user.clinic_id)
    if scoped_highlight is None or scoped_patient is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    updated, _ = undo_highlight_feedback(
        db, highlight=scoped_highlight, patient=scoped_patient, actor=user
    )
    return highlight_read(db, updated, user.clinic_id)


@router.post("/highlights/{highlight_id}/exposures", response_model=ExposureRead)
def expose_highlight(
    highlight_id: str, payload: ExposureCreate, db: DbSession, user: Identity
) -> ExposureRead:
    require_highlight_decision_access(user)
    highlight = get_highlight_in_clinic(db, highlight_id, user.clinic_id)
    if highlight is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    patient = get_patient_in_clinic(db, highlight.patient_id, user.clinic_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Highlight not found")
    require_patient_access(user, patient)
    return ExposureRead(recorded=record_exposure(
        db, highlight=highlight, clinic_id=user.clinic_id, actor=user,
        display_reference=payload.display_reference,
    ))


@router.get("/patients/{patient_id}/highlight-review-queue", response_model=list[HighlightRead])
def review_queue(patient_id: str, db: DbSession, user: Identity) -> list[HighlightRead]:
    require_highlight_decision_access(user)
    patient = get_patient_in_clinic(db, patient_id, user.clinic_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    require_patient_access(user, patient)
    all_items = get_all_patient_highlights_in_clinic(db, patient_id, user.clinic_id)
    # Keep the main Glance ranking untouched; queue lower-ranked suggested candidates.
    ranked = [item for item in all_items if item.status != HighlightStatus.REJECTED]
    queue = [item for item in all_items if item.status == HighlightStatus.REJECTED]
    queue.extend(item for item in ranked[5:] if item.status == HighlightStatus.SUGGESTED)
    return [highlight_read(db, item, user.clinic_id) for item in queue]


@router.get("/patients/{patient_id}/highlight-trust-metrics", response_model=TrustMetricsRead)
def read_trust_metrics(patient_id: str, db: DbSession, user: Identity) -> TrustMetricsRead:
    require_highlight_decision_access(user)
    patient = get_patient_in_clinic(db, patient_id, user.clinic_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    require_patient_access(user, patient)
    return TrustMetricsRead(**trust_metrics(db, user.clinic_id, patient_id))


@router.get("/importance-feedback-policy/{entity_type}", response_model=FeedbackPolicyRead)
def read_feedback_policy(entity_type: str, db: DbSession, user: Identity) -> FeedbackPolicyRead:
    require_highlight_decision_access(user)
    try:
        category = ClinicalEntityType(entity_type)
    except ValueError as error:
        raise HTTPException(status_code=422, detail="Unknown entity type") from error
    return FeedbackPolicyRead(**feedback_policy(db, user.clinic_id, category))


@router.get(
    "/highlights/{highlight_id}/source",
    response_model=HighlightSourceSnapshotRead,
)
def read_highlight_source(
    highlight_id: str, db: DbSession, user: Identity
) -> HighlightSourceSnapshotRead:
    highlight = get_highlight_in_clinic(db, highlight_id, user.clinic_id)
    binding = get_highlight_provenance_in_clinic(db, highlight_id, user.clinic_id)
    if highlight is None or binding is None:
        raise HTTPException(status_code=404, detail="Highlight source not found")
    patient = get_patient_in_clinic(db, highlight.patient_id, user.clinic_id)
    entry = get_entry_in_clinic(db, binding.entry_id, user.clinic_id)
    if patient is None or entry is None:
        raise HTTPException(status_code=404, detail="Highlight source not found")
    require_patient_access(user, patient)
    if not can_view_entry(user, entry):
        raise HTTPException(status_code=403, detail="Role cannot view this source")
    resolved = resolve_highlight_provenance(db, highlight, user.clinic_id)
    if resolved.snapshot is None or resolved.status.value == "broken":
        raise HTTPException(
            status_code=409,
            detail={"error_code": "highlight_provenance_broken", "highlight_id": highlight.id},
        )
    return HighlightSourceSnapshotRead(
        highlight_id=highlight.id,
        entry_id=binding.entry_id,
        source_version_number=binding.source_version_number,
        version_provenance_pointer=binding.version_provenance_pointer,
        provenance_status=resolved.status,
        source_changed=resolved.source_changed,
        content=resolved.snapshot.content,
        source_span=binding.source_span,
        source_span_verified=resolved.source_span_verified,
        created_at=resolved.snapshot.created_at,
    )


@router.get("/importance-preferences", response_model=list[ImportancePreferenceRead])
def read_importance_preferences(db: DbSession, user: Identity) -> list[ImportancePreferenceRead]:
    if user.role.value == "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Preferences are internal")
    return [
        ImportancePreferenceRead(
            category_type=item.category_type,
            category_value=item.category_value,
            accepted_count=item.accepted_count,
            rejected_count=item.rejected_count,
            weight=preference_weight(item),
            explanation=(
                f"{item.accepted_count} accepted × "
                f"{5 if item.category_type == 'entity' else 2}; "
                f"{item.rejected_count} rejected × "
                f"-{2 if item.category_type == 'entity' else 1}"
            ),
            negative_feedback_state=(
                feedback_policy(db, user.clinic_id, item.category_value)["negative_feedback_state"]
                if item.category_type == "entity"
                else "derived_from_actor_events_or_legacy_baseline"
            ),
        )
        for item in get_preferences(db, user.clinic_id)
    ]
