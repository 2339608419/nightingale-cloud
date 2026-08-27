from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import Highlight, HighlightStatus
from app.schemas import (
    HighlightRead,
    HighlightSuggestionCreate,
    HighlightSuggestionRead,
    ImportancePreferenceRead,
)
from app.services.adaptive_importance_service import get_preferences, preference_weight
from app.services.authorization_service import (
    require_entry_collaboration_access,
    require_highlight_decision_access,
    require_patient_access,
)
from app.services.highlight_service import create_highlight_suggestion, set_highlight_status
from app.services.evidence_confidence_service import highlight_read
from app.services.patient_service import get_entry, get_patient


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
    require_entry_collaboration_access(user, entry)
    if payload.source_span not in entry.content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Source span must occur in the timeline entry",
        )
    highlight, evaluation, explanation = create_highlight_suggestion(
        db,
        patient=patient,
        entry=entry,
        payload=payload,
    )
    return HighlightSuggestionRead(
        highlight=highlight_read(db, highlight),
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
    updated = set_highlight_status(
        db,
        highlight=highlight,
        patient=patient,
        new_status=decision,
        actor=user,
    )
    return highlight_read(db, updated)


@router.post("/highlights/{highlight_id}/accept", response_model=HighlightRead)
def accept_highlight(highlight_id: str, db: DbSession, user: Identity) -> HighlightRead:
    return _decide_highlight(highlight_id, HighlightStatus.ACCEPTED, db, user)


@router.post("/highlights/{highlight_id}/reject", response_model=HighlightRead)
def reject_highlight(highlight_id: str, db: DbSession, user: Identity) -> HighlightRead:
    return _decide_highlight(highlight_id, HighlightStatus.REJECTED, db, user)


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
        )
        for item in get_preferences(db, user.clinic_id)
    ]
