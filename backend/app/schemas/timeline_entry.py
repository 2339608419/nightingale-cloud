from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.timeline_entry import AuthorRole, TimelineEntryType


class TimelineEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    author_role: AuthorRole
    author_id: str
    timestamp: datetime
    type: TimelineEntryType
    content: str
    provenance_pointer: str | None
    version: int
    patient_facing_status: str | None
    approved_by: str | None
    approved_at: datetime | None
    approved_version_number: int | None
    ai_derived: bool
    source_entry_id: str | None


class TimelineEntryCreate(BaseModel):
    type: TimelineEntryType
    content: str = Field(min_length=1, max_length=10000)
    provenance_pointer: str | None = Field(default=None, max_length=500)
    ai_derived: bool = False
    source_entry_id: str | None = Field(default=None, max_length=36)

    @model_validator(mode="after")
    def validate_ai_derived_instruction(self) -> "TimelineEntryCreate":
        if self.ai_derived and self.type != TimelineEntryType.INSTRUCTION:
            raise ValueError("AI-derived patient-facing content must be an instruction")
        if self.ai_derived and not self.source_entry_id:
            raise ValueError("AI-derived patient-facing instructions require a source entry")
        if self.source_entry_id and not self.ai_derived:
            raise ValueError("source_entry_id is only valid for AI-derived instructions")
        return self


class TimelineEntryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    provenance_pointer: str | None = Field(default=None, max_length=500)
    expected_version: int = Field(ge=1)
