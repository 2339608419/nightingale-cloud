from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.models import ClinicalEntityType, RiskLevel
from app.services.importance_service import evaluate_importance


ALLERGY = {
    "source_span": "Penicillin allergy remains active.",
    "text": "Penicillin allergy",
    "risk_level": "none",
    "risk_reason": "Active allergy safety fact.",
    "unresolved_action": False,
    "clinical_entity_type": "allergy",
}
MEDICATION_CONFLICT = {
    "source_span": "Lisinopril increased from 10 mg to 20 mg daily.",
    "text": "Unresolved Lisinopril dosage conflict",
    "risk_level": "none",
    "risk_reason": "Different dose values require clinician review.",
    "unresolved_action": True,
    "clinical_entity_type": "medication",
}
LAB = {
    "source_span": "Lab order for renal function and potassium remains pending.",
    "text": "Renal function monitoring",
    "risk_level": "none",
    "risk_reason": "Synthetic lab category.",
    "unresolved_action": False,
    "clinical_entity_type": "lab",
}


def suggest(client: TestClient, entry_id: str, payload: dict) -> dict:
    response = client.post(f"/entries/{entry_id}/highlights", json=payload)
    assert response.status_code == 201
    return response.json()


def reject(client: TestClient, suggestion: dict) -> None:
    response = client.post(f"/highlights/{suggestion['highlight']['id']}/reject")
    assert response.status_code == 200


def accept(client: TestClient, suggestion: dict) -> None:
    response = client.post(f"/highlights/{suggestion['highlight']['id']}/accept")
    assert response.status_code == 200


def test_repeated_rejection_cannot_push_allergy_below_high_floor(
    client: TestClient,
) -> None:
    for index in range(4):
        reject(client, suggest(client, "entry-demo-006", {**ALLERGY, "text": f"Allergy {index}"}))

    future = suggest(client, "entry-demo-006", ALLERGY)

    # One actor's repeated rejects are suppressed by the Phase 5 negative guard.
    assert future["learned_adjustment"] == 0.0
    assert future["adjusted_score"] < future["safety_floor"]
    assert future["safety_floor"] == 50.0
    assert future["safety_floor_risk"] == "high"
    assert future["final_score"] == 50.0
    assert future["highlight"]["importance_score"] == 50.0
    assert future["highlight"]["risk_level"] == "high"
    assert future["floor_applied"] is True


def test_unresolved_medication_dosage_conflict_cannot_fall_below_floor(
    client: TestClient,
) -> None:
    for index in range(4):
        reject(
            client,
            suggest(
                client,
                "entry-demo-006",
                {**MEDICATION_CONFLICT, "text": f"Medication dosage conflict {index}"},
            ),
        )

    future = suggest(client, "entry-demo-006", MEDICATION_CONFLICT)

    assert future["learned_adjustment"] == 0.0
    assert future["safety_floor_rule"] == "unresolved_medication_dosage_conflict"
    assert future["safety_floor"] == 65.0
    assert future["safety_floor_risk"] == "high"
    assert future["final_score"] == 65.0
    assert future["highlight"]["risk_level"] == "high"


def test_noncritical_category_can_move_down_with_feedback(client: TestClient) -> None:
    initial = suggest(client, "entry-demo-007", LAB)
    reject(client, initial)
    second = suggest(client, "entry-demo-007", {**LAB, "text": "Independent lab review"})
    response = client.post(
        f"/highlights/{second['highlight']['id']}/reject",
        headers={
            "X-User-Id": "clinician-demo-002",
            "X-Role": "clinician",
            "X-Clinic-Id": "clinic-demo-001",
        },
    )
    assert response.status_code == 200
    future = suggest(client, "entry-demo-007", {**LAB, "text": "Future lab item"})

    assert initial["safety_floor"] is None
    assert future["floor_applied"] is False
    assert future["learned_adjustment"] == -6.0
    assert future["final_score"] < initial["final_score"]


def test_positive_learning_still_increases_noncritical_priority(client: TestClient) -> None:
    initial = suggest(client, "entry-demo-007", LAB)
    accept(client, initial)
    future = suggest(client, "entry-demo-007", {**LAB, "text": "Future accepted lab item"})

    assert future["learned_adjustment"] == 7.0
    assert future["final_score"] > initial["final_score"]
    assert future["final_score"] == future["adjusted_score"]


def test_safety_floor_preserves_existing_highlight_provenance(client: TestClient) -> None:
    result = suggest(client, "entry-demo-006", ALLERGY)

    assert result["highlight"]["entry_id"] == "entry-demo-006"
    assert result["highlight"]["provenance_pointer"] == "timeline-entry-version-entry-demo-006-v1"
    assert result["highlight"]["source_span"] == ALLERGY["source_span"]


def test_policy_supports_medication_change_and_unresolved_follow_up_floors() -> None:
    now = datetime(2026, 8, 27, tzinfo=timezone.utc)
    medication = evaluate_importance(
        source_timestamp=now,
        risk_level=RiskLevel.NONE,
        unresolved_action=False,
        clinical_entity_type=ClinicalEntityType.MEDICATION,
        clinician_confirmed=False,
        learned_adjustment=-10.0,
        context="Lisinopril dose increased to 20 mg daily.",
        as_of=now,
    )
    follow_up = evaluate_importance(
        source_timestamp=now,
        risk_level=RiskLevel.NONE,
        unresolved_action=True,
        clinical_entity_type=ClinicalEntityType.FOLLOW_UP,
        clinician_confirmed=False,
        learned_adjustment=-10.0,
        context="Nurse follow-up remains unresolved.",
        as_of=now,
    )

    assert medication.safety_floor_rule == "recent_or_unresolved_medication_change"
    assert medication.safety_floor_risk == RiskLevel.MODERATE
    assert medication.final_score >= 35.0
    assert follow_up.safety_floor_rule == "unresolved_clinical_follow_up"
    assert follow_up.safety_floor_risk == RiskLevel.MODERATE
    assert follow_up.final_score >= 50.0
