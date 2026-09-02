from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import DeliveryChannel, DeliveryFailureReason, DeliveryPurpose, DeliveryStatus


class DeliveryCreate(BaseModel):
    channel: DeliveryChannel
    purpose: DeliveryPurpose
    replaces_delivery_id: str | None = None


class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus
    failure_reason_code: DeliveryFailureReason | None = None


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    clinic_id: str
    patient_id: str
    entry_id: str
    approved_version_number: int
    channel: DeliveryChannel
    purpose: DeliveryPurpose
    masked_destination: str
    status: DeliveryStatus
    replaces_delivery_id: str | None
    failure_reason_code: DeliveryFailureReason | None
    created_at: datetime
    updated_at: datetime
