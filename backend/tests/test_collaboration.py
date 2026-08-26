from fastapi.testclient import TestClient

from app.services.seed import SYNTHETIC_PATIENT_ID


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
PATIENT = {
    "X-User-Id": SYNTHETIC_PATIENT_ID,
    "X-Role": "patient",
    "X-Clinic-Id": "clinic-demo-001",
}


def test_comment_creation_extracts_mentions(client: TestClient) -> None:
    response = client.post(
        "/entries/entry-demo-006/comments",
        headers=CLINICIAN,
        json={"content": "@nurse_amy please arrange repeat blood test with @lab_team."},
    )

    assert response.status_code == 201
    assert response.json()["author_id"] == "clinician-demo-001"
    assert response.json()["author_role"] == "clinician"
    assert response.json()["mentions"] == ["nurse_amy", "lab_team"]
    assert response.json()["resolved"] is False


def test_thread_retrieval_includes_replies(client: TestClient) -> None:
    root = client.post(
        "/entries/entry-demo-006/comments",
        headers=CLINICIAN,
        json={"content": "Please confirm the repeat test."},
    ).json()
    reply_response = client.post(
        "/entries/entry-demo-006/comments",
        headers=STAFF,
        json={"content": "@clinician-demo-001 confirmed.", "parent_comment_id": root["id"]},
    )

    assert reply_response.status_code == 201
    assert reply_response.json()["parent_comment_id"] == root["id"]
    thread = client.get("/entries/entry-demo-006/comments", headers=CLINICIAN).json()
    assert [comment["id"] for comment in thread] == [root["id"], reply_response.json()["id"]]


def test_comment_can_be_resolved_and_unresolved(client: TestClient) -> None:
    comment = client.post(
        "/entries/entry-demo-006/comments",
        headers=CLINICIAN,
        json={"content": "Resolve after review."},
    ).json()

    resolved = client.patch(
        f"/comments/{comment['id']}/resolution",
        headers=STAFF,
        json={"resolved": True},
    )
    unresolved = client.patch(
        f"/comments/{comment['id']}/resolution",
        headers=CLINICIAN,
        json={"resolved": False},
    )

    assert resolved.status_code == 200
    assert resolved.json()["resolved"] is True
    assert unresolved.status_code == 200
    assert unresolved.json()["resolved"] is False


def test_patient_cannot_access_or_create_internal_comments(client: TestClient) -> None:
    assert client.get("/entries/entry-demo-006/comments", headers=PATIENT).status_code == 403
    assert client.post(
        "/entries/entry-demo-006/comments",
        headers=PATIENT,
        json={"content": "Patient should not create an internal comment"},
    ).status_code == 403


def test_open_assignments_can_be_created_and_completed(client: TestClient) -> None:
    seeded = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/assignments",
        headers=STAFF,
    )
    assert seeded.status_code == 200
    assert len(seeded.json()) == 3
    assert all(assignment["status"] == "open" for assignment in seeded.json())

    created = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/assignments",
        headers=CLINICIAN,
        json={
            "title": "Review repeat result",
            "entry_id": "entry-demo-006",
            "assigned_role": "clinician",
        },
    )
    assert created.status_code == 201
    completed = client.patch(
        f"/assignments/{created.json()['id']}",
        headers=STAFF,
        json={"status": "completed"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert completed.json()["resolved_at"] is not None


def test_patient_cannot_access_open_assignments(client: TestClient) -> None:
    assert client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/assignments",
        headers=PATIENT,
    ).status_code == 403
