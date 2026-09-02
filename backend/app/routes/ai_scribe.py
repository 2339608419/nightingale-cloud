from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import AiScribeRequest, AiScribeResponse, TimelineEntryRead
from app.services.ai_scribe_service import (
    ingest_synthetic_transcript,
    provider_generation_mode,
)
from app.services.authorization_service import require_ai_scribe_access, require_patient_access
from app.services.clinic_scope_service import get_patient_in_clinic
from app.services.patient_service import get_patient
from app.services.summarization_provider import SummaryProvider, get_summary_provider


router = APIRouter(prefix="/ai-scribe", tags=["ai-scribe"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]
Provider = Annotated[SummaryProvider, Depends(get_summary_provider)]


@router.post("", response_model=AiScribeResponse, status_code=201)
def create_ai_scribed_note(
    payload: AiScribeRequest,
    db: DbSession,
    user: Identity,
    provider: Provider,
    response: Response,
) -> AiScribeResponse:
    patient = get_patient(db, payload.patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    require_patient_access(user, patient)
    require_ai_scribe_access(user)
    scoped_patient = get_patient_in_clinic(db, payload.patient_id, user.clinic_id)
    if scoped_patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    result = ingest_synthetic_transcript(
        db,
        patient=scoped_patient,
        interaction_type=payload.interaction_type,
        external_source_id=payload.source_id,
        transcript=payload.transcript,
        provider=provider,
    )
    generation_mode = provider_generation_mode(provider)
    if result.entry is None:
        response_status, message = {
            "redaction_withheld": (
                status.HTTP_200_OK,
                "AI scribe withheld pending redaction review",
            ),
            "provider_timeout": (
                status.HTTP_504_GATEWAY_TIMEOUT,
                "AI scribe withheld because the provider timed out",
            ),
            "provider_unavailable": (
                status.HTTP_503_SERVICE_UNAVAILABLE,
                "AI scribe withheld because the provider is unavailable",
            ),
            "invalid_provider_response": (
                status.HTTP_502_BAD_GATEWAY,
                "AI scribe withheld because the provider response was invalid",
            ),
        }[result.outcome]
        response.status_code = response_status
        return AiScribeResponse(
            status="withheld",
            outcome=result.outcome,
            message=message,
            provider=provider.name,
            generation_mode=generation_mode,
            safe_abstention=True,
            redaction=result.redaction,
            validation=result.validation,
            generated_summary=None,
            timeline_entry=None,
            provenance_pointer=None,
        )
    success_message = (
        "Rule-derived mock AI-scribed timeline entry created"
        if generation_mode == "rule_derived_mock"
        else "AI-scribed timeline entry created"
    )
    return AiScribeResponse(
        status="created",
        outcome="success",
        message=success_message,
        provider=provider.name,
        generation_mode=generation_mode,
        safe_abstention=False,
        redaction=result.redaction,
        validation=result.validation,
        generated_summary=result.entry.content,
        timeline_entry=TimelineEntryRead.model_validate(result.entry),
        provenance_pointer=result.entry.provenance_pointer or "",
    )
