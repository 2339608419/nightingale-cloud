from fastapi.testclient import TestClient

from app.models import ConflictEntityType
from app.services.conflict_service import extract_clinical_facts
from app.services.seed import SYNTHETIC_PATIENT_ID


CLINICIAN = {
    "X-User-Id": "clinician-demo-001",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-001",
}
PATIENT = {
    "X-User-Id": SYNTHETIC_PATIENT_ID,
    "X-Role": "patient",
    "X-Clinic-Id": "clinic-demo-001",
}


def ingest_ai_medication(client: TestClient, dose: int = 20) -> dict:
    response = client.post(
        "/ai-scribe",
        headers=CLINICIAN,
        json={
            "patient_id": SYNTHETIC_PATIENT_ID,
            "interaction_type": "doctor_consult",
            "source_id": f"conflict-source-lisinopril-{dose}",
            "transcript": f"Lisinopril increased to {dose} mg daily.",
            "synthetic": True,
        },
    )
    assert response.status_code == 201
    return response.json()["timeline_entry"]


def create_clinician_note(client: TestClient, content: str) -> dict:
    response = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINICIAN,
        json={"type": "clinician_note", "content": content},
    )
    assert response.status_code == 201
    return response.json()


def test_conflicting_clinician_ai_medication_creates_open_conflict(
    client: TestClient,
) -> None:
    ai_entry = ingest_ai_medication(client, 20)
    clinician_entry = create_clinician_note(client, "Continue Lisinopril 10 mg daily.")

    response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN
    )

    assert response.status_code == 200
    conflict = response.json()[0]
    assert conflict["status"] == "open"
    assert conflict["entity_type"] == "medication"
    assert conflict["entity_name"] == "lisinopril"
    assert conflict["prior_value"] == "20 mg daily"
    assert conflict["authoritative_value"] == "10 mg daily"
    assert conflict["conflicting_entry_id"] == ai_entry["id"]
    assert conflict["authoritative_entry_id"] == clinician_entry["id"]


def test_identical_information_does_not_create_conflict(client: TestClient) -> None:
    ingest_ai_medication(client, 20)
    create_clinician_note(client, "Continue Lisinopril 20 mg daily.")

    response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN
    )

    assert response.status_code == 200
    assert response.json() == []


def test_clinician_entry_is_authoritative_and_prior_entry_is_preserved(
    client: TestClient,
) -> None:
    ai_entry = ingest_ai_medication(client, 20)
    clinician_entry = create_clinician_note(client, "Continue Lisinopril 10 mg daily.")

    entries = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINICIAN
    ).json()
    by_id = {entry["id"]: entry for entry in entries}

    assert by_id[clinician_entry["id"]]["content"] == "Continue Lisinopril 10 mg daily."
    assert by_id[clinician_entry["id"]]["author_role"] == "clinician"
    assert "Lisinopril increased to 20 mg daily." in by_id[ai_entry["id"]]["content"]


def test_both_conflict_provenance_references_resolve(client: TestClient) -> None:
    ai_entry = ingest_ai_medication(client, 20)
    clinician_entry = create_clinician_note(client, "Continue Lisinopril 10 mg daily.")
    conflict = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN
    ).json()[0]
    entries = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINICIAN
    ).json()
    entry_ids = {entry["id"] for entry in entries}

    assert conflict["authoritative_entry_id"] == clinician_entry["id"] in entry_ids
    assert conflict["conflicting_entry_id"] == ai_entry["id"] in entry_ids
    assert conflict["authoritative_provenance_pointer"] == (
        f"timeline-entry-{clinician_entry['id']}"
    )
    assert conflict["conflicting_provenance_pointer"] == f"timeline-entry-{ai_entry['id']}"


def test_clinician_edit_detects_conflict_and_can_resolve_it(client: TestClient) -> None:
    ingest_ai_medication(client, 20)
    edited = client.patch(
        "/entries/entry-demo-001",
        headers=CLINICIAN,
        json={"content": "Continue Lisinopril 10 mg daily.", "expected_version": 1},
    )
    assert edited.status_code == 200
    conflicts = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN
    ).json()
    conflict = next(
        item for item in conflicts if item["authoritative_entry_id"] == "entry-demo-001"
    )

    resolved = client.post(f"/conflicts/{conflict['id']}/resolve", headers=CLINICIAN)

    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["resolved_at"] is not None


def test_patient_cannot_access_internal_conflicts(client: TestClient) -> None:
    assert client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=PATIENT
    ).status_code == 403


def test_conflicts_respect_clinic_scope(client: TestClient) -> None:
    other_clinic_clinician = {
        "X-User-Id": "clinician-other-001",
        "X-Role": "clinician",
        "X-Clinic-Id": "clinic-demo-002",
    }
    assert client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts",
        headers=other_clinic_clinician,
    ).status_code == 403


def test_demo_extractor_supports_allergy_and_follow_up_status() -> None:
    facts = extract_clinical_facts(
        "No penicillin allergy. Nurse follow-up completed."
    )
    values = {(fact.entity_type, fact.entity_name): fact.value for fact in facts}

    assert values[(ConflictEntityType.ALLERGY, "penicillin")] == "none"
    assert values[(ConflictEntityType.FOLLOW_UP, "nurse follow-up")] == "resolved"
