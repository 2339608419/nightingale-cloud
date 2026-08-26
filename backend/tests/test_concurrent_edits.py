from fastapi.testclient import TestClient


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
    assert stale.json()["detail"]["current_version"] == 2
    entries = client.get("/patients/patient-demo-001/entries", headers=CLINICIAN).json()
    current = next(entry for entry in entries if entry["id"] == "entry-demo-001")
    assert current["content"] == "First accepted edit."
