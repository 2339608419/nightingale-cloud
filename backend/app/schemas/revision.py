from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class EntryVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    entry_id: str
    version_number: int
    content: str
    provenance_pointer: str | None
    changed_by: str
    changed_by_role: str
    created_at: datetime


class RevertRequest(BaseModel):
    expected_version: int = Field(ge=1)


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    actor_id: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    timestamp: datetime
    metadata: dict[str, Any] = Field(validation_alias="metadata_json")
