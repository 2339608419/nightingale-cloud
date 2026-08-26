from fastapi.testclient import TestClient

from app.services.seed import SYNTHETIC_PATIENT_ID


def test_health(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_seeded_patient(client: TestClient) -> None:
    response = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}")
    assert response.status_code == 200
    assert response.json()["name"] == "Maya Chen (Synthetic)"
    assert response.json()["clinic_id"] == "clinic-demo-001"


def test_get_entries_newest_first(client: TestClient) -> None:
    response = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries")
    assert response.status_code == 200
    entries = response.json()
    assert len(entries) == 3
    assert entries[0]["id"] == "entry-demo-003"
    assert all(entry["patient_id"] == SYNTHETIC_PATIENT_ID for entry in entries)
    assert all(entry["provenance_pointer"] for entry in entries)


def test_missing_patient_returns_404(client: TestClient) -> None:
    assert client.get("/patients/missing").status_code == 404
    assert client.get("/patients/missing/entries").status_code == 404

