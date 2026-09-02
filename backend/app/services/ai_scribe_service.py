import logging
from dataclasses import dataclass
from hashlib import sha256
from typing import Literal

from sqlalchemy.orm import Session

from app.models import AuthorRole, Patient, TimelineEntry, TimelineEntryType
from app.schemas.ai_scribe import (
    InteractionType,
    RedactionMetadata,
    RedactionValidationMetadata,
)
from app.services.patient_service import create_patient_entry
from app.services.conflict_service import detect_conflicts_for_entry
from app.services.redaction_service import redact_phi, validate_redaction
from app.services.summarization_provider import (
    InvalidProviderResponseError,
    ProviderFailure,
    ProviderUnavailableError,
    SummaryProvider,
)


logger = logging.getLogger(__name__)

ENTRY_TYPES = {
    InteractionType.DOCTOR_CONSULT: TimelineEntryType.AI_DOCTOR_CONSULT_SUMMARY,
    InteractionType.NURSE_CONSULT: TimelineEntryType.AI_NURSE_CONSULT_SUMMARY,
    InteractionType.PATIENT_SESSION: TimelineEntryType.AI_PATIENT_SESSION_SUMMARY,
}

AiScribeOutcome = Literal[
    "success",
    "redaction_withheld",
    "provider_timeout",
    "provider_unavailable",
    "invalid_provider_response",
]


@dataclass(frozen=True)
class AiScribeIngestionResult:
    entry: TimelineEntry | None
    redaction: RedactionMetadata
    validation: RedactionValidationMetadata
    outcome: AiScribeOutcome


def provider_generation_mode(provider: SummaryProvider) -> str:
    mode = getattr(provider, "generation_mode", "test_double")
    if mode not in {"external_model", "rule_derived_mock", "test_double"}:
        return "test_double"
    return mode


def opaque_source_reference(external_source_id: str) -> str:
    """Create a stable one-way reference; never persist or log the external value."""
    digest = sha256(
        f"nightingale-ai-scribe-source-v1\0{external_source_id}".encode("utf-8")
    ).hexdigest()
    return f"src_sha256_{digest}"


def ingest_synthetic_transcript(
    db: Session,
    *,
    patient: Patient,
    interaction_type: InteractionType,
    external_source_id: str,
    transcript: str,
    provider: SummaryProvider,
) -> AiScribeIngestionResult:
    source_ref = opaque_source_reference(external_source_id)
    known_patient_name = patient.name.removesuffix(" (Synthetic)")
    redaction = redact_phi(transcript, known_names=(known_patient_name,))
    metadata = RedactionMetadata(
        original_character_count=len(transcript),
        redacted_character_count=len(redaction.text),
        names_redacted=redaction.names_redacted,
        ids_redacted=redaction.ids_redacted,
        phones_redacted=redaction.phones_redacted,
        total_redactions=redaction.total_redactions,
    )
    validation_result = validate_redaction(
        transcript,
        redaction,
        known_names=(known_patient_name,),
    )
    validation = RedactionValidationMetadata(
        passed=validation_result.passed,
        detected_redactions=validation_result.detected_redactions,
        remaining_phi_patterns=list(validation_result.remaining_phi_patterns),
        protected_terms_preserved=validation_result.protected_terms_preserved,
        missing_protected_terms=list(validation_result.missing_protected_terms),
        output_integrity_valid=validation_result.output_integrity_valid,
        reason=validation_result.reason,
    )
    if not validation_result.passed:
        logger.warning(
            "Synthetic AI-scribe withheld source_ref=%s interaction_type=%s "
            "redactions=%d validation_reason=%s",
            source_ref,
            interaction_type.value,
            redaction.total_redactions,
            validation_result.reason,
        )
        return AiScribeIngestionResult(
            entry=None,
            redaction=metadata,
            validation=validation,
            outcome="redaction_withheld",
        )

    # Security boundary: only text that is both redacted and validated may cross
    # into a summarization provider.
    try:
        summary = provider.summarize(
            redaction.text,
            interaction_type=interaction_type.value,
        )
        if not isinstance(summary, str) or not summary.strip():
            raise InvalidProviderResponseError()
        summary = summary.strip()
    except ProviderFailure as error:
        logger.warning(
            "Synthetic AI-scribe safely abstained source_ref=%s interaction_type=%s "
            "provider=%s outcome=%s",
            source_ref,
            interaction_type.value,
            provider.name,
            error.outcome,
        )
        return AiScribeIngestionResult(
            entry=None,
            redaction=metadata,
            validation=validation,
            outcome=error.outcome,
        )
    except Exception:
        # Third-party/test-provider exceptions may contain request or response text.
        # Do not log the exception object or traceback; classify it conservatively.
        error = ProviderUnavailableError()
        logger.warning(
            "Synthetic AI-scribe safely abstained source_ref=%s interaction_type=%s "
            "provider=%s outcome=%s",
            source_ref,
            interaction_type.value,
            provider.name,
            error.outcome,
        )
        return AiScribeIngestionResult(
            entry=None,
            redaction=metadata,
            validation=validation,
            outcome=error.outcome,
        )
    provenance_pointer = f"synthetic://ai-scribe/{source_ref}#transcript"
    entry = create_patient_entry(
        db,
        patient_id=patient.id,
        author_role=AuthorRole.SYSTEM,
        author_id=f"ai-scribe:{provider.name}",
        entry_type=ENTRY_TYPES[interaction_type],
        content=summary,
        provenance_pointer=provenance_pointer,
    )
    detect_conflicts_for_entry(db, entry)
    logger.info(
        "Synthetic AI-scribe entry created source_ref=%s interaction_type=%s redactions=%d",
        source_ref,
        interaction_type.value,
        redaction.total_redactions,
    )
    return AiScribeIngestionResult(
        entry=entry,
        redaction=metadata,
        validation=validation,
        outcome="success",
    )
