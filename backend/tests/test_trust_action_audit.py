import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import AuditLog
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
PATIENT = {
    "X-User-Id": SYNTHETIC_PATIENT_ID,
    "X-Role": "patient",
    "X-Clinic-Id": "clinic-demo-001",
}


def audit_rows() -> list[AuditLog]:
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        return list(db.scalars(select(AuditLog).order_by(AuditLog.timestamp, AuditLog.id)))
    finally:
        generator.close()


def entity_audits(entity_id: str) -> list[AuditLog]:
    return [row for row in audit_rows() if row.entity_id == entity_id]


def create_conflict(client: TestClient, marker: str = "") -> dict:
    ai = client.post(
        "/ai-scribe",
        headers=CLINICIAN,
        json={
            "patient_id": SYNTHETIC_PATIENT_ID,
            "interaction_type": "doctor_consult",
            "source_id": f"audit-conflict-source-{marker or 'base'}",
            "transcript": f"{marker} Lisinopril increased to 20 mg daily.",
            "synthetic": True,
        },
    )
    assert ai.status_code == 201
    clinician = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINICIAN,
        json={
            "type": "clinician_note",
            "content": f"{marker} Continue Lisinopril 10 mg daily.",
        },
    )
    assert clinician.status_code == 201
    conflicts = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN
    ).json()
    return next(item for item in conflicts if item["authoritative_entry_id"] == clinician.json()["id"])


def test_accept_highlight_creates_one_metadata_audit_event(client: TestClient) -> None:
    first = client.post("/highlights/highlight-demo-lab/accept", headers=CLINICIAN)
    repeated = client.post("/highlights/highlight-demo-lab/accept", headers=CLINICIAN)

    assert first.status_code == repeated.status_code == 200
    rows = entity_audits("highlight-demo-lab")
    assert [(row.action, row.entity_type) for row in rows] == [
        ("highlight.accepted", "highlight")
    ]
    assert rows[0].actor_id == "clinician-demo-001"
    assert rows[0].actor_role == "clinician"
    assert rows[0].metadata_json == {"from_status": "suggested", "to_status": "accepted"}


def test_reject_highlight_creates_one_metadata_audit_event(client: TestClient) -> None:
    first = client.post("/highlights/highlight-demo-follow-up/reject", headers=CLINICIAN)
    repeated = client.post("/highlights/highlight-demo-follow-up/reject", headers=CLINICIAN)

    assert first.status_code == repeated.status_code == 200
    rows = entity_audits("highlight-demo-follow-up")
    assert [row.action for row in rows] == ["highlight.rejected"]
    assert rows[0].metadata_json == {"from_status": "suggested", "to_status": "rejected"}


def test_resolve_and_unresolve_comment_create_audit_events(client: TestClient) -> None:
    resolved = client.patch(
        "/comments/comment-demo-001/resolution",
        headers=STAFF,
        json={"resolved": True},
    )
    repeated = client.patch(
        "/comments/comment-demo-001/resolution",
        headers=STAFF,
        json={"resolved": True},
    )
    unresolved = client.patch(
        "/comments/comment-demo-001/resolution",
        headers=CLINICIAN,
        json={"resolved": False},
    )

    assert resolved.status_code == repeated.status_code == unresolved.status_code == 200
    rows = entity_audits("comment-demo-001")
    assert [row.action for row in rows] == ["comment.resolved", "comment.unresolved"]
    assert [row.actor_role for row in rows] == ["staff", "clinician"]


def test_complete_and_reopen_assignment_create_audit_events(client: TestClient) -> None:
    completed = client.patch(
        "/assignments/assignment-demo-lab",
        headers=STAFF,
        json={"status": "completed"},
    )
    repeated = client.patch(
        "/assignments/assignment-demo-lab",
        headers=STAFF,
        json={"status": "completed"},
    )
    reopened = client.patch(
        "/assignments/assignment-demo-lab",
        headers=CLINICIAN,
        json={"status": "open"},
    )

    assert completed.status_code == repeated.status_code == reopened.status_code == 200
    rows = entity_audits("assignment-demo-lab")
    assert [row.action for row in rows] == ["assignment.completed", "assignment.reopened"]
    assert [row.entity_type for row in rows] == ["task_assignment", "task_assignment"]


def test_resolving_conflict_creates_one_audit_event(client: TestClient) -> None:
    conflict = create_conflict(client)
    first = client.post(f"/conflicts/{conflict['id']}/resolve", headers=CLINICIAN)
    repeated = client.post(f"/conflicts/{conflict['id']}/resolve", headers=CLINICIAN)

    assert first.status_code == repeated.status_code == 200
    rows = entity_audits(conflict["id"])
    assert [row.action for row in rows] == ["conflict.resolved"]
    assert rows[0].entity_type == "conflict_record"
    assert rows[0].metadata_json == {"from_status": "open", "to_status": "resolved"}


def test_audit_records_never_contain_clinical_or_collaboration_content(
    client: TestClient,
) -> None:
    secrets = [
        "COMMENT_SECRET_CONTENT",
        "HIGHLIGHT_SECRET_CLINICAL_TEXT",
        "ASSIGNMENT_SECRET_TITLE",
        "TRANSCRIPT_SECRET_CONTENT",
    ]
    comment = client.post(
        "/entries/entry-demo-006/comments",
        headers=CLINICIAN,
        json={"content": secrets[0]},
    ).json()
    client.patch(
        f"/comments/{comment['id']}/resolution",
        headers=CLINICIAN,
        json={"resolved": True},
    )
    highlight = client.post(
        "/entries/entry-demo-006/highlights",
        headers=CLINICIAN,
        json={
            "source_span": "Penicillin allergy remains active.",
            "text": secrets[1],
            "risk_level": "high",
            "risk_reason": "Synthetic reason",
            "unresolved_action": False,
            "clinical_entity_type": "allergy",
        },
    ).json()["highlight"]
    client.post(f"/highlights/{highlight['id']}/accept", headers=CLINICIAN)
    assignment = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/assignments",
        headers=CLINICIAN,
        json={"title": secrets[2], "assigned_role": "clinician"},
    ).json()
    client.patch(
        f"/assignments/{assignment['id']}",
        headers=CLINICIAN,
        json={"status": "completed"},
    )
    conflict = create_conflict(client, secrets[3])
    client.post(f"/conflicts/{conflict['id']}/resolve", headers=CLINICIAN)

    serialized_audit = json.dumps(
        [
            {
                "actor_id": row.actor_id,
                "actor_role": row.actor_role,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "metadata": row.metadata_json,
            }
            for row in audit_rows()
        ]
    )
    assert all(secret not in serialized_audit for secret in secrets)
    assert all(set(row.metadata_json) == {"from_status", "to_status"} for row in audit_rows())


def test_unauthorized_operations_do_not_create_success_audits(client: TestClient) -> None:
    conflict = create_conflict(client, "UNAUTHORIZED_SOURCE")
    attempts = [
        client.post("/highlights/highlight-demo-lab/accept", headers=STAFF),
        client.patch(
            "/comments/comment-demo-001/resolution",
            headers=PATIENT,
            json={"resolved": True},
        ),
        client.patch(
            "/assignments/assignment-demo-lab",
            headers=PATIENT,
            json={"status": "completed"},
        ),
        client.post(f"/conflicts/{conflict['id']}/resolve", headers=PATIENT),
    ]

    assert all(response.status_code == 403 for response in attempts)
    protected_ids = {
        "highlight-demo-lab",
        "comment-demo-001",
        "assignment-demo-lab",
        conflict["id"],
    }
    assert not [row for row in audit_rows() if row.entity_id in protected_ids]
