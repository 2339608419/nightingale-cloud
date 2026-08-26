from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TimelineEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    author_role: str
    author_id: str
    timestamp: datetime
    type: str
    content: str
    provenance_pointer: str | None

