from fastapi.testclient import TestClient

from app.services.seed import SYNTHETIC_PATIENT_ID


ALLOWED_ROLES = {"patient", "staff", "clinician", "system"}
ALLOWED_TYPES = {
    "clinician_note",
    "staff_note",
    "ai_doctor_consult_summary",
    "ai_nurse_consult_summary",
    "ai_patient_session_summary",
    "system_event",
    "instruction",
    "admin",
}


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
    assert len(entries) == 8
    timestamps = [entry["timestamp"] for entry in entries]
    assert timestamps == sorted(timestamps, reverse=True)
    assert entries[0]["id"] == "entry-demo-008"
    assert all(entry["patient_id"] == SYNTHETIC_PATIENT_ID for entry in entries)
    assert all(entry["provenance_pointer"] for entry in entries)


def test_entries_have_supported_roles_types_and_required_fields(client: TestClient) -> None:
    entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries").json()
    required_fields = {
        "id",
        "patient_id",
        "author_role",
        "author_id",
        "timestamp",
        "type",
        "content",
        "provenance_pointer",
        "version",
    }

    assert all(set(entry) == required_fields for entry in entries)
    assert {entry["author_role"] for entry in entries} <= ALLOWED_ROLES
    assert {entry["type"] for entry in entries} <= ALLOWED_TYPES
    assert {
        "clinician_note",
        "staff_note",
        "ai_doctor_consult_summary",
        "ai_nurse_consult_summary",
        "ai_patient_session_summary",
    } <= {entry["type"] for entry in entries}


def test_entries_span_required_longitudinal_dates(client: TestClient) -> None:
    entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries").json()
    dates = {entry["timestamp"][:10] for entry in entries}

    assert "2025-04-15" in dates
    assert "2026-02-06" in dates
    assert any(date >= "2026-08-20" for date in dates)


def test_missing_patient_returns_404(client: TestClient) -> None:
    assert client.get("/patients/missing").status_code == 404
    assert client.get("/patients/missing/entries").status_code == 404
