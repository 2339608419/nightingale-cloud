from fastapi.testclient import TestClient
from sqlalchemy import inspect

from app.database import get_db
from app.main import app
from app.models import AuditLog, ConflictProvenance, HighlightFeedback, ImportancePreference
from app.services.seed import SYNTHETIC_PATIENT_ID


CLINICIAN = {"X-User-Id": "clinician-one", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-001"}
CLINICIAN_TWO = {**CLINICIAN, "X-User-Id": "clinician-two"}
STAFF = {"X-User-Id": "nurse-amy", "X-Role": "staff", "X-Clinic-Id": "clinic-demo-001"}
PATIENT = {"X-User-Id": SYNTHETIC_PATIENT_ID, "X-Role": "patient", "X-Clinic-Id": "clinic-demo-001"}
CLINIC_B = {"X-User-Id": "clinic-b-clinician", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-002"}


def _db():
    iterator = app.dependency_overrides[get_db]()
    return iterator, next(iterator)


def _note(client: TestClient, headers: dict[str, str], kind: str, content: str) -> dict:
    response = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=headers,
        json={"type": kind, "content": content},
    )
    assert response.status_code == 201
    return response.json()


def _allergy_suggestion(client: TestClient, entry_id: str, span: str, text: str) -> dict:
    response = client.post(
        f"/entries/{entry_id}/highlights", headers=CLINICIAN,
        json={
            "source_span": span, "text": text, "risk_level": "low",
            "risk_reason": "Synthetic allergy review.", "unresolved_action": False,
            "clinical_entity_type": "allergy",
        },
    )
    assert response.status_code == 201
    return response.json()["highlight"]


def test_exact_nurse_then_ai_no_allergy_is_visible_safe_conflict(client: TestClient) -> None:
    nurse = _note(client, STAFF, "staff_note", "Penicillin allergy is active.")
    ai = client.post("/ai-scribe", headers=CLINICIAN, json={
        "patient_id": SYNTHETIC_PATIENT_ID, "interaction_type": "patient_session",
        "source_id": "phase5-allergy", "transcript": "No known allergies.", "synthetic": True,
    })
    assert ai.status_code == 201
    ai_entry = ai.json()["timeline_entry"]

    entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=CLINICIAN).json()
    assert {nurse["id"], ai_entry["id"]} <= {item["id"] for item in entries}
    conflicts = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN).json()
    conflict = next(item for item in conflicts if item["entity_name"] == "penicillin" and {item["authoritative_entry_id"], item["conflicting_entry_id"]} == {nurse["id"], ai_entry["id"]})
    assert conflict["authority_policy"] == "staff_authoritative"
    assert conflict["requires_clinician_review"] is False
    assert conflict["unresolved_requires_review"] is True
    assert conflict["status"] == "open"
    assert conflict["authoritative_version_number"] == 1
    assert conflict["conflicting_version_number"] == 1
    assert conflict["authoritative_version_pointer"].endswith("-v1")
    assert conflict["conflicting_version_pointer"].endswith("-v1")

    glance = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN).json()
    warning = next(item for item in glance if item["entry_id"] == nurse["id"])
    assert warning["risk_level"] == "high"
    assert warning["evidence_confidence_level"] == "abstain"
    assert warning["confidence_rule_triggered"] == "unresolved_conflict"
    assert warning["confidence_required_action"] == "resolve_conflict_before_trust"
    assert "Penicillin" not in " ".join(warning["confidence_inputs_evaluated"])

    assert client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=PATIENT).status_code == 403
    patient_entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=PATIENT).json()
    assert nurse["id"] not in {item["id"] for item in patient_entries}
    assert ai_entry["id"] not in {item["id"] for item in patient_entries}
    assert client.post(f"/conflicts/{conflict['id']}/resolve", headers=CLINIC_B).status_code in {403, 404}

    resolved = client.post(f"/conflicts/{conflict['id']}/resolve", headers=CLINICIAN)
    assert resolved.status_code == 200
    resolved_glance = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN
    ).json()
    resolved_warning = next(item for item in resolved_glance if item["entry_id"] == nurse["id"])
    assert resolved_warning["evidence_confidence_level"] == "high"
    assert resolved_warning["confidence_rule_triggered"] == "exact_structured_evidence"
    iterator, db = _db()
    try:
        immutable = db.get(ConflictProvenance, conflict["id"])
        assert immutable is not None
        assert immutable.authoritative_version_number == 1
        audit = db.query(AuditLog).filter(AuditLog.entity_id == conflict["id"]).one()
        assert audit.action == "conflict.resolved"
        assert set(audit.metadata_json) == {"from_status", "to_status"}
    finally:
        iterator.close()


def test_conflict_provenance_stays_bound_across_source_edit_and_revert(client: TestClient) -> None:
    nurse = _note(client, STAFF, "staff_note", "Penicillin allergy is active.")
    ai = client.post("/ai-scribe", headers=CLINICIAN, json={
        "patient_id": SYNTHETIC_PATIENT_ID, "interaction_type": "nurse_consult",
        "source_id": "phase5-version", "transcript": "No known allergies.", "synthetic": True,
    }).json()["timeline_entry"]
    conflict = next(item for item in client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts", headers=CLINICIAN
    ).json() if {item["authoritative_entry_id"], item["conflicting_entry_id"]} == {nurse["id"], ai["id"]})
    original_pointer = conflict["authoritative_version_pointer"]

    edited = client.patch(f"/entries/{nurse['id']}", headers=STAFF, json={
        "content": "Penicillin allergy is active; clinician review pending.", "expected_version": 1,
    })
    assert edited.status_code == 200
    reverted = client.post(f"/entries/{nurse['id']}/revert/1", headers=STAFF, json={"expected_version": 2})
    assert reverted.status_code == 200
    updated = next(item for item in client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/conflicts?status=open", headers=CLINICIAN
    ).json() if item["id"] == conflict["id"])
    assert updated["authoritative_version_number"] == 1
    assert updated["authoritative_version_pointer"] == original_pointer


def test_actor_feedback_negative_guard_change_undo_and_metadata(client: TestClient) -> None:
    entry = _note(client, CLINICIAN, "clinician_note", "Metformin 500 mg daily.")
    first = _allergy_suggestion(client, entry["id"], "Metformin 500 mg daily.", "Review synthetic category one")
    second = _allergy_suggestion(client, entry["id"], "Metformin 500 mg daily.", "Review synthetic category two")

    assert client.post(f"/highlights/{first['id']}/reject", headers=PATIENT).status_code == 403
    assert client.post(f"/highlights/{first['id']}/reject", headers=STAFF).status_code == 403

    assert client.post(f"/highlights/{first['id']}/reject", headers=CLINICIAN).status_code == 200
    policy = client.get("/importance-feedback-policy/allergy", headers=CLINICIAN).json()
    assert policy["negative_feedback_state"] == "suppressed"
    prefs = client.get("/importance-preferences", headers=CLINICIAN).json()
    allergy = next(item for item in prefs if item["category_type"] == "entity" and item["category_value"] == "allergy")
    assert allergy["rejected_count"] == 0

    assert client.post(f"/highlights/{second['id']}/reject", headers=CLINICIAN_TWO).status_code == 200
    assert client.get("/importance-feedback-policy/allergy", headers=CLINICIAN).json()["negative_feedback_state"] == "applied"
    allergy = next(item for item in client.get("/importance-preferences", headers=CLINICIAN).json() if item["category_type"] == "entity" and item["category_value"] == "allergy")
    assert allergy["rejected_count"] == 2

    undo = client.post(f"/highlights/{first['id']}/feedback/undo", headers=CLINICIAN)
    assert undo.status_code == 200 and undo.json()["status"] == "suggested"
    iterator, db = _db()
    try:
        audit_before = db.query(AuditLog).filter(AuditLog.action == "highlight.feedback_undone").count()
        feedback = db.query(HighlightFeedback).filter(HighlightFeedback.highlight_id == first["id"]).one()
        assert feedback.decision.value == "undone"
        assert not hasattr(feedback, "content")
        feedback_audits = db.query(AuditLog).filter(
            AuditLog.entity_id.in_([first["id"], second["id"]])
        ).all()
        assert feedback_audits
        serialized = " ".join(str(item.metadata_json) for item in feedback_audits)
        assert "Metformin" not in serialized
        assert "Review synthetic" not in serialized
        assert all(set(item.metadata_json) == {"from_status", "to_status"} for item in feedback_audits)
    finally:
        iterator.close()
    assert client.post(f"/highlights/{first['id']}/feedback/undo", headers=CLINICIAN).status_code == 200
    iterator, db = _db()
    try:
        assert db.query(AuditLog).filter(AuditLog.action == "highlight.feedback_undone").count() == audit_before
    finally:
        iterator.close()


def test_decision_change_replaces_one_actor_contribution_and_negative_cap(client: TestClient) -> None:
    entry = _note(client, CLINICIAN, "clinician_note", "Routine synthetic review note.")
    items = []
    for index in range(6):
        response = client.post(f"/entries/{entry['id']}/highlights", headers=CLINICIAN, json={
            "source_span": "Routine synthetic review note.", "text": f"Capped feedback {index}",
            "risk_level": "none", "risk_reason": "Synthetic cap test.",
            "unresolved_action": False, "clinical_entity_type": "chief_complaint",
        })
        assert response.status_code == 201
        items.append(response.json()["highlight"])
    assert client.post(f"/highlights/{items[0]['id']}/accept", headers=CLINICIAN).status_code == 200
    assert client.post(f"/highlights/{items[0]['id']}/reject", headers=CLINICIAN).status_code == 200
    for index, item in enumerate(items[1:5], start=2):
        headers = {**CLINICIAN, "X-User-Id": f"clinician-cap-{index}"}
        assert client.post(f"/highlights/{item['id']}/reject", headers=headers).status_code == 200
    iterator, db = _db()
    try:
        assert db.query(HighlightFeedback).filter(HighlightFeedback.highlight_id == items[0]["id"]).count() == 1
    finally:
        iterator.close()
    future = client.post(f"/entries/{entry['id']}/highlights", headers=CLINICIAN, json={
        "source_span": "Routine synthetic review note.", "text": "Future capped item",
        "risk_level": "none", "risk_reason": "Synthetic cap test.",
        "unresolved_action": False, "clinical_entity_type": "chief_complaint",
    }).json()
    assert future["learned_adjustment"] == -10.0
    assert any("capped" in item.lower() for item in future["explanation"])


def test_exposure_is_explicit_idempotent_and_review_queue_finds_lower_ranked(client: TestClient) -> None:
    display = "display_phase5_0001"
    top = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN).json()
    assert top
    before = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlight-trust-metrics", headers=CLINICIAN).json()
    assert before["exposed_count"] == 0
    first = client.post(f"/highlights/{top[0]['id']}/exposures", headers=CLINICIAN, json={"display_reference": display})
    again = client.post(f"/highlights/{top[0]['id']}/exposures", headers=CLINICIAN, json={"display_reference": display})
    assert first.json() == {"recorded": True}
    assert again.json() == {"recorded": False}
    assert client.post(f"/highlights/{top[0]['id']}/exposures", headers=STAFF, json={"display_reference": "display_phase5_0002"}).status_code == 403

    entry = _note(client, CLINICIAN, "clinician_note", "Routine synthetic review note.")
    for index in range(6):
        response = client.post(f"/entries/{entry['id']}/highlights", headers=CLINICIAN, json={
            "source_span": "Routine synthetic review note.", "text": f"Low ranked candidate {index}",
            "risk_level": "none", "risk_reason": "Routine review.",
            "unresolved_action": False, "clinical_entity_type": "chief_complaint",
        })
        assert response.status_code == 201
    queue = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlight-review-queue", headers=CLINICIAN)
    assert queue.status_code == 200
    assert any("Low ranked candidate" in item["text"] for item in queue.json())
    metrics = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlight-trust-metrics", headers=CLINICIAN).json()
    assert metrics["eligible_candidate_count"] >= 10
    assert metrics["exposed_count"] == 1
    assert metrics["unexposed_count"] >= 9
    assert "not clinical model accuracy" in metrics["metric_purpose"]
    assert client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlight-trust-metrics", headers=CLINIC_B).status_code == 404


def test_additive_phase5_tables_are_available_to_synthetic_runtime(client: TestClient) -> None:
    iterator, db = _db()
    try:
        tables = set(inspect(db.bind).get_table_names())
        assert {"conflict_provenance", "highlight_feedback", "highlight_exposures"} <= tables
    finally:
        iterator.close()
