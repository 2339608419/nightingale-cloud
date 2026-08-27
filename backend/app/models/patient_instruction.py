from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class PatientFacingStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class PatientInstructionApproval(Base):
    """Approval metadata for AI-derived TimelineEntry instructions only."""

    __tablename__ = "patient_instruction_approvals"

    entry_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="CASCADE"), primary_key=True
    )
    patient_facing_status: Mapped[PatientFacingStatus] = mapped_column(
        SqlEnum(
            PatientFacingStatus,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="patient_facing_status",
        ),
        default=PatientFacingStatus.DRAFT,
        nullable=False,
    )
    ai_derived: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    source_entry_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approved_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
