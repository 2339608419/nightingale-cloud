from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class RiskLevel(str, Enum):
    NONE = "none"
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"


class HighlightStatus(str, Enum):
    SUGGESTED = "suggested"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ClinicalEntityType(str, Enum):
    ALLERGY = "allergy"
    MEDICATION = "medication"
    CHIEF_COMPLAINT = "chief_complaint"
    FOLLOW_UP = "follow_up"
    LAB = "lab"
    RISK = "risk"


class Highlight(Base):
    __tablename__ = "highlights"
    __table_args__ = (
        Index("ix_highlights_patient_status_score", "patient_id", "status", "importance_score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source_span: Mapped[str] = mapped_column(Text, nullable=False)
    text: Mapped[str] = mapped_column(String(300), nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[RiskLevel] = mapped_column(
        SqlEnum(
            RiskLevel,
            values_callable=lambda levels: [level.value for level in levels],
            native_enum=False,
            create_constraint=True,
            name="highlight_risk_level",
        ),
        nullable=False,
    )
    risk_reason: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[HighlightStatus] = mapped_column(
        SqlEnum(
            HighlightStatus,
            values_callable=lambda statuses: [status.value for status in statuses],
            native_enum=False,
            create_constraint=True,
            name="highlight_status",
        ),
        nullable=False,
        default=HighlightStatus.SUGGESTED,
    )
    provenance_pointer: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    clinician_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    unresolved_action: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    clinical_entity_type: Mapped[ClinicalEntityType] = mapped_column(
        SqlEnum(
            ClinicalEntityType,
            values_callable=lambda entities: [entity.value for entity in entities],
            native_enum=False,
            create_constraint=True,
            name="highlight_clinical_entity_type",
        ),
        nullable=False,
    )

    patient: Mapped["Patient"] = relationship(back_populates="highlights")  # noqa: F821
    entry: Mapped["TimelineEntry"] = relationship(back_populates="highlights")  # noqa: F821

