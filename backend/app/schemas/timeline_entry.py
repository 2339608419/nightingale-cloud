from datetime import datetime

from pydantic import BaseModel, ConfigDict

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
