from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.timeline_entry import TimelineEntryRead


class InteractionType(str, Enum):
    DOCTOR_CONSULT = "doctor_consult"
    NURSE_CONSULT = "nurse_consult"
    PATIENT_SESSION = "patient_session"


class AiScribeRequest(BaseModel):
    patient_id: str = Field(min_length=1, max_length=36)
    interaction_type: InteractionType
    source_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
    transcript: str = Field(min_length=1, max_length=50000)
    synthetic: Literal[True]


class RedactionMetadata(BaseModel):
    original_character_count: int
    redacted_character_count: int
    names_redacted: int
    ids_redacted: int
    phones_redacted: int
    total_redactions: int


class RedactionValidationMetadata(BaseModel):
    passed: bool
    detected_redactions: int
    remaining_phi_patterns: list[str]
    protected_terms_preserved: bool
    missing_protected_terms: list[str]
    output_integrity_valid: bool
    reason: str


class AiScribeResponse(BaseModel):
    status: Literal["created", "withheld"]
    outcome: Literal[
        "success",
        "redaction_withheld",
        "provider_timeout",
        "provider_unavailable",
        "invalid_provider_response",
    ]
    message: str
    provider: str
    generation_mode: Literal["external_model", "rule_derived_mock", "test_double"]
    safe_abstention: bool
    redaction: RedactionMetadata
    validation: RedactionValidationMetadata
    generated_summary: str | None
    timeline_entry: TimelineEntryRead | None
    provenance_pointer: str | None
