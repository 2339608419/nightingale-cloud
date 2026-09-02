from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import delete, select

from app.database import get_db
from app.main import app
from app.models import ClinicalEntityType, HighlightProvenance, RiskLevel
from app.services.importance_service import calculate_importance_score
from app.services.seed import SYNTHETIC_PATIENT_ID
from app.services.seed import seed_demo_data


CLINICIAN = {"X-User-Id": "clinician-demo-001", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-001"}
PATIENT = {"X-User-Id": SYNTHETIC_PATIENT_ID, "X-Role": "patient", "X-Clinic-Id": "clinic-demo-001"}
CLINIC_B = {"X-User-Id": "clinician-demo-002", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-002"}


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
        assert highlight["source_version_number"] == 1
        assert highlight["provenance_pointer"] == f"timeline-entry-version-{highlight['entry_id']}-v1"
        assert highlight["provenance_status"] == "current"
        assert highlight["source_changed"] is False
        source = client.get(f"/highlights/{highlight['id']}/source", headers=CLINICIAN)
        assert source.status_code == 200
        assert highlight["source_span"] in source.json()["content"]


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


def test_created_highlight_binds_exact_immutable_source_version(client: TestClient) -> None:
    payload = {
        "source_span": "Initial hypertension review",
        "text": "Hypertension history",
        "risk_level": "moderate",
        "risk_reason": "Relevant chronic condition.",
        "unresolved_action": False,
        "clinical_entity_type": "risk",
        "expected_source_version": 1,
    }
    created = client.post("/entries/entry-demo-001/highlights", headers=CLINICIAN, json=payload)
    assert created.status_code == 201, created.text
    highlight = created.json()["highlight"]
    assert highlight["source_version_number"] == 1
    assert highlight["provenance_status"] == "current"
    assert highlight["version_provenance_pointer"] == "timeline-entry-version-entry-demo-001-v1"

    mismatch = client.post(
        "/entries/entry-demo-001/highlights",
        headers=CLINICIAN,
        json={**payload, "text": "Stale binding attempt", "expected_source_version": 99},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["error_code"] == "highlight_source_version_conflict"


def test_source_edit_and_revert_keep_old_highlight_snapshot_stable(client: TestClient) -> None:
    before = next(
        item for item in client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN).json()
        if item["id"] == "highlight-demo-medication"
    )
    pointer = before["version_provenance_pointer"]
    old_content = client.get("/highlights/highlight-demo-medication/source", headers=CLINICIAN).json()["content"]

    edited = client.patch(
        "/entries/entry-demo-006",
        headers=CLINICIAN,
        json={"content": "Lisinopril is now 10 mg daily after review.", "expected_version": 1},
    )
    assert edited.status_code == 200
    stale = next(
        item for item in client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN).json()
        if item["id"] == "highlight-demo-medication"
    )
    assert stale["provenance_status"] == "stale"
    assert stale["source_changed"] is True
    assert stale["source_version_number"] == 1
    assert stale["version_provenance_pointer"] == pointer
    snapshot = client.get("/highlights/highlight-demo-medication/source", headers=CLINICIAN).json()
    assert snapshot["content"] == old_content
    assert "10 mg daily after review" not in snapshot["content"]

    reverted = client.post(
        "/entries/entry-demo-006/revert/1",
        headers=CLINICIAN,
        json={"expected_version": 2},
    )
    assert reverted.status_code == 200
    after_revert = client.get("/highlights/highlight-demo-medication/source", headers=CLINICIAN).json()
    assert after_revert["source_version_number"] == 1
    assert after_revert["version_provenance_pointer"] == pointer
    assert after_revert["provenance_status"] == "stale"


def test_broken_binding_abstains_without_guessing_current_source(client: TestClient) -> None:
    override = app.dependency_overrides[get_db]
    iterator = override()
    db = next(iterator)
    try:
        binding = db.get(HighlightProvenance, "highlight-demo-lab")
        assert binding is not None
        binding.source_version_number = 999
        db.commit()
    finally:
        iterator.close()
    highlight = next(
        item for item in client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN).json()
        if item["id"] == "highlight-demo-lab"
    )
    assert highlight["provenance_status"] == "broken"
    assert highlight["evidence_confidence_level"] == "abstain"
    response = client.get("/highlights/highlight-demo-lab/source", headers=CLINICIAN)
    assert response.status_code == 409
    assert "Lab order" not in response.text

    iterator = override()
    db = next(iterator)
    try:
        binding = db.get(HighlightProvenance, "highlight-demo-lab")
        binding.source_version_number = 1
        binding.source_span = "corrupted span"
        db.commit()
    finally:
        iterator.close()
    span_broken = next(
        item for item in client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN).json()
        if item["id"] == "highlight-demo-lab"
    )
    assert span_broken["provenance_status"] == "broken"
    assert span_broken["evidence_confidence_level"] == "abstain"


def test_immutable_source_endpoint_enforces_clinic_and_role_visibility(client: TestClient) -> None:
    cross_clinic = client.get("/highlights/highlight-demo-lab/source", headers=CLINIC_B)
    patient = client.get("/highlights/highlight-demo-lab/source", headers=PATIENT)
    assert cross_clinic.status_code == 404
    assert patient.status_code == 403
    assert "Lisinopril" not in cross_clinic.text + patient.text
    approved_instruction = client.get(
        "/highlights/highlight-demo-medication/source", headers=PATIENT
    )
    assert approved_instruction.status_code == 200
    assert approved_instruction.json()["entry_id"] == "entry-demo-006"


def test_seed_highlights_have_resolvable_or_explicitly_broken_bindings(client: TestClient) -> None:
    highlights = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/highlights", headers=CLINICIAN).json()
    assert highlights
    for highlight in highlights:
        assert highlight["provenance_status"] in {"current", "broken"}
        if highlight["provenance_status"] == "current":
            assert client.get(f"/highlights/{highlight['id']}/source", headers=CLINICIAN).status_code == 200


def test_existing_runtime_without_companion_rows_is_safely_backfilled(client: TestClient) -> None:
    override = app.dependency_overrides[get_db]
    iterator = override()
    db = next(iterator)
    try:
        db.execute(delete(HighlightProvenance))
        db.commit()
        seed_demo_data(db)
        bindings = list(db.scalars(select(HighlightProvenance)))
        assert len(bindings) == 4
        assert all(binding.source_span for binding in bindings)
    finally:
        iterator.close()
