from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import AuthorRole, ConflictAuthorityPolicy, ConflictEntityType, ConflictStatus


class ConflictRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    patient_id: str
    authoritative_entry_id: str
    conflicting_entry_id: str
    entity_type: ConflictEntityType
    entity_name: str
    prior_value: str
    authoritative_value: str
    status: ConflictStatus
    created_at: datetime
    resolved_at: datetime | None
    authoritative_provenance_pointer: str
    conflicting_provenance_pointer: str
    authoritative_role: AuthorRole
    conflicting_role: AuthorRole
    authority_policy: ConflictAuthorityPolicy
    requires_clinician_review: bool
    unresolved_requires_review: bool
    authoritative_version_number: int | None = None
    conflicting_version_number: int | None = None
    authoritative_version_pointer: str | None = None
    conflicting_version_pointer: str | None = None
