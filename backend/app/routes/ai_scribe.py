from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.schemas import AiScribeRequest, AiScribeResponse, TimelineEntryRead
from app.services.ai_scribe_service import ingest_synthetic_transcript
from app.services.authorization_service import require_ai_scribe_access, require_patient_access
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
    entry, redaction, validation = ingest_synthetic_transcript(
        db,
        patient=patient,
        interaction_type=payload.interaction_type,
        source_id=payload.source_id,
        transcript=payload.transcript,
        provider=provider,
    )
    if entry is None:
        response.status_code = status.HTTP_200_OK
        return AiScribeResponse(
            status="withheld",
            message="AI scribe withheld pending redaction review",
            provider=provider.name,
            redaction=redaction,
            validation=validation,
            generated_summary=None,
            timeline_entry=None,
            provenance_pointer=None,
        )
    return AiScribeResponse(
        status="created",
        message="AI-scribed timeline entry created",
        provider=provider.name,
        redaction=redaction,
        validation=validation,
        generated_summary=entry.content,
        timeline_entry=TimelineEntryRead.model_validate(entry),
        provenance_pointer=entry.provenance_pointer or "",
    )
