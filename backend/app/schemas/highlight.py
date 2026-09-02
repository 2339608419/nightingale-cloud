from datetime import datetime

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from app.models.highlight import (
    ClinicalEntityType,
    EvidenceConfidenceLevel,
    HighlightStatus,
    RiskLevel,
)


class ProvenanceStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    BROKEN = "broken"


class HighlightRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    entry_id: str
    source_span: str
    text: str
    importance_score: float
    risk_level: RiskLevel
    risk_reason: str
    status: HighlightStatus
    provenance_pointer: str
    created_at: datetime
    clinician_confirmed: bool
    unresolved_action: bool
    clinical_entity_type: ClinicalEntityType
    evidence_confidence_level: EvidenceConfidenceLevel
    confidence_reason: str
    requires_review: bool
    abstained: bool
    provenance_resolved: bool
    source_span_verified: bool
    structured_fact_match: bool
    open_conflict: bool
    source_version_number: int | None
    provenance_status: ProvenanceStatus
    source_changed: bool
    version_provenance_pointer: str | None
    confidence_inputs_evaluated: list[str]
    confidence_rule_triggered: str
    confidence_required_action: str


class HighlightSuggestionCreate(BaseModel):
    source_span: str = Field(min_length=1, max_length=2000)
    text: str = Field(min_length=1, max_length=300)
    risk_level: RiskLevel
    risk_reason: str = Field(min_length=1, max_length=500)
    unresolved_action: bool = False
    clinical_entity_type: ClinicalEntityType
    expected_source_version: int | None = Field(default=None, ge=1)


class HighlightSourceSnapshotRead(BaseModel):
    highlight_id: str
    entry_id: str
    source_version_number: int
    version_provenance_pointer: str
    provenance_status: ProvenanceStatus
    source_changed: bool
    content: str
    source_span: str
    source_span_verified: bool
    created_at: datetime


class HighlightSuggestionRead(BaseModel):
    highlight: HighlightRead
    base_score: float
    learned_bonus: float
    learned_adjustment: float
    adjusted_score: float
    safety_floor: float | None
    safety_floor_risk: RiskLevel | None
    safety_floor_rule: str | None
    final_score: float
    floor_applied: bool
    explanation: list[str]


class ImportancePreferenceRead(BaseModel):
    category_type: str
    category_value: str
    accepted_count: int
    rejected_count: int
    weight: float
    explanation: str
    negative_feedback_state: str = "legacy_aggregate"
