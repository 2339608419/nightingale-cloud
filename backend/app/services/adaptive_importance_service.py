from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import ClinicalEntityType, ImportancePreference, TimelineEntryType


ACCEPT_WEIGHTS = {"entity": 5.0, "entry_type": 2.0}
REJECT_WEIGHTS = {"entity": 2.0, "entry_type": 1.0}
MIN_TOTAL_BONUS = -10.0
MAX_TOTAL_BONUS = 25.0


def preference_weight(preference: ImportancePreference) -> float:
    return (
        preference.accepted_count * ACCEPT_WEIGHTS[preference.category_type]
        - preference.rejected_count * REJECT_WEIGHTS[preference.category_type]
    )


def get_preferences(db: Session, clinic_id: str) -> list[ImportancePreference]:
    return list(
        db.scalars(
            select(ImportancePreference)
            .where(ImportancePreference.clinic_id == clinic_id)
            .order_by(ImportancePreference.category_type, ImportancePreference.category_value)
        )
    )


def learned_bonus(
    db: Session,
    *,
    clinic_id: str,
    entity_type: ClinicalEntityType,
    entry_type: TimelineEntryType,
) -> tuple[float, list[str]]:
    preferences = get_preferences(db, clinic_id)
    keys = {("entity", entity_type.value), ("entry_type", entry_type.value)}
    matched = [item for item in preferences if (item.category_type, item.category_value) in keys]
    raw_bonus = sum(preference_weight(item) for item in matched)
    bonus = max(MIN_TOTAL_BONUS, min(MAX_TOTAL_BONUS, raw_bonus))
    explanation = [
        f"{item.category_type}:{item.category_value} {preference_weight(item):+.1f} "
        f"({item.accepted_count} accepted, {item.rejected_count} rejected)"
        for item in matched
    ]
    if not explanation:
        explanation = ["No learned preference yet"]
    if bonus != raw_bonus:
        explanation.append(f"Total learned bonus capped at {bonus:+.1f}")
    return bonus, explanation


def _get_or_create(
    db: Session, *, clinic_id: str, category_type: str, category_value: str
) -> ImportancePreference:
    preference = db.scalar(
        select(ImportancePreference).where(
            ImportancePreference.clinic_id == clinic_id,
            ImportancePreference.category_type == category_type,
            ImportancePreference.category_value == category_value,
        )
    )
    if preference is None:
        preference = ImportancePreference(
            id=str(uuid4()),
            clinic_id=clinic_id,
            category_type=category_type,
            category_value=category_value,
            accepted_count=0,
            rejected_count=0,
            updated_at=datetime.now(timezone.utc),
        )
        db.add(preference)
    return preference


def record_feedback(
    db: Session,
    *,
    clinic_id: str,
    entity_type: ClinicalEntityType,
    entry_type: TimelineEntryType,
    previous_status: str,
    new_status: str,
) -> None:
    if previous_status == new_status:
        return
    for category_type, category_value in (
        ("entity", entity_type.value),
        ("entry_type", entry_type.value),
    ):
        preference = _get_or_create(
            db,
            clinic_id=clinic_id,
            category_type=category_type,
            category_value=category_value,
        )
        if previous_status == "accepted":
            preference.accepted_count = max(0, preference.accepted_count - 1)
        elif previous_status == "rejected":
            preference.rejected_count = max(0, preference.rejected_count - 1)
        if new_status == "accepted":
            preference.accepted_count += 1
        elif new_status == "rejected":
            preference.rejected_count += 1
        preference.updated_at = datetime.now(timezone.utc)
