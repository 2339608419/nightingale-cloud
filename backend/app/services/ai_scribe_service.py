import logging

from sqlalchemy.orm import Session

from app.models import AuthorRole, Patient, TimelineEntry, TimelineEntryType
from app.schemas.ai_scribe import InteractionType, RedactionMetadata
from app.services.patient_service import create_patient_entry
from app.services.redaction_service import redact_phi
from app.services.summarization_provider import SummaryProvider


logger = logging.getLogger(__name__)

ENTRY_TYPES = {
    InteractionType.DOCTOR_CONSULT: TimelineEntryType.AI_DOCTOR_CONSULT_SUMMARY,
    InteractionType.NURSE_CONSULT: TimelineEntryType.AI_NURSE_CONSULT_SUMMARY,
    InteractionType.PATIENT_SESSION: TimelineEntryType.AI_PATIENT_SESSION_SUMMARY,
}


def ingest_synthetic_transcript(
    db: Session,
    *,
    patient: Patient,
    interaction_type: InteractionType,
    source_id: str,
    transcript: str,
    provider: SummaryProvider,
) -> tuple[TimelineEntry, RedactionMetadata]:
    known_patient_name = patient.name.removesuffix(" (Synthetic)")
    redaction = redact_phi(transcript, known_names=(known_patient_name,))

    # Security boundary: only redaction.text may cross into a summarization provider.
    summary = provider.summarize(redaction.text, interaction_type=interaction_type.value)
    provenance_pointer = f"synthetic://ai-scribe/{source_id}#transcript"
    entry = create_patient_entry(
        db,
        patient_id=patient.id,
        author_role=AuthorRole.SYSTEM,
        author_id=f"ai-scribe:{provider.name}",
        entry_type=ENTRY_TYPES[interaction_type],
        content=summary,
        provenance_pointer=provenance_pointer,
    )
    metadata = RedactionMetadata(
        original_character_count=len(transcript),
        redacted_character_count=len(redaction.text),
        names_redacted=redaction.names_redacted,
        ids_redacted=redaction.ids_redacted,
        phones_redacted=redaction.phones_redacted,
        total_redactions=redaction.total_redactions,
    )
    logger.info(
        "Synthetic AI-scribe entry created source_id=%s interaction_type=%s redactions=%d",
        source_id,
        interaction_type.value,
        redaction.total_redactions,
    )
    return entry, metadata
