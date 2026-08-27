from fastapi.testclient import TestClient

from app.services.seed import SYNTHETIC_PATIENT_ID


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


def _create_note(
    client: TestClient, headers: dict[str, str], entry_type: str, content: str
) -> dict:
    response = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=headers,
        json={"type": entry_type, "content": content},
    )
    assert response.status_code == 201
    return response.json()


def _open_conflicts(client: TestClient) -> list[dict]:
    response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN
    )
    assert response.status_code == 200
    return response.json()


def _conflict_between(conflicts: list[dict], first_id: str, second_id: str) -> dict:
    expected = {first_id, second_id}
    return next(
        item
        for item in conflicts
        if {item["authoritative_entry_id"], item["conflicting_entry_id"]} == expected
    )


def test_staff_10mg_vs_clinician_20mg_creates_conflict_with_clinician_authority(
    client: TestClient,
) -> None:
    staff = _create_note(client, STAFF, "staff_note", "Lisinopril 10 mg daily.")
    clinician = _create_note(
        client, CLINICIAN, "clinician_note", "Continue Lisinopril 20 mg daily."
    )

    conflict = _conflict_between(_open_conflicts(client), staff["id"], clinician["id"])
    assert conflict["status"] == "open"
    assert conflict["entity_type"] == "medication"
    assert conflict["entity_name"] == "lisinopril"
    assert conflict["authoritative_entry_id"] == clinician["id"]
    assert conflict["authoritative_value"] == "20 mg daily"
    assert conflict["prior_value"] == "10 mg daily"
    assert conflict["authority_policy"] == "clinician_authoritative"
    assert conflict["requires_clinician_review"] is False


def test_staff_vs_staff_conflict_is_open_without_invented_authority(
    client: TestClient,
) -> None:
    first = _create_note(client, STAFF, "staff_note", "Lisinopril 10 mg daily.")
    second = _create_note(client, STAFF, "staff_note", "Lisinopril 20 mg daily.")

    conflict = _conflict_between(_open_conflicts(client), first["id"], second["id"])
    assert conflict["status"] == "open"
    assert conflict["authority_policy"] == "clinician_review_required"
    assert conflict["requires_clinician_review"] is True
    assert conflict["authoritative_role"] == "staff"
    assert conflict["conflicting_role"] == "staff"


def test_identical_human_facts_do_not_create_conflict(client: TestClient) -> None:
    first = _create_note(client, STAFF, "staff_note", "Metformin 500 mg twice daily.")
    second = _create_note(client, STAFF, "staff_note", "Metformin 500 mg twice daily.")

    assert not any(
        {item["authoritative_entry_id"], item["conflicting_entry_id"]}
        == {first["id"], second["id"]}
        for item in _open_conflicts(client)
    )


def test_human_conflict_sources_and_provenance_resolve(client: TestClient) -> None:
    staff = _create_note(client, STAFF, "staff_note", "Lisinopril 10 mg daily.")
    clinician = _create_note(
        client, CLINICIAN, "clinician_note", "Continue Lisinopril 20 mg daily."
    )
    conflict = _conflict_between(_open_conflicts(client), staff["id"], clinician["id"])
    entries = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINICIAN
    ).json()
    entry_ids = {entry["id"] for entry in entries}

    assert conflict["authoritative_entry_id"] in entry_ids
    assert conflict["conflicting_entry_id"] in entry_ids
    assert conflict["authoritative_provenance_pointer"] == (
        f"timeline-entry-{conflict['authoritative_entry_id']}"
    )
    assert conflict["conflicting_provenance_pointer"] == (
        f"timeline-entry-{conflict['conflicting_entry_id']}"
    )
