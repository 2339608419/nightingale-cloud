from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class ConflictEntityType(str, Enum):
    MEDICATION = "medication"
    ALLERGY = "allergy"
    FOLLOW_UP = "follow_up"


class ConflictStatus(str, Enum):
    OPEN = "open"
    RESOLVED = "resolved"


class ConflictAuthorityPolicy(str, Enum):
    CLINICIAN_AUTHORITATIVE = "clinician_authoritative"
    STAFF_AUTHORITATIVE = "staff_authoritative"
    CLINICIAN_REVIEW_REQUIRED = "clinician_review_required"


class ConflictRecord(Base):
    __tablename__ = "conflict_records"
    __table_args__ = (
        Index("ix_conflict_patient_status", "patient_id", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    authoritative_entry_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="CASCADE"), nullable=False
    )
    conflicting_entry_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="CASCADE"), nullable=False
    )
    entity_type: Mapped[ConflictEntityType] = mapped_column(
        SqlEnum(
            ConflictEntityType,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="conflict_entity_type",
        ),
        nullable=False,
    )
    entity_name: Mapped[str] = mapped_column(String(100), nullable=False)
    prior_value: Mapped[str] = mapped_column(String(100), nullable=False)
    authoritative_value: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ConflictStatus] = mapped_column(
        SqlEnum(
            ConflictStatus,
            values_callable=lambda values: [value.value for value in values],
            native_enum=False,
            create_constraint=True,
            name="conflict_status",
        ),
        default=ConflictStatus.OPEN,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ConflictProvenance(Base):
    """Immutable version binding for both contradictory sources."""

    __tablename__ = "conflict_provenance"
    __table_args__ = (UniqueConstraint("conflict_id"),)

    conflict_id: Mapped[str] = mapped_column(
        ForeignKey("conflict_records.id", ondelete="CASCADE"), primary_key=True
    )
    authoritative_version_number: Mapped[int] = mapped_column(nullable=False)
    conflicting_version_number: Mapped[int] = mapped_column(nullable=False)
    authoritative_version_pointer: Mapped[str] = mapped_column(String(500), nullable=False)
    conflicting_version_pointer: Mapped[str] = mapped_column(String(500), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
