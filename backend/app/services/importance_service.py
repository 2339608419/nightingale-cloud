from datetime import datetime, timezone
from dataclasses import dataclass

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

RISK_ORDER = {
    RiskLevel.NONE: 0,
    RiskLevel.LOW: 1,
    RiskLevel.MODERATE: 2,
    RiskLevel.HIGH: 3,
    RiskLevel.CRITICAL: 4,
}


@dataclass(frozen=True)
class SafetyFloor:
    rule: str
    minimum_risk: RiskLevel
    minimum_score: float


@dataclass(frozen=True)
class ImportanceEvaluation:
    base_score: float
    learned_adjustment: float
    adjusted_score: float
    safety_floor: float | None
    safety_floor_risk: RiskLevel | None
    safety_floor_rule: str | None
    final_score: float
    final_risk: RiskLevel
    floor_applied: bool


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


def clinical_safety_floor(
    *,
    source_timestamp: datetime,
    unresolved_action: bool,
    clinical_entity_type: ClinicalEntityType,
    context: str,
    as_of: datetime | None = None,
) -> SafetyFloor | None:
    """Return the centralized deterministic floor for the supported demo vocabulary."""
    reference_time = as_of or datetime.now(timezone.utc)
    age_days = max(0, (_as_utc(reference_time) - _as_utc(source_timestamp)).days)
    normalized = context.lower()

    if clinical_entity_type == ClinicalEntityType.ALLERGY:
        return SafetyFloor("allergy", RiskLevel.HIGH, 50.0)

    medication_conflict = (
        clinical_entity_type == ClinicalEntityType.MEDICATION
        and unresolved_action
        and any(
            keyword in normalized
            for keyword in ("conflict", "mismatch", "discrepancy", "different dose")
        )
    )
    if medication_conflict:
        return SafetyFloor("unresolved_medication_dosage_conflict", RiskLevel.HIGH, 65.0)

    medication_change = (
        clinical_entity_type == ClinicalEntityType.MEDICATION
        and (age_days <= 30 or unresolved_action)
        and any(
            keyword in normalized
            for keyword in (
                "dose",
                " mg",
                "increase",
                "decrease",
                "change",
                "started",
                "stopped",
            )
        )
    )
    if medication_change:
        return SafetyFloor("recent_or_unresolved_medication_change", RiskLevel.MODERATE, 35.0)

    if clinical_entity_type == ClinicalEntityType.FOLLOW_UP and unresolved_action:
        return SafetyFloor("unresolved_clinical_follow_up", RiskLevel.MODERATE, 50.0)

    return None


def evaluate_importance(
    *,
    source_timestamp: datetime,
    risk_level: RiskLevel,
    unresolved_action: bool,
    clinical_entity_type: ClinicalEntityType,
    clinician_confirmed: bool,
    learned_adjustment: float,
    context: str,
    as_of: datetime | None = None,
) -> ImportanceEvaluation:
    """Apply base scoring, learned adjustment, then the clinical safety floor."""
    base_score = calculate_importance_score(
        source_timestamp=source_timestamp,
        risk_level=risk_level,
        unresolved_action=unresolved_action,
        clinical_entity_type=clinical_entity_type,
        clinician_confirmed=clinician_confirmed,
        as_of=as_of,
    )
    adjusted_score = base_score + learned_adjustment
    floor = clinical_safety_floor(
        source_timestamp=source_timestamp,
        unresolved_action=unresolved_action,
        clinical_entity_type=clinical_entity_type,
        context=context,
        as_of=as_of,
    )
    final_score = max(adjusted_score, floor.minimum_score) if floor else adjusted_score
    final_risk = risk_level
    if floor and RISK_ORDER[final_risk] < RISK_ORDER[floor.minimum_risk]:
        final_risk = floor.minimum_risk
    floor_applied = bool(
        floor
        and (final_score != adjusted_score or final_risk != risk_level)
    )
    return ImportanceEvaluation(
        base_score=base_score,
        learned_adjustment=learned_adjustment,
        adjusted_score=adjusted_score,
        safety_floor=floor.minimum_score if floor else None,
        safety_floor_risk=floor.minimum_risk if floor else None,
        safety_floor_rule=floor.rule if floor else None,
        final_score=final_score,
        final_risk=final_risk,
        floor_applied=floor_applied,
    )
