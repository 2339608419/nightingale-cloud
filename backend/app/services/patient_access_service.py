import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import CurrentUser, UserRole
from app.models import Patient, PatientPortalSession, PhoneAccessChallenge
from app.services.clinic_scope_service import get_patient_in_clinic
from app.services.contact_security_service import mask_phone, phone_digest, token_digest


CHALLENGE_LIFETIME = timedelta(minutes=10)
SESSION_LIFETIME = timedelta(hours=1)


class InvalidPatientAccessToken(Exception):
    pass


@dataclass(frozen=True)
class IssuedPhoneChallenge:
    challenge_id: str
    masked_destination: str
    token: str
    expires_at: datetime


@dataclass(frozen=True)
class IssuedPatientSession:
    token: str
    expires_at: datetime
    patient_id: str


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _is_expired(value: datetime, now: datetime) -> bool:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value <= now


def request_phone_challenge(
    db: Session, phone_e164: str, clinic_id: str
) -> IssuedPhoneChallenge | None:
    digest = phone_digest(phone_e164)
    patient = db.scalar(
        select(Patient).where(
            Patient.phone_digest == digest,
            Patient.clinic_id == clinic_id,
            Patient.phone_is_synthetic.is_(True),
        )
    )
    if patient is None or patient.phone_masked is None:
        return None
    now = _now()
    plaintext = secrets.token_urlsafe(32)
    challenge = PhoneAccessChallenge(
        id=str(uuid4()),
        patient_id=patient.id,
        clinic_id=patient.clinic_id,
        token_digest=token_digest(plaintext),
        expires_at=now + CHALLENGE_LIFETIME,
        consumed_at=None,
        created_at=now,
    )
    db.add(challenge)
    db.commit()
    return IssuedPhoneChallenge(
        challenge_id=challenge.id,
        masked_destination=mask_phone(phone_e164),
        token=plaintext,
        expires_at=challenge.expires_at,
    )


def create_decoy_phone_challenge(phone_e164: str) -> IssuedPhoneChallenge:
    """Return a non-persisted, non-redeemable response indistinguishable by shape."""
    now = _now()
    return IssuedPhoneChallenge(
        challenge_id=str(uuid4()),
        masked_destination=mask_phone(phone_e164),
        token=secrets.token_urlsafe(32),
        expires_at=now + CHALLENGE_LIFETIME,
    )


def claim_phone_challenge(
    db: Session, digest: str, now: datetime
) -> tuple[str, str] | None:
    """Atomically claim one live, unused challenge inside the caller transaction."""
    row = db.execute(
        update(PhoneAccessChallenge)
        .where(
            PhoneAccessChallenge.token_digest == digest,
            PhoneAccessChallenge.consumed_at.is_(None),
            PhoneAccessChallenge.expires_at > now,
        )
        .values(consumed_at=now)
        .returning(PhoneAccessChallenge.patient_id, PhoneAccessChallenge.clinic_id)
    ).first()
    if row is None:
        return None
    return row.patient_id, row.clinic_id


def exchange_phone_challenge(db: Session, plaintext: str) -> IssuedPatientSession:
    now = _now()
    claimed = claim_phone_challenge(db, token_digest(plaintext), now)
    if claimed is None:
        db.rollback()
        raise InvalidPatientAccessToken
    patient_id, clinic_id = claimed
    patient = get_patient_in_clinic(db, patient_id, clinic_id)
    if patient is None or not patient.phone_is_synthetic:
        db.rollback()
        raise InvalidPatientAccessToken
    session_plaintext = secrets.token_urlsafe(32)
    session = PatientPortalSession(
        id=str(uuid4()),
        patient_id=patient.id,
        clinic_id=patient.clinic_id,
        token_digest=token_digest(session_plaintext),
        expires_at=now + SESSION_LIFETIME,
        revoked_at=None,
        created_at=now,
    )
    db.add(session)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return IssuedPatientSession(
        token=session_plaintext,
        expires_at=session.expires_at,
        patient_id=patient.id,
    )


def authenticate_patient_session(db: Session, plaintext: str) -> CurrentUser:
    now = _now()
    session = db.scalar(
        select(PatientPortalSession).where(
            PatientPortalSession.token_digest == token_digest(plaintext)
        )
    )
    if (
        session is None
        or session.revoked_at is not None
        or _is_expired(session.expires_at, now)
        or get_patient_in_clinic(db, session.patient_id, session.clinic_id) is None
    ):
        raise InvalidPatientAccessToken
    return CurrentUser(
        user_id=session.patient_id,
        role=UserRole.PATIENT,
        clinic_id=session.clinic_id,
    )
