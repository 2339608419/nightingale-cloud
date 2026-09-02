from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import AuditLog, EntryVersion, PatientDelivery


STAFF = {
    "X-User-Id": "staff-demo-001",
    "X-Role": "staff",
    "X-Clinic-Id": "clinic-demo-001",
}
CLINICIAN = {
    "X-User-Id": "clinician-demo-001",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-001",
}
CLINIC_B = {"X-User-Id": "clinician-demo-002", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-002"}


def test_permitted_edits_to_different_entries_are_independent(client: TestClient) -> None:
    staff_update = client.patch(
        "/entries/entry-demo-003",
        headers=STAFF,
        json={"content": "Staff section updated independently.", "expected_version": 1},
    )
    clinician_update = client.patch(
        "/entries/entry-demo-001",
        headers=CLINICIAN,
        json={"content": "Clinician section updated independently.", "expected_version": 1},
    )

    assert staff_update.status_code == 200
    assert clinician_update.status_code == 200
    entries = client.get("/patients/patient-demo-001/entries", headers=CLINICIAN).json()
    contents = {entry["id"]: entry["content"] for entry in entries}
    assert contents["entry-demo-003"] == "Staff section updated independently."
    assert contents["entry-demo-001"] == "Clinician section updated independently."


def test_stale_same_entry_edit_is_rejected_with_409(client: TestClient) -> None:
    first = client.patch(
        "/entries/entry-demo-001",
        headers=CLINICIAN,
        json={"content": "First accepted edit.", "expected_version": 1},
    )
    stale = client.patch(
        "/entries/entry-demo-001",
        headers=CLINICIAN,
        json={"content": "Stale overwrite attempt.", "expected_version": 1},
    )

    assert first.status_code == 200
    assert stale.status_code == 409
    detail = stale.json()["detail"]
    assert detail == {
        "error_code": "entry_version_conflict",
        "entry_id": "entry-demo-001",
        "expected_version": 1,
        "current_version": 2,
        "current_content": "First accepted edit.",
        "current_provenance_pointer": "synthetic://encounter/2025-04-15#assessment",
    }
    entries = client.get("/patients/patient-demo-001/entries", headers=CLINICIAN).json()
    current = next(entry for entry in entries if entry["id"] == "entry-demo-001")
    assert current["content"] == "First accepted edit."

    override = app.dependency_overrides[get_db]
    iterator = override()
    db = next(iterator)
    try:
        versions = list(db.scalars(select(EntryVersion).where(EntryVersion.entry_id == "entry-demo-001")))
        audits = list(db.scalars(select(AuditLog).where(
            AuditLog.entity_type == "timeline_entry",
            AuditLog.entity_id == "entry-demo-001",
            AuditLog.action == "entry.updated",
        )))
        assert [item.version_number for item in versions] == [1, 2]
        assert len(audits) == 1
        assert all("Stale overwrite attempt." not in item.content for item in versions)
    finally:
        iterator.close()


def test_stale_edit_does_not_repeat_approval_or_delivery_mutations(client: TestClient) -> None:
    draft = client.post(
        "/patients/patient-demo-001/entries",
        headers=CLINICIAN,
        json={
            "type": "instruction",
            "content": "Synthetic approved instruction.",
            "ai_derived": True,
            "source_entry_id": "entry-demo-004",
        },
    ).json()
    assert client.post(f"/entries/{draft['id']}/patient-facing/approve", headers=CLINICIAN).status_code == 200
    delivery = client.post(
        f"/entries/{draft['id']}/deliveries",
        headers=STAFF,
        json={"channel": "sms_mock", "purpose": "instruction", "replaces_delivery_id": None},
    ).json()
    first = client.patch(
        f"/entries/{draft['id']}", headers=CLINICIAN,
        json={"content": "First valid correction.", "expected_version": 1},
    )
    assert first.status_code == 200

    override = app.dependency_overrides[get_db]
    iterator = override()
    db = next(iterator)
    try:
        before_status = db.get(PatientDelivery, delivery["id"]).status
        before_audits = len(list(db.scalars(select(AuditLog))))
    finally:
        iterator.close()
    stale = client.patch(
        f"/entries/{draft['id']}", headers=CLINICIAN,
        json={"content": "Rejected stale correction.", "expected_version": 1},
    )
    assert stale.status_code == 409
    iterator = override()
    db = next(iterator)
    try:
        assert db.get(PatientDelivery, delivery["id"]).status == before_status
        assert len(list(db.scalars(select(AuditLog)))) == before_audits
        versions = list(db.scalars(select(EntryVersion).where(EntryVersion.entry_id == draft["id"])))
        assert len(versions) == 2
        assert all("Rejected stale correction." not in item.content for item in versions)
    finally:
        iterator.close()


def test_unauthorized_and_cross_clinic_edits_do_not_receive_conflict_content(client: TestClient) -> None:
    secret = "Authorized clinician server content."
    assert client.patch(
        "/entries/entry-demo-001", headers=CLINICIAN,
        json={"content": secret, "expected_version": 1},
    ).status_code == 200
    for headers in (STAFF, CLINIC_B):
        response = client.patch(
            "/entries/entry-demo-001", headers=headers,
            json={"content": "Unauthorized draft.", "expected_version": 1},
        )
        assert response.status_code in {403, 404}
        assert secret not in response.text
        assert "current_content" not in response.text
