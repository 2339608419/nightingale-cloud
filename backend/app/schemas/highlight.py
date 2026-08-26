from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.highlight import ClinicalEntityType, HighlightStatus, RiskLevel


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


class HighlightSuggestionCreate(BaseModel):
    source_span: str = Field(min_length=1, max_length=2000)
    text: str = Field(min_length=1, max_length=300)
    risk_level: RiskLevel
    risk_reason: str = Field(min_length=1, max_length=500)
    unresolved_action: bool = False
    clinical_entity_type: ClinicalEntityType


class HighlightSuggestionRead(BaseModel):
    highlight: HighlightRead
    base_score: float
    learned_bonus: float
    explanation: list[str]


class ImportancePreferenceRead(BaseModel):
    category_type: str
    category_value: str
    accepted_count: int
    rejected_count: int
    weight: float
    explanation: str
