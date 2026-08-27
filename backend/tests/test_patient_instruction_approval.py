import json

import pytest
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import TimelineEntry
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
PATIENT = {
    "X-User-Id": SYNTHETIC_PATIENT_ID,
    "X-Role": "patient",
    "X-Clinic-Id": "clinic-demo-001",
}
ADMIN = {
    "X-User-Id": "admin-demo-001",
    "X-Role": "admin",
    "X-Clinic-Id": "clinic-demo-001",
}


def _create_ai_draft(client: TestClient, content: str = "Repeat labs next week.") -> dict:
    response = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINICIAN,
        json={
            "type": "instruction",
            "content": content,
            "ai_derived": True,
            "source_entry_id": "entry-demo-004",
        },
    )
    assert response.status_code == 201
    draft = response.json()
    assert draft["patient_facing_status"] == "draft"
    assert draft["ai_derived"] is True
    assert draft["source_entry_id"] == "entry-demo-004"
    assert draft["provenance_pointer"] == "timeline-entry-entry-demo-004"
    clinician_entry_ids = {
        entry["id"]
        for entry in client.get(
            f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINICIAN
        ).json()
    }
    assert draft["source_entry_id"] in clinician_entry_ids
    return draft


def _patient_entries(client: TestClient) -> list[dict]:
    response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=PATIENT
    )
    assert response.status_code == 200
    return response.json()


def test_ai_derived_draft_is_hidden_until_clinician_approval(
    client: TestClient,
) -> None:
    draft = _create_ai_draft(client)
    assert draft["id"] not in {entry["id"] for entry in _patient_entries(client)}

    approved = client.post(
        f"/entries/{draft['id']}/patient-facing/approve", headers=CLINICIAN
    )

    assert approved.status_code == 200
    assert approved.json()["patient_facing_status"] == "approved"
    assert approved.json()["approved_by"] == "clinician-demo-001"
    assert approved.json()["approved_at"] is not None
    assert draft["id"] in {entry["id"] for entry in _patient_entries(client)}


@pytest.mark.parametrize("headers", [STAFF, PATIENT, ADMIN])
def test_only_clinician_can_approve(
    client: TestClient, headers: dict[str, str]
) -> None:
    draft = _create_ai_draft(client)

    response = client.post(
        f"/entries/{draft['id']}/patient-facing/approve", headers=headers
    )

    assert response.status_code == 403
    current = next(
        entry
        for entry in client.get(
            f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINICIAN
        ).json()
        if entry["id"] == draft["id"]
    )
    assert current["patient_facing_status"] == "draft"
    assert client.get(f"/entries/{draft['id']}/audit", headers=CLINICIAN).json() == []


def test_rejected_instruction_remains_patient_invisible(client: TestClient) -> None:
    draft = _create_ai_draft(client)
    rejected = client.post(
        f"/entries/{draft['id']}/patient-facing/reject", headers=CLINICIAN
    )

    assert rejected.status_code == 200
    assert rejected.json()["patient_facing_status"] == "rejected"
    assert rejected.json()["approved_by"] is None
    assert draft["id"] not in {entry["id"] for entry in _patient_entries(client)}


def test_editing_approved_instruction_invalidates_approval_and_preserves_version(
    client: TestClient,
) -> None:
    original = "AI-derived synthetic instruction before clinician review."
    edited = "Edited synthetic instruction requiring a new clinician review."
    draft = _create_ai_draft(client, original)
    assert client.post(
        f"/entries/{draft['id']}/patient-facing/approve", headers=CLINICIAN
    ).status_code == 200

    response = client.patch(
        f"/entries/{draft['id']}",
        headers=CLINICIAN,
        json={"content": edited, "expected_version": 1},
    )

    assert response.status_code == 200
    assert response.json()["patient_facing_status"] == "draft"
    assert response.json()["approved_by"] is None
    assert response.json()["approved_at"] is None
    assert draft["id"] not in {entry["id"] for entry in _patient_entries(client)}
    versions = client.get(
        f"/entries/{draft['id']}/versions", headers=CLINICIAN
    ).json()
    assert [version["version_number"] for version in versions] == [2, 1]
    assert versions[1]["content"] == original
    assert versions[0]["content"] == edited


def test_approval_actions_are_metadata_only(client: TestClient) -> None:
    secret = "Synthetic instruction secret S1234567A 91234567"
    draft = _create_ai_draft(client, secret)
    client.post(f"/entries/{draft['id']}/patient-facing/approve", headers=CLINICIAN)
    client.patch(
        f"/entries/{draft['id']}",
        headers=CLINICIAN,
        json={"content": f"{secret} edited", "expected_version": 1},
    )
    client.post(f"/entries/{draft['id']}/patient-facing/reject", headers=CLINICIAN)

    logs = client.get(f"/entries/{draft['id']}/audit", headers=CLINICIAN).json()
    actions = {row["action"] for row in logs}
    assert {
        "patient_instruction.approved",
        "patient_instruction.approval_invalidated",
        "patient_instruction.rejected",
    } <= actions
    trust_logs = [row for row in logs if row["action"].startswith("patient_instruction.")]
    assert all(set(row["metadata"]) == {"from_status", "to_status"} for row in trust_logs)
    transitions = {row["action"]: row["metadata"] for row in trust_logs}
    assert transitions["patient_instruction.approved"] == {
        "from_status": "draft",
        "to_status": "approved",
    }
    assert transitions["patient_instruction.approval_invalidated"] == {
        "from_status": "approved",
        "to_status": "draft",
    }
    assert transitions["patient_instruction.rejected"] == {
        "from_status": "draft",
        "to_status": "rejected",
    }
    serialized = json.dumps(trust_logs)
    assert secret not in serialized
    assert "S1234567A" not in serialized
    assert "91234567" not in serialized


def test_broken_provenance_cannot_be_approved(client: TestClient) -> None:
    draft = _create_ai_draft(client)
    override = app.dependency_overrides[get_db]
    db_iterator = override()
    db = next(db_iterator)
    try:
        entry = db.get(TimelineEntry, draft["id"])
        assert entry is not None
        entry.provenance_pointer = "timeline-entry-missing"
        db.commit()
    finally:
        db_iterator.close()

    response = client.post(
        f"/entries/{draft['id']}/patient-facing/approve", headers=CLINICIAN
    )
    assert response.status_code == 422
    assert "Needs review" in response.json()["detail"]
    assert draft["id"] not in {entry["id"] for entry in _patient_entries(client)}


def test_manual_clinician_instruction_remains_inherently_approved(
    client: TestClient,
) -> None:
    instruction = next(
        entry for entry in _patient_entries(client) if entry["id"] == "entry-demo-006"
    )
    assert instruction["patient_facing_status"] == "approved"
    assert instruction["approved_by"] == "clinician-demo-001"
    assert instruction["ai_derived"] is False


def test_patient_internal_restrictions_remain_enforced(client: TestClient) -> None:
    draft = _create_ai_draft(client)
    entries = _patient_entries(client)
    assert all(not entry["type"].startswith("ai_") for entry in entries)
    assert all(entry["type"] == "instruction" for entry in entries)
    assert client.get(
        f"/entries/{draft['id']}/comments", headers=PATIENT
    ).status_code == 403
    assert client.get(
        f"/entries/{draft['id']}/audit", headers=PATIENT
    ).status_code == 403
    assert client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=PATIENT
    ).status_code == 403


def test_approval_respects_clinic_scope(client: TestClient) -> None:
    draft = _create_ai_draft(client)
    other_clinic_clinician = {
        "X-User-Id": "clinician-other-001",
        "X-Role": "clinician",
        "X-Clinic-Id": "clinic-demo-002",
    }
    response = client.post(
        f"/entries/{draft['id']}/patient-facing/approve",
        headers=other_clinic_clinician,
    )
    assert response.status_code == 403
    assert OTHER_CLINIC_PATIENT_ID != SYNTHETIC_PATIENT_ID
    assert client.get(f"/entries/{draft['id']}/audit", headers=CLINICIAN).json() == []
