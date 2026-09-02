from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.consult import CaptureState, ConsultMode, ConsultState, SegmentState, SummaryAudience
from app.schemas.timeline_entry import TimelineEntryRead


SUPPORTED_LANGUAGES = {"english", "malay", "hokkien", "mandarin", "tamil"}


class ConsultSessionCreate(BaseModel):
    patient_id: str
    synthetic: Literal[True]
    mode: Literal["synthetic_text_stream"] = "synthetic_text_stream"
    noise_profile: Literal["simulated_clinic_noise", "simulated_quiet"] = "simulated_clinic_noise"


class ConsultSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    clinic_id: str
    patient_id: str
    mode: ConsultMode
    state: ConsultState
    synthetic: bool
    noise_profile: str
    generation_mode: str
    provider_status: str
    started_at: datetime
    finalized_at: datetime | None


class LanguageSpan(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(gt=0)
    language: str


class TranscriptSegmentContent(BaseModel):
    original_synthetic_text: str = Field(min_length=1, max_length=4000)
    language_spans: list[LanguageSpan]
    capture_uncertainty: str | None = Field(default=None, max_length=60)
    alternatives: list[Annotated[str, Field(min_length=1, max_length=160)]] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_content_ranges(self):
        if not self.language_spans:
            raise ValueError("language_spans are required")
        text_length = len(self.original_synthetic_text)
        previous_end = 0
        for span in self.language_spans:
            if span.end > text_length or span.start < previous_end or span.end <= span.start:
                raise ValueError("language spans must be ordered, non-overlapping, and inside the text")
            previous_end = span.end
        return self


class TranscriptSegmentCreate(TranscriptSegmentContent):
    sequence_number: int = Field(ge=1)
    start_offset_ms: int = Field(ge=0)
    end_offset_ms: int = Field(gt=0)
    speaker: Literal["patient", "clinician", "staff"]
    state: Literal["partial", "final"]

    @model_validator(mode="after")
    def validate_offsets(self):
        if self.end_offset_ms <= self.start_offset_ms:
            raise ValueError("end_offset_ms must be greater than start_offset_ms")
        return self


class TranscriptSegmentCorrect(TranscriptSegmentContent):
    pass


class TranscriptSegmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    session_id: str
    sequence_number: int
    version_number: int
    start_offset_ms: int
    end_offset_ms: int
    speaker: str
    original_synthetic_text: str
    language_spans: list
    state: SegmentState
    capture_uncertainty: str | None
    alternatives: list
    correction_status: str
    is_current: bool
    provenance_pointer: str
    created_at: datetime


class SafetySignalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    session_id: str
    segment_id: str
    segment_version_number: int
    entity_type: str
    status: str
    risk_level: str
    provenance_pointer: str
    source_offset_ms: int
    created_at: datetime


class ClinicalCaptureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    session_id: str
    segment_id: str
    segment_version_number: int
    captured_term: str
    exact_source_phrase: str
    candidate_values: list
    state: CaptureState
    reference_title: str | None
    reference_source_id: str | None
    reference_scope: str | None
    confirmed_value: str | None
    confirmed_by: str | None
    confirmed_at: datetime | None
    provenance_pointer: str
    created_at: datetime


class ClinicalCaptureConfirm(BaseModel):
    selected_value: str = Field(min_length=1, max_length=80)


class ConsultSummaryRead(BaseModel):
    id: str
    session_id: str
    audience: SummaryAudience
    generation_mode: str
    source_provenance: list
    source_status: str
    timeline_entry: TimelineEntryRead
