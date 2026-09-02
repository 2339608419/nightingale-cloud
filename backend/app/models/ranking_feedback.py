from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class FeedbackDecision(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNDONE = "undone"


class HighlightFeedback(Base):
    """Actor-aware decision state; never stores Highlight or clinical text."""

    __tablename__ = "highlight_feedback"
    __table_args__ = (
        UniqueConstraint("clinic_id", "highlight_id", "actor_id"),
        Index("ix_feedback_clinic_category", "clinic_id", "category_type", "category_value"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    clinic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    highlight_id: Mapped[str] = mapped_column(
        ForeignKey("highlights.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(30), nullable=False)
    decision: Mapped[FeedbackDecision] = mapped_column(
        SqlEnum(
            FeedbackDecision,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="feedback_decision",
        ),
        nullable=False,
    )
    category_type: Mapped[str] = mapped_column(String(30), nullable=False)
    category_value: Mapped[str] = mapped_column(String(50), nullable=False)
    entry_type_value: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class HighlightExposure(Base):
    """Explicit, idempotent UI impression metadata without clinical content."""

    __tablename__ = "highlight_exposures"
    __table_args__ = (
        UniqueConstraint("clinic_id", "highlight_id", "display_reference"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    clinic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    highlight_id: Mapped[str] = mapped_column(
        ForeignKey("highlights.id", ondelete="CASCADE"), nullable=False, index=True
    )
    actor_id: Mapped[str] = mapped_column(String(100), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(30), nullable=False)
    display_reference: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
