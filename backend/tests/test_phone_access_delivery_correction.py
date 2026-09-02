import json
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog,
    DeliveryFailureReason,
    EntryVersion,
    Patient,
    PatientDelivery,
    PatientPortalSession,
    PhoneAccessChallenge,
)
from app.routes import deliveries as delivery_routes
from app.services.contact_security_service import phone_digest, token_digest
from app.services.patient_access_service import claim_phone_challenge
from app.services.seed import OTHER_CLINIC_PATIENT_ID, SYNTHETIC_PATIENT_ID


CLINICIAN = {
    "X-User-Id": "clinician-demo-001",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-001",
}
STAFF = {
    "X-User-Id": "staff-demo-001",
    "X-Role": "staff",
    "X-Clinic-Id": "clinic-demo-001",
}
CLINIC_B = {
    "X-User-Id": "clinician-demo-002",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-002",
}
SYNTHETIC_PHONE = "+6590000001"


def _db_session():
    override = app.dependency_overrides[get_db]
    iterator = override()
    return iterator, next(iterator)


def _issue_session(client: TestClient) -> tuple[str, str]:
    request = client.post(
        "/patient-access/phone/request",
        json={"phone": SYNTHETIC_PHONE, "clinic_id": "clinic-demo-001", "synthetic": True},
    )
    assert request.status_code == 200
    assert request.json()["accepted"] is True
    access_token = request.json()["mock_access_token"]
    exchange = client.post(
        "/patient-access/phone/exchange",
        json={"access_token": access_token},
    )
    assert exchange.status_code == 200
    return access_token, exchange.json()["session_token"]


def test_known_and_unknown_valid_phone_requests_are_publicly_indistinguishable(
    client: TestClient,
) -> None:
    known = client.post(
        "/patient-access/phone/request",
        json={"phone": SYNTHETIC_PHONE, "clinic_id": "clinic-demo-001", "synthetic": True},
    )
    unknown = client.post(
        "/patient-access/phone/request",
        json={"phone": "+6599999999", "clinic_id": "clinic-demo-001", "synthetic": True},
    )
    assert known.status_code == unknown.status_code == 200
    known_body, unknown_body = known.json(), unknown.json()
    assert set(known_body) == set(unknown_body)
    for field in ("accepted", "mode", "warning"):
        assert known_body[field] == unknown_body[field]
    assert known_body["accepted"] is unknown_body["accepted"] is True
    assert known_body["masked_destination"].startswith("+65")
    assert unknown_body["masked_destination"].startswith("+65")
    assert len(known_body["masked_destination"]) == len(unknown_body["masked_destination"])
    assert all(known_body[field] for field in ("challenge_id", "mock_access_token", "expires_at"))
    assert all(unknown_body[field] for field in ("challenge_id", "mock_access_token", "expires_at"))

    exchange = client.post(
        "/patient-access/phone/exchange",
        json={"access_token": unknown_body["mock_access_token"]},
    )
    assert exchange.status_code == 401
    iterator, db = _db_session()
    try:
        assert db.get(PhoneAccessChallenge, unknown_body["challenge_id"]) is None
    finally:
        iterator.close()


def test_same_synthetic_phone_resolves_within_requested_clinic(client: TestClient) -> None:
    patient_ids = []
    for clinic_id in ("clinic-demo-001", "clinic-demo-002"):
        issued = client.post(
            "/patient-access/phone/request",
            json={"phone": SYNTHETIC_PHONE, "clinic_id": clinic_id, "synthetic": True},
        )
        assert issued.status_code == 200
        exchanged = client.post(
            "/patient-access/phone/exchange",
            json={"access_token": issued.json()["mock_access_token"]},
        )
        assert exchanged.status_code == 200
        patient_ids.append(exchanged.json()["patient_id"])
    assert patient_ids == [SYNTHETIC_PATIENT_ID, OTHER_CLINIC_PATIENT_ID]


def test_same_clinic_rejects_duplicate_phone_digest(client: TestClient) -> None:
    iterator, db = _db_session()
    try:
        db.add(
            Patient(
                id="patient-duplicate-phone",
                clinic_id="clinic-demo-001",
                name="Synthetic Duplicate",
                date_of_birth=datetime(1990, 1, 1).date(),
                phone_digest=phone_digest(SYNTHETIC_PHONE),
                phone_masked="+65••••0001",
                phone_is_synthetic=True,
                created_at=datetime.now(timezone.utc),
            )
        )
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()
    finally:
        iterator.close()


def test_atomic_challenge_claim_allows_only_one_database_session(tmp_path) -> None:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'atomic-claim.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    now = datetime.now(timezone.utc)
    token = "synthetic-one-time-token"
    setup = Session()
    setup.add_all(
        [
            Patient(
                id="atomic-patient",
                clinic_id="atomic-clinic",
                name="Synthetic Atomic Patient",
                date_of_birth=datetime(1990, 1, 1).date(),
                phone_digest=phone_digest("+6591111111"),
                phone_masked="+65••••1111",
                phone_is_synthetic=True,
                created_at=now,
            ),
            PhoneAccessChallenge(
                id="atomic-challenge",
                patient_id="atomic-patient",
                clinic_id="atomic-clinic",
                token_digest=token_digest(token),
                expires_at=now + timedelta(minutes=10),
                consumed_at=None,
                created_at=now,
            ),
        ]
    )
    setup.commit()
    setup.close()

    first, second = Session(), Session()
    try:
        assert claim_phone_challenge(first, token_digest(token), now) == (
            "atomic-patient",
            "atomic-clinic",
        )
        first.commit()
        assert claim_phone_challenge(second, token_digest(token), now) is None
        second.rollback()
    finally:
        first.close()
        second.close()
        engine.dispose()


def _create_approved_ai_instruction(client: TestClient, content: str = "Repeat synthetic labs next week.") -> dict:
    draft = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINICIAN,
        json={
            "type": "instruction",
            "content": content,
            "ai_derived": True,
            "source_entry_id": "entry-demo-004",
        },
    )
    assert draft.status_code == 201
    approved = client.post(
        f"/entries/{draft.json()['id']}/patient-facing/approve", headers=CLINICIAN
    )
    assert approved.status_code == 200
    assert approved.json()["approved_version_number"] == 1
    return approved.json()


def _create_delivery(client: TestClient, entry_id: str, **overrides) -> dict:
    payload = {
        "channel": "whatsapp_mock",
        "purpose": "instruction",
        "replaces_delivery_id": None,
        **overrides,
    }
    response = client.post(
        f"/entries/{entry_id}/deliveries", headers=STAFF, json=payload
    )
    assert response.status_code == 201, response.text
    return response.json()


def _transition(client: TestClient, delivery_id: str, state: str, reason: str | None = None):
    return client.patch(
        f"/deliveries/{delivery_id}/status",
        headers=STAFF,
        json={"status": state, "failure_reason_code": reason},
    )


def test_phone_first_access_uses_digest_single_use_and_self_only_portal(
    client: TestClient, caplog: pytest.LogCaptureFixture
) -> None:
    access_token, session_token = _issue_session(client)
    bearer = {
        "Authorization": f"Bearer {session_token}",
        "X-User-Id": "",
        "X-Role": "",
        "X-Clinic-Id": "",
    }

    replay = client.post(
        "/patient-access/phone/exchange", json={"access_token": access_token}
    )
    instructions = client.get("/patient-portal/instructions", headers=bearer)
    other_patient = client.get(
        f"/patient-portal/patients/{OTHER_CLINIC_PATIENT_ID}/instructions",
        headers=bearer,
    )

    assert replay.status_code == 401
    assert instructions.status_code == 200
    assert instructions.json()
    assert all(item["type"] == "instruction" for item in instructions.json())
    assert all(item["patient_facing_status"] == "approved" for item in instructions.json())
    assert other_patient.status_code == 403
    assert client.get("/entries/entry-demo-006/audit", headers=bearer).status_code == 401
    assert client.get("/entries/entry-demo-007/comments", headers=bearer).status_code == 401
    assert client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=bearer).status_code == 401

    iterator, db = _db_session()
    try:
        challenge = db.scalar(select(PhoneAccessChallenge))
        session = db.scalar(select(PatientPortalSession))
        assert challenge is not None and session is not None
        assert challenge.token_digest != access_token
        assert session.token_digest != session_token
        assert access_token not in challenge.token_digest
        assert session_token not in session.token_digest
        assert challenge.consumed_at is not None
        assert db.scalar(select(AuditLog).where(AuditLog.entity_type == "phone_access")) is None
    finally:
        iterator.close()
    serialized = caplog.text + instructions.text + other_patient.text
    assert SYNTHETIC_PHONE not in serialized


def test_expired_access_token_is_rejected_without_plaintext_storage(client: TestClient) -> None:
    request = client.post(
        "/patient-access/phone/request",
        json={"phone": SYNTHETIC_PHONE, "clinic_id": "clinic-demo-001", "synthetic": True},
    )
    token = request.json()["mock_access_token"]
    iterator, db = _db_session()
    try:
        challenge = db.scalar(select(PhoneAccessChallenge))
        assert challenge is not None
        challenge.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.commit()
    finally:
        iterator.close()

    response = client.post(
        "/patient-access/phone/exchange", json={"access_token": token}
    )
    assert response.status_code == 401
    assert token not in response.text


def test_draft_and_rejected_instructions_remain_absent_from_phone_session(client: TestClient) -> None:
    _, session_token = _issue_session(client)
    draft = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINICIAN,
        json={
            "type": "instruction",
            "content": "Synthetic draft not approved.",
            "ai_derived": True,
            "source_entry_id": "entry-demo-004",
        },
    ).json()
    rejected = client.post(
        f"/entries/{draft['id']}/patient-facing/reject", headers=CLINICIAN
    )
    assert rejected.status_code == 200

    response = client.get(
        "/patient-portal/instructions",
        headers={"Authorization": f"Bearer {session_token}"},
    )
    assert response.status_code == 200
    assert draft["id"] not in {item["id"] for item in response.json()}


def test_delivery_states_are_distinct_and_invalid_transition_has_no_audit(client: TestClient) -> None:
    delivery = _create_delivery(client, "entry-demo-006", purpose="appointment_link")
    assert delivery["status"] == "created"
    queued = _transition(client, delivery["id"], "queued")
    assert queued.status_code == 200 and queued.json()["status"] == "queued"
    failed = _transition(client, delivery["id"], "failed", "receipt_unavailable")
    assert failed.status_code == 200 and failed.json()["status"] == "failed"

    iterator, db = _db_session()
    try:
        audit_count = len(list(db.scalars(select(AuditLog).where(AuditLog.entity_id == delivery["id"]))))
    finally:
        iterator.close()
    illegal = _transition(client, delivery["id"], "simulated_delivered")
    assert illegal.status_code == 409
    iterator, db = _db_session()
    try:
        assert len(list(db.scalars(select(AuditLog).where(AuditLog.entity_id == delivery["id"])))) == audit_count
    finally:
        iterator.close()

    sent_delivery = _create_delivery(client, "entry-demo-006")
    assert _transition(client, sent_delivery["id"], "queued").status_code == 200
    sent = _transition(client, sent_delivery["id"], "simulated_sent")
    assert sent.json()["status"] == "simulated_sent"
    assert sent.json()["status"] != "simulated_delivered"
    delivered = _transition(client, sent_delivery["id"], "simulated_delivered")
    assert delivered.json()["status"] == "simulated_delivered"


def test_delivery_failure_reason_is_allowlisted_and_rejections_have_no_side_effects(
    client: TestClient,
) -> None:
    delivery = _create_delivery(client, "entry-demo-006")
    assert _transition(client, delivery["id"], "queued").status_code == 200

    iterator, db = _db_session()
    try:
        before_audits = len(list(db.scalars(select(AuditLog).where(AuditLog.entity_id == delivery["id"]))))
    finally:
        iterator.close()

    for unsafe_reason in ("free_text", "John Tan S1234567A +6591234567 Lisinopril 99 mg"):
        response = _transition(client, delivery["id"], "failed", unsafe_reason)
        assert response.status_code == 422
    assert _transition(client, delivery["id"], "failed").status_code == 422
    assert _transition(client, delivery["id"], "simulated_sent", "provider_timeout").status_code == 422

    iterator, db = _db_session()
    try:
        unchanged = db.get(PatientDelivery, delivery["id"])
        assert unchanged.status.value == "queued"
        assert unchanged.failure_reason_code is None
        after_audits = len(list(db.scalars(select(AuditLog).where(AuditLog.entity_id == delivery["id"]))))
        assert after_audits == before_audits
    finally:
        iterator.close()

    accepted = _transition(client, delivery["id"], "failed", DeliveryFailureReason.PROVIDER_TIMEOUT.value)
    assert accepted.status_code == 200
    assert accepted.json()["failure_reason_code"] == "provider_timeout"


def test_delivery_binds_approved_snapshot_and_edit_requires_traceable_correction(client: TestClient) -> None:
    original = "Synthetic Lisinopril 20 mg instruction approved for delivery."
    corrected = "Synthetic Lisinopril 10 mg corrected instruction."
    instruction = _create_approved_ai_instruction(client, original)
    delivery = _create_delivery(client, instruction["id"])
    assert delivery["approved_version_number"] == 1
    assert _transition(client, delivery["id"], "queued").status_code == 200
    assert _transition(client, delivery["id"], "simulated_sent").status_code == 200

    edit = client.patch(
        f"/entries/{instruction['id']}",
        headers=CLINICIAN,
        json={"content": corrected, "expected_version": 1},
    )
    assert edit.status_code == 200
    assert edit.json()["patient_facing_status"] == "draft"
    old = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/deliveries", headers=CLINICIAN
    ).json()
    old = next(item for item in old if item["id"] == delivery["id"])
    assert old["status"] == "correction_required"
    assert client.post(
        f"/entries/{instruction['id']}/deliveries",
        headers=STAFF,
        json={"channel": "whatsapp_mock", "purpose": "correction", "replaces_delivery_id": delivery["id"]},
    ).status_code == 422

    versions = client.get(f"/entries/{instruction['id']}/versions", headers=CLINICIAN).json()
    assert [item["version_number"] for item in versions] == [2, 1]
    assert versions[1]["content"] == original
    assert client.post(
        f"/entries/{instruction['id']}/patient-facing/approve", headers=CLINICIAN
    ).json()["approved_version_number"] == 2
    replacement = _create_delivery(
        client,
        instruction["id"],
        purpose="correction",
        replaces_delivery_id=delivery["id"],
    )
    assert replacement["approved_version_number"] == 2
    assert replacement["replaces_delivery_id"] == delivery["id"]
    old_after = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/deliveries", headers=CLINICIAN
    ).json()
    assert next(item for item in old_after if item["id"] == delivery["id"])["status"] == "superseded"


@pytest.mark.parametrize("role", ["staff", "patient", "admin"])
def test_non_clinicians_cannot_approve_corrected_instruction(client: TestClient, role: str) -> None:
    instruction = _create_approved_ai_instruction(client)
    client.patch(
        f"/entries/{instruction['id']}",
        headers=CLINICIAN,
        json={"content": "Corrected synthetic instruction.", "expected_version": 1},
    )
    headers = {
        "X-User-Id": SYNTHETIC_PATIENT_ID if role == "patient" else f"{role}-demo-001",
        "X-Role": role,
        "X-Clinic-Id": "clinic-demo-001",
    }
    assert client.post(
        f"/entries/{instruction['id']}/patient-facing/approve", headers=headers
    ).status_code == 403


def test_delivery_audit_is_metadata_only(client: TestClient) -> None:
    secret = "Synthetic wrong dose Lisinopril 99 mg +6590000001"
    instruction = _create_approved_ai_instruction(client, secret)
    delivery = _create_delivery(client, instruction["id"])
    _transition(client, delivery["id"], "queued")
    iterator, db = _db_session()
    try:
        events = list(db.scalars(select(AuditLog).where(AuditLog.entity_id == delivery["id"])))
        serialized = json.dumps(
            [{"action": item.action, "metadata": item.metadata_json} for item in events]
        )
        assert events
        assert all(set(item.metadata_json) == {"from_status", "to_status"} for item in events)
        assert secret not in serialized
        assert SYNTHETIC_PHONE not in serialized
        assert "99 mg" not in serialized
    finally:
        iterator.close()


def test_clinic_b_cannot_read_or_mutate_clinic_a_delivery_when_outer_guard_fails(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    delivery = _create_delivery(client, "entry-demo-006")
    monkeypatch.setattr(delivery_routes, "require_patient_access", lambda _user, _patient: None)
    read = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/deliveries", headers=CLINIC_B)
    mutate = client.patch(
        f"/deliveries/{delivery['id']}/status",
        headers=CLINIC_B,
        json={"status": "queued"},
    )
    assert read.status_code == 404
    assert mutate.status_code == 404
    assert "Lisinopril" not in read.text + mutate.text


def test_replacement_link_injection_is_rejected(client: TestClient) -> None:
    first = _create_approved_ai_instruction(client, "First synthetic instruction.")
    second = _create_approved_ai_instruction(client, "Second synthetic instruction.")
    old = _create_delivery(client, first["id"])
    _transition(client, old["id"], "queued")
    _transition(client, old["id"], "simulated_sent")
    client.patch(
        f"/entries/{first['id']}",
        headers=CLINICIAN,
        json={"content": "First corrected instruction.", "expected_version": 1},
    )
    response = client.post(
        f"/entries/{second['id']}/deliveries",
        headers=STAFF,
        json={
            "channel": "sms_mock",
            "purpose": "correction",
            "replaces_delivery_id": old["id"],
        },
    )
    assert response.status_code == 422
