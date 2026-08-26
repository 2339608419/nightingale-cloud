from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from app.auth import CurrentUser
from app.models import AuditLog


ALLOWED_TRUST_METADATA_KEYS = {"from_status", "to_status"}


def add_trust_action_audit(
    db: Session,
    *,
    actor: CurrentUser,
    action: str,
    entity_type: str,
    entity_id: str,
    from_status: str,
    to_status: str,
) -> AuditLog:
    """Stage a metadata-only trust action event in the caller's transaction."""
    metadata = {"from_status": from_status, "to_status": to_status}
    if set(metadata) != ALLOWED_TRUST_METADATA_KEYS:
        raise ValueError("Trust audit metadata must contain status fields only")
    event = AuditLog(
        id=str(uuid4()),
        actor_id=actor.user_id,
        actor_role=actor.role.value,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        timestamp=datetime.now(timezone.utc),
        metadata_json=metadata,
    )
    db.add(event)
    return event
