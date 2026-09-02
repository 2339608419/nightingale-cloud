import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    AuthorRole,
    ClinicalEntityType,
    ConflictAuthorityPolicy,
    ConflictEntityType,
    ConflictProvenance,
    ConflictRecord,
    ConflictStatus,
    EntryVersion,
    Highlight,
    HighlightStatus,
    RiskLevel,
    TimelineEntry,
    TimelineEntryType,
)
from app.services.audit_service import add_trust_action_audit
from app.services.highlight_provenance_service import bind_highlight_to_current_version, version_pointer


AI_ENTRY_TYPES = {
    TimelineEntryType.AI_DOCTOR_CONSULT_SUMMARY,
    TimelineEntryType.AI_NURSE_CONSULT_SUMMARY,
    TimelineEntryType.AI_PATIENT_SESSION_SUMMARY,
}
HUMAN_ENTRY_TYPES = {
    TimelineEntryType.CLINICIAN_NOTE,
    TimelineEntryType.STAFF_NOTE,
    TimelineEntryType.INSTRUCTION,
}
MEDICATION_NAMES = ("lisinopril", "amlodipine", "metformin")
ALLERGEN_NAMES = ("penicillin", "sulfa")
DOSE_PATTERN = re.compile(
    r"\b(\d+(?:\.\d+)?)\s*mg\b(?:\s+(once daily|twice daily|daily|at night))?",
    re.IGNORECASE,
)
FOLLOW_UP_PATTERN = re.compile(
    r"\b(?:(nurse|clinician|staff)\s+)?follow-up\b.{0,45}?"
    r"\b(unresolved|pending|open|resolved|completed|complete)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class ExtractedFact:
    entity_type: ConflictEntityType
    entity_name: str
    value: str


def extract_clinical_facts(content: str) -> list[ExtractedFact]:
    """Extract only the small, deterministic vocabulary used by the synthetic demo."""
    lowered = content.lower()
    facts: list[ExtractedFact] = []

    for medication in MEDICATION_NAMES:
        start = lowered.find(medication)
        if start < 0:
            continue
        sentence_end = lowered.find(".", start)
        window = content[start : sentence_end if sentence_end >= 0 else start + 120]
        doses = list(DOSE_PATTERN.finditer(window))
        if doses:
            dose = doses[-1]
            frequency = (dose.group(2) or "").lower()
            value = f"{dose.group(1)} mg" + (f" {frequency}" if frequency else "")
            facts.append(ExtractedFact(ConflictEntityType.MEDICATION, medication, value))

    general_no_allergy = re.search(r"\b(no known allergies|no known allergy|denies (?:any )?allergies)\b", lowered)
    for allergen in ALLERGEN_NAMES:
        if general_no_allergy:
            facts.append(ExtractedFact(ConflictEntityType.ALLERGY, allergen, "none"))
            continue
        if allergen not in lowered or "allerg" not in lowered:
            continue
        context_start = max(0, lowered.find(allergen) - 20)
        context = lowered[context_start : lowered.find(allergen) + 60]
        if re.search(r"\b(no|denies|without)\b.{0,25}\ballerg", context):
            value = "none"
        elif re.search(r"\b(resolved|inactive)\b", context):
            value = "resolved"
        else:
            value = "active"
        facts.append(ExtractedFact(ConflictEntityType.ALLERGY, allergen, value))

    for match in FOLLOW_UP_PATTERN.finditer(content):
        owner = (match.group(1) or "general").lower()
        raw_status = match.group(2).lower()
        value = "resolved" if raw_status in {"resolved", "completed", "complete"} else "unresolved"
        facts.append(
            ExtractedFact(ConflictEntityType.FOLLOW_UP, f"{owner} follow-up", value)
        )

    return facts


def get_patient_conflicts(
    db: Session, patient_id: str, conflict_status: ConflictStatus | None = None
) -> list[ConflictRecord]:
    statement = select(ConflictRecord).where(ConflictRecord.patient_id == patient_id)
    if conflict_status is not None:
        statement = statement.where(ConflictRecord.status == conflict_status)
    return list(db.scalars(statement.order_by(ConflictRecord.created_at.desc(), ConflictRecord.id)))


def _authority_rank(entry: TimelineEntry) -> int:
    if entry.author_role == AuthorRole.CLINICIAN:
        return 3
    if entry.author_role == AuthorRole.STAFF:
        return 2
    return 1


def conflict_authority_policy(
    authoritative_entry: TimelineEntry, conflicting_entry: TimelineEntry
) -> ConflictAuthorityPolicy:
    if _authority_rank(authoritative_entry) == _authority_rank(conflicting_entry):
        return ConflictAuthorityPolicy.CLINICIAN_REVIEW_REQUIRED
    if authoritative_entry.author_role == AuthorRole.CLINICIAN:
        return ConflictAuthorityPolicy.CLINICIAN_AUTHORITATIVE
    if authoritative_entry.author_role == AuthorRole.STAFF:
        return ConflictAuthorityPolicy.STAFF_AUTHORITATIVE
    return ConflictAuthorityPolicy.CLINICIAN_REVIEW_REQUIRED


def detect_conflicts_for_entry(
    db: Session, changed_entry: TimelineEntry
) -> list[ConflictRecord]:
    """Compare a new deterministic fact against retained human, AI, and patient evidence."""
    changed_facts = extract_clinical_facts(changed_entry.content)
    if not changed_facts:
        return []

    source_entries = list(
        db.scalars(
            select(TimelineEntry)
            .where(
                TimelineEntry.patient_id == changed_entry.patient_id,
                TimelineEntry.id != changed_entry.id,
                (
                    TimelineEntry.type.in_(AI_ENTRY_TYPES)
                    | TimelineEntry.type.in_(HUMAN_ENTRY_TYPES)
                    | TimelineEntry.author_role.in_(
                        {AuthorRole.PATIENT, AuthorRole.STAFF, AuthorRole.CLINICIAN}
                    )
                ),
            )
            .order_by(TimelineEntry.timestamp.desc(), TimelineEntry.id)
        )
    )
    created: list[ConflictRecord] = []
    batch_started_at = datetime.now(timezone.utc)
    # Create oldest-source records first so the existing newest-first conflict feed
    # presents the most recent contradictory evidence first.
    for source in reversed(source_entries):
        prior_by_key = {
            (fact.entity_type, fact.entity_name): fact for fact in extract_clinical_facts(source.content)
        }
        for changed_fact in changed_facts:
            prior = prior_by_key.get((changed_fact.entity_type, changed_fact.entity_name))
            if prior is None or prior.value == changed_fact.value:
                continue
            changed_is_authoritative = _authority_rank(changed_entry) >= _authority_rank(source)
            authoritative_entry = changed_entry if changed_is_authoritative else source
            conflicting_entry = source if changed_is_authoritative else changed_entry
            authoritative_value = changed_fact.value if changed_is_authoritative else prior.value
            conflicting_value = prior.value if changed_is_authoritative else changed_fact.value
            exists = db.scalar(
                select(ConflictRecord).where(
                    ConflictRecord.authoritative_entry_id == authoritative_entry.id,
                    ConflictRecord.conflicting_entry_id == conflicting_entry.id,
                    ConflictRecord.entity_type == changed_fact.entity_type,
                    ConflictRecord.entity_name == changed_fact.entity_name,
                    ConflictRecord.prior_value == conflicting_value,
                    ConflictRecord.authoritative_value == authoritative_value,
                )
            )
            if exists is not None:
                continue
            conflict = ConflictRecord(
                id=str(uuid4()),
                patient_id=changed_entry.patient_id,
                authoritative_entry_id=authoritative_entry.id,
                conflicting_entry_id=conflicting_entry.id,
                entity_type=changed_fact.entity_type,
                entity_name=changed_fact.entity_name,
                prior_value=conflicting_value,
                authoritative_value=authoritative_value,
                status=ConflictStatus.OPEN,
                created_at=batch_started_at + timedelta(microseconds=len(created) + 1),
                resolved_at=None,
            )
            db.add(conflict)
            db.flush()
            authoritative_version = db.scalar(
                select(EntryVersion.version_number)
                .where(EntryVersion.entry_id == authoritative_entry.id)
                .order_by(EntryVersion.version_number.desc()).limit(1)
            )
            conflicting_version = db.scalar(
                select(EntryVersion.version_number)
                .where(EntryVersion.entry_id == conflicting_entry.id)
                .order_by(EntryVersion.version_number.desc()).limit(1)
            )
            if authoritative_version is not None and conflicting_version is not None:
                db.add(ConflictProvenance(
                    conflict_id=conflict.id,
                    authoritative_version_number=authoritative_version,
                    conflicting_version_number=conflicting_version,
                    authoritative_version_pointer=version_pointer(authoritative_entry.id, authoritative_version),
                    conflicting_version_pointer=version_pointer(conflicting_entry.id, conflicting_version),
                    created_at=batch_started_at,
                ))
            if changed_fact.entity_type == ConflictEntityType.ALLERGY:
                existing_highlight = db.scalar(select(Highlight).where(
                    Highlight.patient_id == changed_entry.patient_id,
                    Highlight.entry_id == authoritative_entry.id,
                    Highlight.clinical_entity_type == ClinicalEntityType.ALLERGY,
                    Highlight.status != HighlightStatus.REJECTED,
                ))
                if existing_highlight is None:
                    existing_highlight = Highlight(
                        id=str(uuid4()), patient_id=changed_entry.patient_id,
                        entry_id=authoritative_entry.id,
                        source_span=authoritative_entry.content,
                        text="Allergy contradiction requires clinician review",
                        importance_score=65.0, risk_level=RiskLevel.HIGH,
                        risk_reason="Contradictory allergy evidence requires clinician review.",
                        status=HighlightStatus.SUGGESTED,
                        provenance_pointer="pending-immutable-binding",
                        created_at=batch_started_at,
                        clinician_confirmed=False, unresolved_action=True,
                        clinical_entity_type=ClinicalEntityType.ALLERGY,
                    )
                    db.add(existing_highlight)
                    db.flush()
                    bind_highlight_to_current_version(
                        db, highlight=existing_highlight, entry=authoritative_entry,
                        source_span=authoritative_entry.content,
                        expected_source_version=None,
                    )
            created.append(conflict)
    db.commit()
    for conflict in created:
        db.refresh(conflict)
    return created


def detect_conflicts_for_clinician_entry(
    db: Session, authoritative_entry: TimelineEntry
) -> list[ConflictRecord]:
    """Backward-compatible entry point retained for existing integrations."""
    if authoritative_entry.author_role != AuthorRole.CLINICIAN:
        return []
    return detect_conflicts_for_entry(db, authoritative_entry)


def resolve_conflict(
    db: Session, conflict: ConflictRecord, actor: CurrentUser
) -> ConflictRecord:
    if conflict.status == ConflictStatus.RESOLVED:
        return conflict
    previous_status = conflict.status
    conflict.status = ConflictStatus.RESOLVED
    conflict.resolved_at = datetime.now(timezone.utc)
    add_trust_action_audit(
        db,
        actor=actor,
        action="conflict.resolved",
        entity_type="conflict_record",
        entity_id=conflict.id,
        from_status=previous_status.value,
        to_status=ConflictStatus.RESOLVED.value,
    )
    db.commit()
    db.refresh(conflict)
    return conflict
