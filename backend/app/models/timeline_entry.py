from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class AuthorRole(str, Enum):
    PATIENT = "patient"
    STAFF = "staff"
    CLINICIAN = "clinician"
    SYSTEM = "system"


class TimelineEntryType(str, Enum):
    CLINICIAN_NOTE = "clinician_note"
    STAFF_NOTE = "staff_note"
    AI_DOCTOR_CONSULT_SUMMARY = "ai_doctor_consult_summary"
    AI_NURSE_CONSULT_SUMMARY = "ai_nurse_consult_summary"
    AI_PATIENT_SESSION_SUMMARY = "ai_patient_session_summary"
    SYSTEM_EVENT = "system_event"
    INSTRUCTION = "instruction"
    ADMIN = "admin"


class TimelineEntry(Base):
    __tablename__ = "timeline_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    author_role: Mapped[AuthorRole] = mapped_column(
        SqlEnum(
            AuthorRole,
            values_callable=lambda roles: [role.value for role in roles],
            native_enum=False,
            create_constraint=True,
            name="timeline_author_role",
        ),
        nullable=False,
    )
    author_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
    )
    type: Mapped[TimelineEntryType] = mapped_column(
        SqlEnum(
            TimelineEntryType,
            values_callable=lambda entry_types: [entry_type.value for entry_type in entry_types],
            native_enum=False,
            create_constraint=True,
            name="timeline_entry_type",
        ),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    provenance_pointer: Mapped[str | None] = mapped_column(String(500), nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="entries")  # noqa: F821
    highlights: Mapped[list["Highlight"]] = relationship(  # noqa: F821
        back_populates="entry", cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(  # noqa: F821
        back_populates="entry", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["TaskAssignment"]] = relationship(  # noqa: F821
        back_populates="entry"
    )
