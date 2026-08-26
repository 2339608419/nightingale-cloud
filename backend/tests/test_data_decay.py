from fastapi.testclient import TestClient

from app.services.seed import SYNTHETIC_PATIENT_ID


def test_decay_preview_is_reversible_and_preserves_durable_facts(client: TestClient) -> None:
    response = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/decay-preview")
    assert response.status_code == 200
    previews = {item["entry_id"]: item for item in response.json()}

    assert previews["entry-demo-001"]["storage_tier"] == "full_detail"
    assert previews["entry-demo-001"]["durable_exempt"] is True
    assert previews["entry-demo-002"]["storage_tier"] == "cold_summary"
    assert previews["entry-demo-002"]["original_available"] is True
    assert previews["entry-demo-007"]["storage_tier"] == "full_detail"
    assert all(item["provenance_pointer"] for item in previews.values())


def test_decay_preview_does_not_mutate_original_entries(client: TestClient) -> None:
    before = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries").json()
    client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/decay-preview")
    after = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries").json()

    assert after == before
