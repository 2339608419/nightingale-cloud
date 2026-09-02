from dataclasses import dataclass

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    ConflictRecord,
    ConflictStatus,
    EvidenceConfidenceLevel,
    Highlight,
)
from app.schemas.highlight import HighlightRead
from app.services.conflict_service import extract_clinical_facts
from app.services.highlight_provenance_service import resolve_highlight_provenance


@dataclass(frozen=True)
class EvidenceConfidence:
    evidence_confidence_level: EvidenceConfidenceLevel
    confidence_reason: str
    requires_review: bool
    abstained: bool
    provenance_resolved: bool
    source_span_verified: bool
    structured_fact_match: bool
    open_conflict: bool


def evaluate_evidence_confidence(
    db: Session, highlight: Highlight, clinic_id: str | None = None
) -> EvidenceConfidence:
    """Evaluate confidence only from resolvable evidence and deterministic state."""
    resolved = resolve_highlight_provenance(db, highlight, clinic_id)
    source = resolved.snapshot
    provenance_resolved = (
        resolved.binding is not None
        and source is not None
        and resolved.status.value != "broken"
    )
    source_span_verified = resolved.source_span_verified

    if source is None:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.ABSTAIN,
            "Needs review · Source entry cannot be resolved.",
            True,
            True,
            False,
            False,
            False,
            False,
        )
    if not provenance_resolved:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.ABSTAIN,
            "Needs review · Provenance pointer does not resolve to the source entry.",
            True,
            True,
            False,
            source_span_verified,
            False,
            False,
        )
    if not source_span_verified:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.ABSTAIN,
            "Needs review · Exact source span cannot be verified.",
            True,
            True,
            True,
            False,
            False,
            False,
        )

    open_conflict = db.scalar(
        select(ConflictRecord.id).where(
            ConflictRecord.patient_id == highlight.patient_id,
            ConflictRecord.status == ConflictStatus.OPEN,
            or_(
                ConflictRecord.authoritative_entry_id == highlight.entry_id,
                ConflictRecord.conflicting_entry_id == highlight.entry_id,
            ),
        ).limit(1)
    ) is not None
    facts = extract_clinical_facts(highlight.source_span)
    structured_fact_match = any(
        fact.entity_type.value == highlight.clinical_entity_type.value for fact in facts
    )

    if open_conflict:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.ABSTAIN,
            "Needs review · Unresolved contradiction affects this source.",
            True,
            True,
            True,
            True,
            structured_fact_match,
            True,
        )
    if facts and not structured_fact_match:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.LOW,
            "Evidence incomplete · Extracted fact does not match the declared entity.",
            True,
            False,
            True,
            True,
            False,
            False,
        )
    if structured_fact_match and highlight.clinician_confirmed:
        reason = "Exact source verified · Structured fact matched · Clinician confirmed."
    elif structured_fact_match:
        reason = "Exact source verified · Structured fact matched · No open conflict."
    elif highlight.clinician_confirmed:
        reason = "Exact source verified · Clinician confirmed · No open conflict."
    else:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.MEDIUM,
            "Exact source verified · Extraction is not structured · No open conflict.",
            False,
            False,
            True,
            True,
            False,
            False,
        )
    return EvidenceConfidence(
        EvidenceConfidenceLevel.HIGH,
        reason,
        False,
        False,
        True,
        True,
        structured_fact_match,
        False,
    )


def highlight_read(
    db: Session, highlight: Highlight, clinic_id: str | None = None
) -> HighlightRead:
    confidence = evaluate_evidence_confidence(db, highlight, clinic_id)
    resolved = resolve_highlight_provenance(db, highlight, clinic_id)
    binding = resolved.binding
    return HighlightRead.model_validate(
        {
            **highlight.__dict__,
            **confidence.__dict__,
            "source_version_number": (
                binding.source_version_number if binding is not None else None
            ),
            "provenance_status": resolved.status,
            "source_changed": resolved.source_changed,
            "version_provenance_pointer": (
                binding.version_provenance_pointer if binding is not None else None
            ),
        }
    )
