from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Highlight, HighlightStatus, Patient


GLANCE_LIMIT = 5


def get_patient_highlights(db: Session, patient_id: str) -> list[Highlight] | None:
    if db.get(Patient, patient_id) is None:
        return None
    statement = (
        select(Highlight)
        .where(
            Highlight.patient_id == patient_id,
            Highlight.status != HighlightStatus.REJECTED,
        )
        .order_by(
            Highlight.importance_score.desc(),
            Highlight.created_at.desc(),
            Highlight.id.desc(),
        )
        .limit(GLANCE_LIMIT)
    )
    return list(db.scalars(statement))

