from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import CurrentUser, get_current_user
from app.database import get_db
from app.models import PatientDelivery
from app.schemas import DeliveryCreate, DeliveryRead, DeliveryStatusUpdate
from app.services.authorization_service import (
    require_delivery_action_access,
    require_patient_access,
)
from app.services.clinic_scope_service import (
    get_delivery_in_clinic,
    get_entry_in_clinic,
    get_patient_deliveries_in_clinic,
    get_patient_in_clinic,
)
from app.services.delivery_service import create_delivery, transition_delivery
from app.services.patient_service import get_entry, get_patient


router = APIRouter(tags=["deliveries"])
DbSession = Annotated[Session, Depends(get_db)]
Identity = Annotated[CurrentUser, Depends(get_current_user)]


@router.get("/patients/{patient_id}/deliveries", response_model=list[DeliveryRead])
def read_deliveries(patient_id: str, db: DbSession, user: Identity) -> list[DeliveryRead]:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    require_patient_access(user, patient)
    if get_patient_in_clinic(db, patient_id, user.clinic_id) is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    return [
        DeliveryRead.model_validate(item)
        for item in get_patient_deliveries_in_clinic(db, patient_id, user.clinic_id)
    ]


@router.post("/entries/{entry_id}/deliveries", response_model=DeliveryRead, status_code=201)
def add_delivery(
    entry_id: str, payload: DeliveryCreate, db: DbSession, user: Identity
) -> DeliveryRead:
    entry = get_entry(db, entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    patient = get_patient(db, entry.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    require_patient_access(user, patient)
    require_delivery_action_access(user)
    scoped_entry = get_entry_in_clinic(db, entry_id, user.clinic_id)
    scoped_patient = get_patient_in_clinic(db, entry.patient_id, user.clinic_id)
    if scoped_entry is None or scoped_patient is None:
        raise HTTPException(status_code=404, detail="Entry not found")
    if not scoped_patient.phone_is_synthetic or scoped_patient.phone_masked is None:
        raise HTTPException(status_code=422, detail="Synthetic patient destination is unavailable")
    return DeliveryRead.model_validate(
        create_delivery(
            db,
            entry=scoped_entry,
            actor=user,
            masked_destination=scoped_patient.phone_masked,
            channel=payload.channel,
            purpose=payload.purpose,
            replaces_delivery_id=payload.replaces_delivery_id,
        )
    )


@router.patch("/deliveries/{delivery_id}/status", response_model=DeliveryRead)
def update_delivery_status(
    delivery_id: str,
    payload: DeliveryStatusUpdate,
    db: DbSession,
    user: Identity,
) -> DeliveryRead:
    delivery = db.get(PatientDelivery, delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    patient = get_patient(db, delivery.patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")
    require_patient_access(user, patient)
    require_delivery_action_access(user)
    scoped = get_delivery_in_clinic(db, delivery_id, user.clinic_id)
    if scoped is None:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return DeliveryRead.model_validate(
        transition_delivery(db, scoped, user, payload.status, payload.failure_reason_code)
    )
