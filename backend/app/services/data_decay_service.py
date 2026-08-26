from datetime import datetime, timezone

from app.models import ClinicalEntityType, Highlight, HighlightStatus, TimelineEntry
from app.schemas.data_decay import DataDecayPreviewRead


RECENT_DAYS = 180
DURABLE_ENTITIES = {ClinicalEntityType.ALLERGY, ClinicalEntityType.RISK}
DURABLE_KEYWORDS = ("allergy", "chronic", "major procedure", "hypertension")


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def _summary(content: str, limit: int = 150) -> str:
    normalized = " ".join(content.split())
    first_sentence = normalized.split(". ", 1)[0].rstrip(".") + "."
    if len(first_sentence) <= limit:
        return first_sentence
    return first_sentence[: limit - 1].rstrip() + "…"


def build_decay_preview(
    entries: list[TimelineEntry],
    highlights: list[Highlight],
    *,
    as_of: datetime | None = None,
) -> list[DataDecayPreviewRead]:
    """Build reversible display/storage recommendations without mutating source entries."""
    reference_time = _as_utc(as_of or datetime.now(timezone.utc))
    durable_entry_ids = {
        highlight.entry_id
        for highlight in highlights
        if highlight.status != HighlightStatus.REJECTED
        and highlight.clinical_entity_type in DURABLE_ENTITIES
    }
    results: list[DataDecayPreviewRead] = []
    for entry in entries:
        age_days = max(0, (reference_time - _as_utc(entry.timestamp)).days)
        keyword_durable = any(keyword in entry.content.lower() for keyword in DURABLE_KEYWORDS)
        durable = entry.id in durable_entry_ids or keyword_durable
        if durable:
            tier = "full_detail"
            content = entry.content
            reason = "Clinically durable fact is exempt from decay."
        elif age_days <= RECENT_DAYS:
            tier = "full_detail"
            content = entry.content
            reason = f"Recent entry ({age_days} days old) remains in full detail."
        else:
            tier = "cold_summary"
            content = _summary(entry.content)
            reason = f"Older low-priority entry ({age_days} days old) receives a reversible summary preview."
        results.append(
            DataDecayPreviewRead(
                entry_id=entry.id,
                storage_tier=tier,
                display_content=content,
                original_available=True,
                durable_exempt=durable,
                reason=reason,
                provenance_pointer=entry.provenance_pointer,
            )
        )
    return results
