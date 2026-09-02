from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import EntryVersion, Highlight, HighlightProvenance, TimelineEntry
from app.schemas.highlight import ProvenanceStatus
from app.services.revision_service import ensure_initial_version, get_versions
from app.services.clinic_scope_service import get_entry_in_clinic, get_entry_version_in_clinic


class HighlightSourceVersionConflict(Exception):
    def __init__(self, current_version: int) -> None:
        self.current_version = current_version


@dataclass(frozen=True)
class ResolvedHighlightProvenance:
    binding: HighlightProvenance | None
    snapshot: EntryVersion | None
    status: ProvenanceStatus
    source_changed: bool
    source_span_verified: bool


def version_pointer(entry_id: str, version_number: int) -> str:
    return f"timeline-entry-version-{entry_id}-v{version_number}"


def bind_highlight_to_current_version(
    db: Session,
    *,
    highlight: Highlight,
    entry: TimelineEntry,
    source_span: str,
    expected_source_version: int | None,
) -> HighlightProvenance:
    ensure_initial_version(db, entry)
    versions = get_versions(db, entry.id)
    current = versions[0]
    if expected_source_version is not None and expected_source_version != current.version_number:
        raise HighlightSourceVersionConflict(current.version_number)
    if source_span not in current.content:
        raise ValueError("Source span must occur in the immutable source version")
    binding = HighlightProvenance(
        highlight_id=highlight.id,
        entry_id=entry.id,
        source_version_number=current.version_number,
        source_span=source_span,
        version_provenance_pointer=version_pointer(entry.id, current.version_number),
        created_at=datetime.now(timezone.utc),
    )
    highlight.provenance_pointer = binding.version_provenance_pointer
    db.add(binding)
    return binding


def resolve_highlight_provenance(
    db: Session, highlight: Highlight, clinic_id: str | None = None
) -> ResolvedHighlightProvenance:
    binding = db.get(HighlightProvenance, highlight.id)
    if binding is None or binding.entry_id != highlight.entry_id:
        return ResolvedHighlightProvenance(
            binding, None, ProvenanceStatus.BROKEN, False, False
        )
    snapshot = (
        get_entry_version_in_clinic(
            db, binding.entry_id, binding.source_version_number, clinic_id
        )
        if clinic_id is not None
        else db.scalar(
            select(EntryVersion).where(
                EntryVersion.entry_id == binding.entry_id,
                EntryVersion.version_number == binding.source_version_number,
            )
        )
    )
    entry = (
        get_entry_in_clinic(db, binding.entry_id, clinic_id)
        if clinic_id is not None
        else db.get(TimelineEntry, binding.entry_id)
    )
    if (
        snapshot is None
        or entry is None
        or highlight.provenance_pointer != binding.version_provenance_pointer
        or binding.version_provenance_pointer
        != version_pointer(binding.entry_id, binding.source_version_number)
    ):
        return ResolvedHighlightProvenance(
            binding, snapshot, ProvenanceStatus.BROKEN, False, False
        )
    span_verified = (
        binding.source_span == highlight.source_span
        and binding.source_span in snapshot.content
    )
    if not span_verified:
        return ResolvedHighlightProvenance(
            binding, snapshot, ProvenanceStatus.BROKEN, False, False
        )
    current_version = max((item.version_number for item in entry.versions), default=1)
    changed = current_version != binding.source_version_number
    return ResolvedHighlightProvenance(
        binding,
        snapshot,
        ProvenanceStatus.STALE if changed else ProvenanceStatus.CURRENT,
        changed,
        True,
    )


def backfill_synthetic_highlight_provenance(db: Session) -> None:
    """Bind only unambiguous exact snapshots; ambiguous/missing evidence stays broken."""
    for highlight in db.scalars(select(Highlight)):
        if db.get(HighlightProvenance, highlight.id) is not None:
            continue
        matches = [
            version
            for version in get_versions(db, highlight.entry_id)
            if highlight.source_span in version.content
        ]
        if len(matches) != 1:
            continue
        snapshot = matches[0]
        binding = HighlightProvenance(
            highlight_id=highlight.id,
            entry_id=highlight.entry_id,
            source_version_number=snapshot.version_number,
            source_span=highlight.source_span,
            version_provenance_pointer=version_pointer(
                highlight.entry_id, snapshot.version_number
            ),
            created_at=highlight.created_at,
        )
        highlight.provenance_pointer = binding.version_provenance_pointer
        db.add(binding)
