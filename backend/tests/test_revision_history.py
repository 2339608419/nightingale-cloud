from fastapi.testclient import TestClient


ENTRY_ID = "entry-demo-001"


def test_edit_increments_version_and_preserves_snapshot(client: TestClient) -> None:
    original = client.get("/patients/patient-demo-001/entries").json()
    original_content = next(item["content"] for item in original if item["id"] == ENTRY_ID)

    response = client.patch(
        f"/entries/{ENTRY_ID}",
        json={"content": "Updated synthetic clinician assessment.", "expected_version": 1},
    )

    assert response.status_code == 200
    assert response.json()["version"] == 2
    versions = client.get(f"/entries/{ENTRY_ID}/versions").json()
    assert [item["version_number"] for item in versions] == [2, 1]
    assert versions[1]["content"] == original_content


def test_revert_restores_prior_content_as_new_version(client: TestClient) -> None:
    original_content = next(
        item["content"]
        for item in client.get("/patients/patient-demo-001/entries").json()
        if item["id"] == ENTRY_ID
    )
    client.patch(
        f"/entries/{ENTRY_ID}",
        json={"content": "Temporary revised assessment.", "expected_version": 1},
    )

    response = client.post(f"/entries/{ENTRY_ID}/revert/1", json={"expected_version": 2})

    assert response.status_code == 200
    assert response.json()["content"] == original_content
    assert response.json()["version"] == 3
    assert [item["version_number"] for item in client.get(f"/entries/{ENTRY_ID}/versions").json()] == [3, 2, 1]


def test_audit_log_records_actor_and_metadata_without_content(client: TestClient) -> None:
    client.patch(
        f"/entries/{ENTRY_ID}",
        json={"content": "Metadata-safe synthetic update.", "expected_version": 1},
    )
    client.post(f"/entries/{ENTRY_ID}/revert/1", json={"expected_version": 2})

    logs = client.get(f"/entries/{ENTRY_ID}/audit").json()
    assert {item["action"] for item in logs} == {"entry.updated", "entry.reverted"}
    assert all(item["actor_id"] == "clinician-demo-001" for item in logs)
    assert all(item["actor_role"] == "clinician" for item in logs)
    assert all("content" not in item["metadata"] for item in logs)
    assert all(item["entity_type"] == "timeline_entry" for item in logs)
