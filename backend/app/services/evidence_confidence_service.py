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
    confidence_inputs_evaluated: list[str]
    confidence_rule_triggered: str
    confidence_required_action: str


def evaluate_evidence_confidence(
    db: Session, highlight: Highlight, clinic_id: str | None = None
) -> EvidenceConfidence:
    """Answer whether immutable cited evidence verifies the Highlight; never clinical truth."""
    try:
        return _evaluate_evidence_confidence(db, highlight, clinic_id)
    except Exception:
        # Corrupt/invariant-breaking evidence must never leave a stale trusted label.
        return EvidenceConfidence(
            EvidenceConfidenceLevel.ABSTAIN,
            "Needs review · Evidence evaluation could not be completed safely.",
            True, True, False, False, False, False,
            ["immutable_source", "version_pointer", "exact_span", "structured_entity", "conflict", "human_confirmation", "source_currency"],
            "evaluation_failed_closed",
            "clinician_review",
        )


def _evaluate_evidence_confidence(
    db: Session, highlight: Highlight, clinic_id: str | None = None
) -> EvidenceConfidence:
    inputs = [
        "immutable_source", "version_pointer", "exact_span", "structured_entity",
        "conflict", "human_confirmation", "source_currency",
    ]
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
            True, True, False, False, False, False,
            inputs, "source_missing", "clinician_review",
        )
    if not provenance_resolved:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.ABSTAIN,
            "Needs review · Provenance pointer does not resolve to the source entry.",
            True, True, False, source_span_verified, False, False,
            inputs, "version_pointer_unresolved", "clinician_review",
        )
    if not source_span_verified:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.ABSTAIN,
            "Needs review · Exact source span cannot be verified.",
            True, True, True, False, False, False,
            inputs, "exact_span_missing", "clinician_review",
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
            True, True, True, True, structured_fact_match, True,
            inputs, "unresolved_conflict", "resolve_conflict_before_trust",
        )
    if facts and not structured_fact_match:
        return EvidenceConfidence(
            EvidenceConfidenceLevel.LOW,
            "Evidence incomplete · Extracted fact does not match the declared entity.",
            True, False, True, True, False, False,
            inputs, "structured_entity_mismatch", "clinician_review",
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
            False, False, True, True, False, False,
            inputs, "exact_evidence_unstructured", "review_if_used_clinically",
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
        inputs,
        (
            "exact_structured_evidence_confirmed"
            if structured_fact_match and highlight.clinician_confirmed
            else "exact_evidence_human_confirmed"
            if highlight.clinician_confirmed
            else "exact_structured_evidence"
        ),
        "review_source_currency" if resolved.source_changed else "none",
    )


def highlight_read(
    db: Session, highlight: Highlight, clinic_id: str | None = None
) -> HighlightRead:
    confidence = evaluate_evidence_confidence(db, highlight, clinic_id)
    try:
        resolved = resolve_highlight_provenance(db, highlight, clinic_id)
        binding = resolved.binding
        provenance_status = resolved.status
        source_changed = resolved.source_changed
    except Exception:
        binding = None
        provenance_status = "broken"
        source_changed = False
    return HighlightRead.model_validate(
        {
            **highlight.__dict__,
            **confidence.__dict__,
            "source_version_number": (
                binding.source_version_number if binding is not None else None
            ),
            "provenance_status": provenance_status,
            "source_changed": source_changed,
            "version_provenance_pointer": (
                binding.version_provenance_pointer if binding is not None else None
            ),
        }
    )
