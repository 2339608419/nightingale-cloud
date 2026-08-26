from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

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


class TimelineEntryCreate(BaseModel):
    type: TimelineEntryType
    content: str = Field(min_length=1, max_length=10000)
    provenance_pointer: str | None = Field(default=None, max_length=500)


class TimelineEntryUpdate(BaseModel):
    content: str = Field(min_length=1, max_length=10000)
    provenance_pointer: str | None = Field(default=None, max_length=500)
    expected_version: int = Field(ge=1)
