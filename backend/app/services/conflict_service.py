import re
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import (
    AuthorRole,
    ConflictEntityType,
    ConflictRecord,
    ConflictStatus,
    TimelineEntry,
    TimelineEntryType,
)
from app.services.audit_service import add_trust_action_audit


AI_ENTRY_TYPES = {
    TimelineEntryType.AI_DOCTOR_CONSULT_SUMMARY,
    TimelineEntryType.AI_NURSE_CONSULT_SUMMARY,
    TimelineEntryType.AI_PATIENT_SESSION_SUMMARY,
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

    for allergen in ALLERGEN_NAMES:
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


def detect_conflicts_for_clinician_entry(
    db: Session, authoritative_entry: TimelineEntry
) -> list[ConflictRecord]:
    if authoritative_entry.author_role != AuthorRole.CLINICIAN:
        return []
    authoritative_facts = extract_clinical_facts(authoritative_entry.content)
    if not authoritative_facts:
        return []

    source_entries = list(
        db.scalars(
            select(TimelineEntry)
            .where(
                TimelineEntry.patient_id == authoritative_entry.patient_id,
                TimelineEntry.id != authoritative_entry.id,
                (
                    TimelineEntry.type.in_(AI_ENTRY_TYPES)
                    | (TimelineEntry.author_role == AuthorRole.PATIENT)
                ),
            )
            .order_by(TimelineEntry.timestamp.desc(), TimelineEntry.id)
        )
    )
    created: list[ConflictRecord] = []
    for source in source_entries:
        prior_by_key = {
            (fact.entity_type, fact.entity_name): fact for fact in extract_clinical_facts(source.content)
        }
        for authoritative in authoritative_facts:
            prior = prior_by_key.get((authoritative.entity_type, authoritative.entity_name))
            if prior is None or prior.value == authoritative.value:
                continue
            exists = db.scalar(
                select(ConflictRecord).where(
                    ConflictRecord.authoritative_entry_id == authoritative_entry.id,
                    ConflictRecord.conflicting_entry_id == source.id,
                    ConflictRecord.entity_type == authoritative.entity_type,
                    ConflictRecord.entity_name == authoritative.entity_name,
                    ConflictRecord.prior_value == prior.value,
                    ConflictRecord.authoritative_value == authoritative.value,
                )
            )
            if exists is not None:
                continue
            conflict = ConflictRecord(
                id=str(uuid4()),
                patient_id=authoritative_entry.patient_id,
                authoritative_entry_id=authoritative_entry.id,
                conflicting_entry_id=source.id,
                entity_type=authoritative.entity_type,
                entity_name=authoritative.entity_name,
                prior_value=prior.value,
                authoritative_value=authoritative.value,
                status=ConflictStatus.OPEN,
                created_at=datetime.now(timezone.utc),
                resolved_at=None,
            )
            db.add(conflict)
            created.append(conflict)
    db.commit()
    for conflict in created:
        db.refresh(conflict)
    return created


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
