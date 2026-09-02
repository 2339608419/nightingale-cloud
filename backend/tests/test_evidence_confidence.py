from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models import Highlight
from app.services.seed import SYNTHETIC_PATIENT_ID
from app.services.summarization_provider import get_summary_provider


CLINICIAN = {
    "X-User-Id": "clinician-demo-001",
    "X-Role": "clinician",
    "X-Clinic-Id": "clinic-demo-001",
}


def _highlights(client: TestClient) -> list[dict]:
    response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN
    )
    assert response.status_code == 200
    return response.json()


def test_exact_source_valid_span_and_no_conflict_produces_high_confidence(
    client: TestClient,
) -> None:
    allergy = next(
        item for item in _highlights(client) if item["id"] == "highlight-demo-allergy"
    )

    assert allergy["evidence_confidence_level"] == "high"
    assert allergy["provenance_resolved"] is True
    assert allergy["source_span_verified"] is True
    assert allergy["structured_fact_match"] is True
    assert allergy["open_conflict"] is False
    assert allergy["requires_review"] is False
    assert allergy["abstained"] is False


def test_unresolved_conflict_causes_needs_review(client: TestClient) -> None:
    ai_response = client.post(
        "/ai-scribe",
        headers=CLINICIAN,
        json={
            "patient_id": SYNTHETIC_PATIENT_ID,
            "interaction_type": "doctor_consult",
            "source_id": "confidence-conflict-source",
            "transcript": "Lisinopril increased to 20 mg daily.",
            "synthetic": True,
        },
    )
    assert ai_response.status_code == 201
    ai_entry = ai_response.json()["timeline_entry"]

    clinician_response = client.post(
        f"/patients/{SYNTHETIC_PATIENT_ID}/entries",
        headers=CLINICIAN,
        json={
            "type": "clinician_note",
            "content": "Continue Lisinopril 10 mg daily.",
        },
    )
    assert clinician_response.status_code == 201

    suggestion = client.post(
        f"/entries/{ai_entry['id']}/highlights",
        headers=CLINICIAN,
        json={
            "source_span": "Lisinopril increased to 20 mg daily.",
            "text": "Lisinopril increased to 20 mg daily",
            "risk_level": "high",
            "risk_reason": "Medication dosage conflicts with clinician plan.",
            "unresolved_action": True,
            "clinical_entity_type": "medication",
        },
    )

    assert suggestion.status_code == 201
    confidence = suggestion.json()["highlight"]
    assert confidence["evidence_confidence_level"] == "abstain"
    assert confidence["open_conflict"] is True
    assert confidence["requires_review"] is True
    assert confidence["abstained"] is True


def test_broken_provenance_causes_abstain(client: TestClient) -> None:
    override = app.dependency_overrides[get_db]
    db_iterator = override()
    db = next(db_iterator)
    try:
        highlight = db.get(Highlight, "highlight-demo-allergy")
        assert highlight is not None
        highlight.provenance_pointer = "timeline-entry-missing"
        db.commit()
    finally:
        db_iterator.close()

    allergy = next(
        item for item in _highlights(client) if item["id"] == "highlight-demo-allergy"
    )
    assert allergy["evidence_confidence_level"] == "abstain"
    assert allergy["provenance_resolved"] is False
    assert allergy["requires_review"] is True
    assert allergy["abstained"] is True


def test_evidence_confidence_is_deterministic(client: TestClient) -> None:
    first = {item["id"]: item for item in _highlights(client)}
    second = {item["id"]: item for item in _highlights(client)}
    confidence_fields = (
        "evidence_confidence_level",
        "confidence_reason",
        "requires_review",
        "abstained",
        "provenance_resolved",
        "source_span_verified",
        "structured_fact_match",
        "open_conflict",
    )

    assert first.keys() == second.keys()
    for highlight_id in first:
        assert {field: first[highlight_id][field] for field in confidence_fields} == {
            field: second[highlight_id][field] for field in confidence_fields
        }


def test_confidence_calculation_does_not_call_summary_provider(
    client: TestClient,
) -> None:
    class FailingProvider:
        name = "must-not-run"

        def __init__(self) -> None:
            self.calls = 0

        def summarize(self, redacted_text: str, interaction_type: str) -> str:
            self.calls += 1
            raise AssertionError("Evidence confidence must not invoke an LLM provider")

    provider = FailingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider

    assert _highlights(client)
    assert provider.calls == 0


def test_confidence_explanation_is_structured_and_contains_no_clinical_text(
    client: TestClient,
) -> None:
    allergy = next(item for item in _highlights(client) if item["id"] == "highlight-demo-allergy")
    assert allergy["confidence_rule_triggered"] == "exact_structured_evidence_confirmed"
    assert allergy["confidence_required_action"] == "none"
    assert set(allergy["confidence_inputs_evaluated"]) == {
        "immutable_source", "version_pointer", "exact_span", "structured_entity",
        "conflict", "human_confirmation", "source_currency",
    }
    serialized = " ".join(allergy["confidence_inputs_evaluated"])
    assert "Penicillin" not in serialized
    assert allergy["source_span"] not in serialized


def test_unexpected_evidence_invariant_failure_abstains_instead_of_500(
    client: TestClient, monkeypatch,
) -> None:
    import app.services.evidence_confidence_service as confidence_service

    def broken_resolver(*_args, **_kwargs):
        raise RuntimeError("synthetic invariant failure with forbidden clinical body")

    monkeypatch.setattr(confidence_service, "resolve_highlight_provenance", broken_resolver)
    response = client.get(
        f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN
    )
    assert response.status_code == 200
    assert response.json()
    assert all(item["evidence_confidence_level"] == "abstain" for item in response.json())
    assert all(item["confidence_rule_triggered"] == "evaluation_failed_closed" for item in response.json())
    assert "forbidden clinical body" not in response.text


def test_high_medium_low_and_human_confirmation_rules_are_explicit(client: TestClient) -> None:
    current = {item["id"]: item for item in _highlights(client)}
    assert current["highlight-demo-allergy"]["evidence_confidence_level"] == "high"
    assert current["highlight-demo-lab"]["evidence_confidence_level"] == "medium"

    mismatch = client.post("/entries/entry-demo-006/highlights", headers=CLINICIAN, json={
        "source_span": "Lisinopril increased from 10 mg to 20 mg daily.",
        "text": "Declared as wrong synthetic entity", "risk_level": "low",
        "risk_reason": "Negative deterministic test.", "unresolved_action": False,
        "clinical_entity_type": "lab",
    })
    assert mismatch.status_code == 201
    assert mismatch.json()["highlight"]["evidence_confidence_level"] == "low"
    assert mismatch.json()["highlight"]["confidence_rule_triggered"] == "structured_entity_mismatch"

    confirmed = client.post("/highlights/highlight-demo-lab/accept", headers=CLINICIAN)
    assert confirmed.status_code == 200
    assert confirmed.json()["evidence_confidence_level"] == "high"
    assert confirmed.json()["confidence_rule_triggered"] == "exact_evidence_human_confirmed"
