from datetime import datetime

from pydantic import BaseModel, ConfigDict

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

