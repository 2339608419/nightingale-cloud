from datetime import date, datetime, timezone

from sqlalchemy import Boolean, Date, DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.session import Base


class Patient(Base):
    __tablename__ = "patients"
    __table_args__ = (
        UniqueConstraint("clinic_id", "phone_digest", name="uq_patient_clinic_phone_digest"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    clinic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    date_of_birth: Mapped[date] = mapped_column(Date, nullable=False)
    phone_digest: Mapped[str | None] = mapped_column(String(80), nullable=True)
    phone_masked: Mapped[str | None] = mapped_column(String(32), nullable=True)
    phone_is_synthetic: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    entries: Mapped[list["TimelineEntry"]] = relationship(  # noqa: F821
        back_populates="patient", cascade="all, delete-orphan"
    )
    highlights: Mapped[list["Highlight"]] = relationship(  # noqa: F821
        back_populates="patient", cascade="all, delete-orphan"
    )
    assignments: Mapped[list["TaskAssignment"]] = relationship(  # noqa: F821
        back_populates="patient", cascade="all, delete-orphan"
    )
