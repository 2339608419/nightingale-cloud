from datetime import datetime, timezone

from app.models import ClinicalEntityType, RiskLevel


RISK_WEIGHTS = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 10,
    RiskLevel.MODERATE: 20,
    RiskLevel.HIGH: 30,
    RiskLevel.CRITICAL: 40,
}

ENTITY_WEIGHTS = {
    ClinicalEntityType.ALLERGY: 20,
    ClinicalEntityType.MEDICATION: 15,
    ClinicalEntityType.RISK: 15,
    ClinicalEntityType.LAB: 12,
    ClinicalEntityType.FOLLOW_UP: 10,
    ClinicalEntityType.CHIEF_COMPLAINT: 10,
}


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def recency_score(source_timestamp: datetime, as_of: datetime) -> int:
    age_days = max(0, (_as_utc(as_of) - _as_utc(source_timestamp)).days)
    if age_days <= 7:
        return 15
    if age_days <= 30:
        return 10
    if age_days <= 180:
        return 5
    return 0


def calculate_importance_score(
    *,
    source_timestamp: datetime,
    risk_level: RiskLevel,
    unresolved_action: bool,
    clinical_entity_type: ClinicalEntityType,
    clinician_confirmed: bool,
    as_of: datetime | None = None,
) -> float:
    """Return an explainable additive importance score on a 0–110 scale."""
    reference_time = as_of or datetime.now(timezone.utc)
    score = RISK_WEIGHTS[risk_level]
    score += recency_score(source_timestamp, reference_time)
    score += 20 if unresolved_action else 0
    score += ENTITY_WEIGHTS[clinical_entity_type]
    score += 15 if clinician_confirmed else 0
    return float(score)

