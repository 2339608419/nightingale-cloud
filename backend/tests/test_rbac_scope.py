from fastapi.testclient import TestClient

from app.services.seed import OTHER_CLINIC_PATIENT_ID, SYNTHETIC_PATIENT_ID


def identity(user_id: str, role: str, clinic_id: str = "clinic-demo-001") -> dict[str, str]:
    return {
        "X-User-Id": user_id,
        "X-Role": role,
        "X-Clinic-Id": clinic_id,
    }


STAFF = identity("staff-demo-001", "staff")
CLINICIAN = identity("clinician-demo-001", "clinician")
PATIENT = identity(SYNTHETIC_PATIENT_ID, "patient")


def test_staff_cannot_write_or_edit_clinician_notes(client: TestClient) -> None:
    create_response = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=STAFF,
        json={"type": "clinician_note", "content": "Unauthorized clinician note"},
    )
    edit_response = client.patch(
        "/entries/entry-demo-001",
        headers=STAFF,
        json={"content": "Unauthorized overwrite", "expected_version": 1},
    )

    assert create_response.status_code == 403
    assert edit_response.status_code == 403


def test_clinician_cannot_overwrite_staff_notes(client: TestClient) -> None:
    response = client.patch(
        "/entries/entry-demo-003",
        headers=CLINICIAN,
        json={"content": "Unauthorized staff overwrite", "expected_version": 1},
    )
    assert response.status_code == 403


def test_patient_cannot_access_raw_ai_scribed_notes(client: TestClient) -> None:
    response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=PATIENT,
    )
    assert response.status_code == 200
    assert response.json()
    assert {entry["type"] for entry in response.json()} == {"instruction"}
    assert all(not entry["type"].startswith("ai_") for entry in response.json())


def test_patient_cannot_access_internal_comments(client: TestClient) -> None:
    patient_response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/internal-comments",
        headers=PATIENT,
    )
    clinician_response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/internal-comments",
        headers=CLINICIAN,
    )

    assert patient_response.status_code == 403
    assert clinician_response.status_code == 200
    assert clinician_response.json() == []


def test_staff_and_clinician_cannot_access_other_clinic(client: TestClient) -> None:
    for headers in (STAFF, CLINICIAN):
        assert client.get(f"/patients/{OTHER_CLINIC_PATIENT_ID}", headers=headers).status_code == 403
        assert (
            client.get(f"/patients/{OTHER_CLINIC_PATIENT_ID}/entries", headers=headers).status_code
            == 403
        )


def test_staff_and_clinician_can_create_and_edit_only_their_note_types(
    client: TestClient,
) -> None:
    staff_created = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=STAFF,
        json={"type": "staff_note", "content": "Synthetic staff update"},
    )
    assert staff_created.status_code == 201
    assert staff_created.json()["author_role"] == "staff"
    assert client.patch(
        f"/entries/{staff_created.json()['id']}",
        headers=STAFF,
        json={"content": "Synthetic staff update edited", "expected_version": 1},
    ).status_code == 200

    clinician_created = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINICIAN,
        json={"type": "clinician_note", "content": "Synthetic clinician update"},
    )
    assert clinician_created.status_code == 201
    assert clinician_created.json()["author_role"] == "clinician"
    assert client.patch(
        f"/entries/{clinician_created.json()['id']}",
        headers=CLINICIAN,
        json={"content": "Synthetic clinician update edited", "expected_version": 1},
    ).status_code == 200


def test_protected_endpoint_requires_development_identity(client: TestClient) -> None:
    client.headers.clear()
    assert client.get(f"/patients/{SYNTHETIC_PATIENT_ID}").status_code == 401
