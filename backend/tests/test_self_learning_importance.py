from fastapi.testclient import TestClient


MEDICATION_SUGGESTION = {
    "source_span": "Lisinopril increased from 10 mg to 20 mg daily.",
    "text": "Medication dose increased",
    "risk_level": "moderate",
    "risk_reason": "Recent dose change warrants monitoring.",
    "unresolved_action": False,
    "clinical_entity_type": "medication",
}


def test_acceptance_increases_similar_future_highlight_score(client: TestClient) -> None:
    first = client.post(
        "/entries/entry-demo-006/highlights",
        json=MEDICATION_SUGGESTION,
    )
    assert first.status_code == 201
    first_body = first.json()
    assert first_body["learned_bonus"] == 0.0
    assert first_body["highlight"]["risk_reason"]
    assert first_body["highlight"]["provenance_pointer"] == "timeline-entry-version-entry-demo-006-v1"

    accepted = client.post(f"/highlights/{first_body['highlight']['id']}/accept")
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["clinician_confirmed"] is True

    future = client.post(
        "/entries/entry-demo-006/highlights",
        json={**MEDICATION_SUGGESTION, "text": "Similar future medication change"},
    )
    assert future.status_code == 201
    future_body = future.json()
    assert future_body["base_score"] == first_body["base_score"]
    assert future_body["learned_bonus"] == 7.0
    assert future_body["highlight"]["importance_score"] > first_body["highlight"]["importance_score"]
    assert any("entity:medication +5.0" in item for item in future_body["explanation"])
    assert any("entry_type:instruction +2.0" in item for item in future_body["explanation"])

    preferences = client.get("/importance-preferences").json()
    medication = next(item for item in preferences if item["category_value"] == "medication")
    assert medication["accepted_count"] == 1
    assert medication["weight"] == 5.0
    assert "1 accepted" in medication["explanation"]


def test_clinician_can_reject_and_staff_cannot_decide(client: TestClient) -> None:
    suggestion = client.post(
        "/entries/entry-demo-006/highlights",
        json=MEDICATION_SUGGESTION,
    ).json()["highlight"]
    staff_headers = {
        "X-User-Id": "staff-demo-001",
        "X-Role": "staff",
        "X-Clinic-Id": "clinic-demo-001",
    }

    assert client.post(
        f"/highlights/{suggestion['id']}/accept", headers=staff_headers
    ).status_code == 403
    rejected = client.post(f"/highlights/{suggestion['id']}/reject")
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["risk_reason"] == MEDICATION_SUGGESTION["risk_reason"]
