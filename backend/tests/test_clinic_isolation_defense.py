import json
from collections.abc import Generator
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import AuditLog, ImportancePreference
from app.routes import ai_scribe as ai_scribe_routes
from app.routes import collaboration as collaboration_routes
from app.routes import conflicts as conflicts_routes
from app.routes import entries as entries_routes
from app.routes import highlights as highlights_routes
from app.routes import patients as patients_routes
from app.services.seed import OTHER_CLINIC_PATIENT_ID, SYNTHETIC_PATIENT_ID


CLINIC_A = {
    "X-User-Id": "clinician-demo-001",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-001",
}
CLINIC_B = {
    "X-User-Id": "clinician-demo-002",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-002",
}
CLINIC_A_ENTRY = "entry-demo-001"
CLINIC_A_HIGHLIGHT = "highlight-demo-lab"
CLINIC_A_SECRET_MARKERS = ("Maya", "Penicillin", "Lisinopril", "potassium")


@contextmanager
def database_session() -> Generator:
    override = app.dependency_overrides[get_db]
    generator = override()
    db = next(generator)
    try:
        yield db
    finally:
        generator.close()


def audit_snapshot() -> str:
    with database_session() as db:
        rows = db.scalars(select(AuditLog).order_by(AuditLog.id)).all()
        return json.dumps(
            [
                {
                    "id": row.id,
                    "action": row.action,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "metadata": row.metadata_json,
                }
                for row in rows
            ],
            sort_keys=True,
        )


def disable_outer_clinic_guard(monkeypatch: pytest.MonkeyPatch) -> None:
    def no_op_guard(_user, _patient) -> None:
        return None

    for module in (
        patients_routes,
        entries_routes,
        collaboration_routes,
        highlights_routes,
        conflicts_routes,
        ai_scribe_routes,
    ):
        monkeypatch.setattr(module, "require_patient_access", no_op_guard)


def create_targets(client: TestClient) -> dict[str, str]:
    comments = client.get(
        "/entries/entry-demo-007/comments", headers=CLINIC_A
    ).json()
    assignments = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/assignments", headers=CLINIC_A
    ).json()
    assert comments and assignments

    ai_entry = client.post(
        "/ai-scribe",
        headers=CLINIC_A,
        json={
            "patient_id": SYNTHETIC_PATIENT_ID,
            "interaction_type": "doctor_consult",
            "source_id": "tenant-defense-conflict-source",
            "transcript": "Lisinopril increased to 20 mg daily.",
            "synthetic": True,
        },
    )
    assert ai_entry.status_code == 201
    clinician_note = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINIC_A,
        json={
            "type": "clinician_note",
            "content": "Continue Lisinopril 10 mg daily.",
        },
    )
    assert clinician_note.status_code == 201
    conflicts = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINIC_A
    ).json()
    assert conflicts

    draft = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINIC_A,
        json={
            "type": "instruction",
            "content": "Repeat synthetic labs next week.",
            "ai_derived": True,
            "source_entry_id": "entry-demo-004",
        },
    )
    assert draft.status_code == 201
    return {
        "comment": comments[0]["id"],
        "assignment": assignments[0]["id"],
        "conflict": conflicts[0]["id"],
        "instruction": draft.json()["id"],
    }


CROSS_CLINIC_CASES = (
    "patient_read",
    "timeline_read",
    "decay_read",
    "highlight_list",
    "entry_edit",
    "versions_read",
    "audit_read",
    "comments_read",
    "comment_create",
    "comment_resolve",
    "assignments_read",
    "assignment_complete",
    "highlight_accept",
    "conflicts_read",
    "conflict_resolve",
    "instruction_approve",
    "ai_scribe_create",
)


def cross_clinic_request(
    client: TestClient, case: str, targets: dict[str, str]
):
    if case == "patient_read":
        return client.get(f"/patients/{SYNTHETIC_PATIENT_ID}", headers=CLINIC_B)
    if case == "timeline_read":
        return client.get(
            f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINIC_B
        )
    if case == "decay_read":
        return client.get(
            f"/patients/{SYNTHETIC_PATIENT_ID}/decay-preview", headers=CLINIC_B
        )
    if case == "highlight_list":
        return client.get(
            f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINIC_B
        )
    if case == "entry_edit":
        return client.patch(
            f"/entries/{CLINIC_A_ENTRY}",
            headers=CLINIC_B,
            json={"content": "Cross-clinic overwrite", "expected_version": 1},
        )
    if case == "versions_read":
        return client.get(f"/entries/{CLINIC_A_ENTRY}/versions", headers=CLINIC_B)
    if case == "audit_read":
        return client.get(f"/entries/{CLINIC_A_ENTRY}/audit", headers=CLINIC_B)
    if case == "comments_read":
        return client.get("/entries/entry-demo-007/comments", headers=CLINIC_B)
    if case == "comment_create":
        return client.post(
            "/entries/entry-demo-007/comments",
            headers=CLINIC_B,
            json={"content": "Cross-clinic comment"},
        )
    if case == "comment_resolve":
        return client.patch(
            f"/comments/{targets['comment']}/resolution",
            headers=CLINIC_B,
            json={"resolved": True},
        )
    if case == "assignments_read":
        return client.get(
            f"/patients/{SYNTHETIC_PATIENT_ID}/assignments", headers=CLINIC_B
        )
    if case == "assignment_complete":
        return client.patch(
            f"/assignments/{targets['assignment']}",
            headers=CLINIC_B,
            json={"status": "completed"},
        )
    if case == "highlight_accept":
        return client.post(
            f"/highlights/{CLINIC_A_HIGHLIGHT}/accept", headers=CLINIC_B
        )
    if case == "conflicts_read":
        return client.get(
            f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINIC_B
        )
    if case == "conflict_resolve":
        return client.post(
            f"/conflicts/{targets['conflict']}/resolve", headers=CLINIC_B
        )
    if case == "instruction_approve":
        return client.post(
            f"/entries/{targets['instruction']}/patient-facing/approve",
            headers=CLINIC_B,
        )
    if case == "ai_scribe_create":
        return client.post(
            "/ai-scribe",
            headers=CLINIC_B,
            json={
                "patient_id": SYNTHETIC_PATIENT_ID,
                "interaction_type": "doctor_consult",
                "source_id": "cross-clinic-known-id",
                "transcript": "Penicillin allergy remains active.",
                "synthetic": True,
            },
        )
    raise AssertionError(f"Unknown test case: {case}")


@pytest.mark.parametrize("case", CROSS_CLINIC_CASES)
def test_inner_scope_blocks_known_clinic_a_ids_when_outer_guard_is_no_op(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    case: str,
) -> None:
    targets = create_targets(client)
    before_audit = audit_snapshot()
    before_entries = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINIC_A
    ).json()
    disable_outer_clinic_guard(monkeypatch)

    response = cross_clinic_request(client, case, targets)

    assert response.status_code == 404
    assert response.json()["detail"] in {
        "Patient not found",
        "Entry not found",
        "Comment not found",
        "Assignment not found",
        "Highlight not found",
        "Conflict not found",
    }
    assert all(marker not in response.text for marker in CLINIC_A_SECRET_MARKERS)
    assert audit_snapshot() == before_audit
    after_entries = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINIC_A
    ).json()
    assert after_entries == before_entries


def test_same_clinic_access_still_works_when_outer_guard_is_no_op(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    disable_outer_clinic_guard(monkeypatch)

    patient = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}", headers=CLINIC_A)
    entries = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINIC_A
    )

    assert patient.status_code == 200
    assert entries.status_code == 200
    assert entries.json()


def test_cross_tenant_assignment_entry_injection_is_rejected(
    client: TestClient,
) -> None:
    before = client.get(
        f"/patients/{OTHER_CLINIC_PATIENT_ID}/assignments", headers=CLINIC_B
    ).json()

    response = client.post(
        f"/patients/{OTHER_CLINIC_PATIENT_ID}/assignments",
        headers=CLINIC_B,
        json={
            "title": "Synthetic cross-tenant association attempt",
            "entry_id": CLINIC_A_ENTRY,
            "assigned_role": "staff",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Assignment entry must belong to the patient"
    after = client.get(
        f"/patients/{OTHER_CLINIC_PATIENT_ID}/assignments", headers=CLINIC_B
    ).json()
    assert after == before


def test_importance_preferences_query_is_directly_clinic_scoped(
    client: TestClient,
) -> None:
    with database_session() as db:
        db.add_all(
            [
                ImportancePreference(
                    id="preference-clinic-a-test",
                    clinic_id="clinic-demo-001",
                    category_type="entity",
                    category_value="clinic_a_only",
                    accepted_count=9,
                    rejected_count=0,
                ),
                ImportancePreference(
                    id="preference-clinic-b-test",
                    clinic_id="clinic-demo-002",
                    category_type="entity",
                    category_value="clinic_b_only",
                    accepted_count=1,
                    rejected_count=0,
                ),
            ]
        )
        db.commit()

    response = client.get("/importance-preferences", headers=CLINIC_B)

    assert response.status_code == 200
    values = {item["category_value"] for item in response.json()}
    assert "clinic_b_only" in values
    assert "clinic_a_only" not in values
