from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.models import ClinicalEntityType, RiskLevel
from app.services.importance_service import calculate_importance_score
from app.services.seed import SYNTHETIC_PATIENT_ID


def test_highlights_are_retrieved_in_importance_order(client: TestClient) -> None:
    response = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights")
    assert response.status_code == 200
    highlights = response.json()

    assert 3 <= len(highlights) <= 5
    scores = [highlight["importance_score"] for highlight in highlights]
    assert scores == sorted(scores, reverse=True)
    assert {highlight["text"] for highlight in highlights} == {
        "Penicillin allergy",
        "Lisinopril increased to 20 mg daily",
        "Renal function and potassium labs pending",
        "Nurse follow-up unresolved",
    }


def test_every_highlight_resolves_to_existing_entry_and_source_span(client: TestClient) -> None:
    entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries").json()
    entries_by_id = {entry["id"]: entry for entry in entries}
    highlights = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights").json()

    for highlight in highlights:
        assert highlight["entry_id"] in entries_by_id
        assert highlight["provenance_pointer"] == f"timeline-entry-{highlight['entry_id']}"
        assert highlight["source_span"] in entries_by_id[highlight["entry_id"]]["content"]


def test_importance_scoring_is_deterministic_and_explainable() -> None:
    source_time = datetime(2026, 8, 24, tzinfo=timezone.utc)
    as_of = datetime(2026, 8, 26, tzinfo=timezone.utc)

    score = calculate_importance_score(
        source_timestamp=source_time,
        risk_level=RiskLevel.HIGH,
        unresolved_action=True,
        clinical_entity_type=ClinicalEntityType.ALLERGY,
        clinician_confirmed=True,
        as_of=as_of,
    )

    assert score == 100.0  # risk 30 + unresolved 20 + allergy 20 + confirmed 15 + recent 15


def test_highlights_for_missing_patient_return_404(client: TestClient) -> None:
    assert client.get("/patients/missing/highlights").status_code == 404
