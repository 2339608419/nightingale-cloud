from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    DeliveryRead,
    PatientSessionRead,
    PhoneAccessChallengeRead,
    PhoneAccessExchange,
    PhoneAccessRequest,
    TimelineEntryRead,
)
from app.services.authorization_service import filter_visible_entries
from app.services.clinic_scope_service import (
    get_patient_deliveries_in_clinic,
    get_patient_entries_in_clinic,
)
from app.services.patient_access_service import (
    InvalidPatientAccessToken,
    authenticate_patient_session,
    create_decoy_phone_challenge,
    exchange_phone_challenge,
    request_phone_challenge,
)


router = APIRouter(tags=["patient-access"])
DbSession = Annotated[Session, Depends(get_db)]


def _bearer_token(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Patient session is required")
    return authorization.removeprefix("Bearer ").strip()


@router.post("/patient-access/phone/request", response_model=PhoneAccessChallengeRead)
def request_access(payload: PhoneAccessRequest, db: DbSession) -> PhoneAccessChallengeRead:
    try:
        challenge = request_phone_challenge(db, payload.phone, payload.clinic_id)
        if challenge is None:
            challenge = create_decoy_phone_challenge(payload.phone)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid synthetic phone format",
        ) from error
    return PhoneAccessChallengeRead(
        challenge_id=challenge.challenge_id,
        masked_destination=challenge.masked_destination,
        expires_at=challenge.expires_at,
        mock_access_token=challenge.token,
    )


@router.post("/patient-access/phone/exchange", response_model=PatientSessionRead)
def exchange_access(payload: PhoneAccessExchange, db: DbSession) -> PatientSessionRead:
    try:
        issued = exchange_phone_challenge(db, payload.access_token)
    except InvalidPatientAccessToken as error:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Access token is invalid or expired") from error
    return PatientSessionRead(
        patient_id=issued.patient_id,
        session_token=issued.token,
        expires_at=issued.expires_at,
    )


def _patient_identity(db: Session, authorization: str | None):
    try:
        return authenticate_patient_session(db, _bearer_token(authorization))
    except InvalidPatientAccessToken as error:
        raise HTTPException(status_code=401, detail="Patient session is invalid or expired") from error


@router.get("/patient-portal/instructions", response_model=list[TimelineEntryRead])
def read_portal_instructions(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> list[TimelineEntryRead]:
    user = _patient_identity(db, authorization)
    entries = get_patient_entries_in_clinic(db, user.user_id, user.clinic_id)
    return [TimelineEntryRead.model_validate(item) for item in filter_visible_entries(user, entries)]


@router.get(
    "/patient-portal/patients/{patient_id}/instructions",
    response_model=list[TimelineEntryRead],
)
def read_portal_patient_instructions(
    patient_id: str,
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> list[TimelineEntryRead]:
    user = _patient_identity(db, authorization)
    if patient_id != user.user_id:
        raise HTTPException(status_code=403, detail="Patient session is self-only")
    entries = get_patient_entries_in_clinic(db, patient_id, user.clinic_id)
    return [TimelineEntryRead.model_validate(item) for item in filter_visible_entries(user, entries)]


@router.get("/patient-portal/deliveries", response_model=list[DeliveryRead])
def read_portal_deliveries(
    db: DbSession,
    authorization: Annotated[str | None, Header()] = None,
) -> list[DeliveryRead]:
    user = _patient_identity(db, authorization)
    return [
        DeliveryRead.model_validate(item)
        for item in get_patient_deliveries_in_clinic(db, user.user_id, user.clinic_id)
    ]
