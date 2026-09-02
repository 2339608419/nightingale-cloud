from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SqlEnum, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.session import Base


class DeliveryChannel(str, Enum):
    WHATSAPP_MOCK = "whatsapp_mock"
    SMS_MOCK = "sms_mock"


class DeliveryPurpose(str, Enum):
    INSTRUCTION = "instruction"
    APPOINTMENT_LINK = "appointment_link"
    CORRECTION = "correction"


class DeliveryStatus(str, Enum):
    CREATED = "created"
    QUEUED = "queued"
    SIMULATED_SENT = "simulated_sent"
    SIMULATED_DELIVERED = "simulated_delivered"
    FAILED = "failed"
    CORRECTION_REQUIRED = "correction_required"
    SUPERSEDED = "superseded"


class DeliveryFailureReason(str, Enum):
    INVALID_DESTINATION = "invalid_destination"
    CHANNEL_UNAVAILABLE = "channel_unavailable"
    RECEIPT_UNAVAILABLE = "receipt_unavailable"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_REJECTED = "provider_rejected"


class PatientDelivery(Base):
    __tablename__ = "patient_deliveries"
    __table_args__ = (
        UniqueConstraint("provider_message_reference"),
        Index("ix_delivery_patient_status_created", "patient_id", "status", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    clinic_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    patient_id: Mapped[str] = mapped_column(
        ForeignKey("patients.id", ondelete="CASCADE"), nullable=False, index=True
    )
    entry_id: Mapped[str] = mapped_column(
        ForeignKey("timeline_entries.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    approved_version_number: Mapped[int] = mapped_column(nullable=False)
    channel: Mapped[DeliveryChannel] = mapped_column(
        SqlEnum(DeliveryChannel, values_callable=lambda values: [v.value for v in values], native_enum=False),
        nullable=False,
    )
    purpose: Mapped[DeliveryPurpose] = mapped_column(
        SqlEnum(DeliveryPurpose, values_callable=lambda values: [v.value for v in values], native_enum=False),
        nullable=False,
    )
    masked_destination: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[DeliveryStatus] = mapped_column(
        SqlEnum(DeliveryStatus, values_callable=lambda values: [v.value for v in values], native_enum=False),
        nullable=False,
    )
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(20), nullable=False)
    provider_message_reference: Mapped[str] = mapped_column(String(80), nullable=False)
    replaces_delivery_id: Mapped[str | None] = mapped_column(
        ForeignKey("patient_deliveries.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    failure_reason_code: Mapped[DeliveryFailureReason | None] = mapped_column(
        SqlEnum(
            DeliveryFailureReason,
            values_callable=lambda values: [v.value for v in values],
            native_enum=False,
        ),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
