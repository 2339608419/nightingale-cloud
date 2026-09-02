"""Direct, numbered resilience acceptance tests for original scenarios 1–16.

These tests intentionally reuse the deeper assertion helpers in the focused suites. They are
an executable index, not weaker copies of those tests. Each scenario still runs against a
fresh synthetic database through the shared ``client`` fixture.
"""

import json

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app
from app.models import (
    AuditLog, HighlightExposure, HighlightFeedback, ImportancePreference, Patient,
    TimelineEntry,
)
from app.services.seed import SYNTHETIC_PATIENT_ID, seed_demo_data

from app.services.summarization_provider import ProviderUnavailableError

from test_ai_provider_failures import (
    test_openai_provider_timeout_uses_configured_deadline_and_abstains as _provider_timeout,
    test_typed_provider_failures_safely_abstain_without_entry_or_audit as _typed_failure,
    test_unexpected_provider_error_body_is_never_logged_or_returned as _safe_provider_error,
)
from test_ai_scribe import test_provider_receives_only_redacted_text as _redacted_provider_input
from test_clinic_isolation_defense import (
    create_targets as _create_tenant_targets,
    disable_outer_clinic_guard as _disable_outer_guard,
    cross_clinic_request as _cross_clinic_request,
)
from test_concurrent_edits import test_stale_same_entry_edit_is_rejected_with_409 as _stale_edit
from test_evidence_confidence import (
    test_evidence_confidence_is_deterministic as _confidence_deterministic,
    test_unexpected_evidence_invariant_failure_abstains_instead_of_500 as _confidence_fail_closed,
)
from test_highlight_provenance import test_source_edit_and_revert_keep_old_highlight_snapshot_stable as _immutable_source
from test_phase5_clinical_trust import (
    _allergy_suggestion,
    _note,
    test_actor_feedback_negative_guard_change_undo_and_metadata as _feedback_guard,
    test_exact_nurse_then_ai_no_allergy_is_visible_safe_conflict as _allergy_conflict,
    test_exposure_is_explicit_idempotent_and_review_queue_finds_lower_ranked as _exposure_queue,
)
from test_phase6_multilingual_consult import (
    test_code_switching_spans_and_post_asr_minute_two_signal as _code_switch_and_signal,
    test_partial_finalization_is_append_only_and_only_final_derives as _partial_to_final,
)
from test_phone_access_delivery_correction import (
    test_delivery_binds_approved_snapshot_and_edit_requires_traceable_correction as _delivery_correction,
    test_delivery_states_are_distinct_and_invalid_transition_has_no_audit as _delivery_states,
    test_phone_first_access_uses_digest_single_use_and_self_only_portal as _phone_portal,
    test_same_synthetic_phone_resolves_within_requested_clinic as _tenant_phone,
)


def test_scenario_01_phone_only_patient_access(client, caplog):
    _phone_portal(client, caplog)


def test_scenario_02_clinic_guard_failure(client, monkeypatch):
    targets = _create_tenant_targets(client)
    _disable_outer_guard(monkeypatch)
    response = _cross_clinic_request(client, "patient_read", targets)
    assert response.status_code == 404
    assert "Maya" not in response.text


def test_scenario_03_no_phi_or_provider_error_in_logs_and_audit(client, caplog):
    _safe_provider_error(client, caplog)


def test_scenario_04_provider_receives_only_redacted_validated_text(client):
    _redacted_provider_input(client)


def test_scenario_05_clinic_b_isolation_not_full_onboarding(client):
    _tenant_phone(client)
    denied = client.get(
        "/patients/patient-demo-001",
        headers={"X-User-Id": "clinician-b", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-002"},
    )
    assert denied.status_code in {403, 404}
    assert "Maya" not in denied.text


def test_scenario_06_code_switched_synthetic_text_and_no_audio_claim(client):
    _code_switch_and_signal(client)
    unsupported = client.post("/consults", json={
        "patient_id": "patient-demo-001", "synthetic": True,
        "mode": "audio_stream", "noise_profile": "simulated_clinic_noise",
    })
    assert unsupported.status_code == 422


def test_scenario_07_minute_two_final_signal_partial_withheld(client):
    _partial_to_final(client)


def test_scenario_08_provider_timeout_typed_abstention_no_entry(client, monkeypatch):
    _provider_timeout(client, monkeypatch)


def test_scenario_09_provider_unavailable_safe_abstention(client, caplog):
    _typed_failure(client, caplog, ProviderUnavailableError(), 503, "provider_unavailable")


def test_scenario_10_stale_edit_safe_409_and_history(client):
    _stale_edit(client)


def test_scenario_11_created_is_not_delivered_and_states_are_distinct(client):
    _delivery_states(client)


def test_scenario_12_wrong_sent_version_requires_traceable_correction(client):
    _delivery_correction(client)


def test_scenario_13_nurse_ai_allergy_conflict_has_two_sources(client):
    _allergy_conflict(client)


def test_scenario_14_evidence_confidence_is_deterministic_and_fail_closed(client, monkeypatch):
    _confidence_deterministic(client)
    _confidence_fail_closed(client, monkeypatch)


def test_scenario_15_feedback_guard_undo_exposure_queue_and_floor(client):
    _feedback_guard(client)
    _exposure_queue(client)
    top = client.get("/patients/patient-demo-001/highlights").json()
    queue = client.get("/patients/patient-demo-001/highlight-review-queue").json()
    assert queue
    assert {item["id"] for item in queue}.isdisjoint(item["id"] for item in top)
    policy = client.get("/importance-feedback-policy/allergy").json()
    assert "Clinical safety floors are applied after" in " ".join(policy["explanation"])


def test_scenario_16_highlight_keeps_immutable_source_after_edit(client):
    _immutable_source(client)


def test_phase5_feedback_state_machine_roles_tenant_and_metadata(client):
    clinician_one = {"X-User-Id": "phase7-one", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-001"}
    clinician_two = {**clinician_one, "X-User-Id": "phase7-two"}
    clinic_b = {**clinician_one, "X-User-Id": "phase7-b", "X-Clinic-Id": "clinic-demo-002"}
    entry = _note(client, clinician_one, "clinician_note", "Penicillin allergy is active.")
    first = _allergy_suggestion(client, entry["id"], "Penicillin allergy is active.", "Phase 7 first")
    second = _allergy_suggestion(client, entry["id"], "Penicillin allergy is active.", "Phase 7 second")

    assert client.post(f"/highlights/{first['id']}/accept", headers=clinician_one).status_code == 200
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        audit_count = db.query(AuditLog).filter(AuditLog.entity_id == first["id"]).count()
    finally:
        iterator.close()
    assert client.post(f"/highlights/{first['id']}/accept", headers=clinician_one).status_code == 200
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        assert db.query(AuditLog).filter(AuditLog.entity_id == first["id"]).count() == audit_count
        assert db.query(HighlightFeedback).filter(HighlightFeedback.highlight_id == first["id"]).count() == 1
    finally:
        iterator.close()

    assert client.post(f"/highlights/{first['id']}/reject", headers=clinician_one).status_code == 200
    assert client.post(f"/highlights/{second['id']}/reject", headers=clinician_one).status_code == 200
    assert client.get("/importance-feedback-policy/allergy", headers=clinician_one).json()["negative_feedback_state"] == "suppressed"
    assert client.post(f"/highlights/{second['id']}/reject", headers=clinician_two).status_code == 200
    assert client.get("/importance-feedback-policy/allergy", headers=clinician_one).json()["negative_feedback_state"] == "applied"
    assert client.get("/importance-feedback-policy/allergy", headers=clinic_b).json()["negative_feedback_state"] == "suppressed"

    for role in ("patient", "staff", "admin"):
        headers = {"X-User-Id": f"phase7-{role}", "X-Role": role, "X-Clinic-Id": "clinic-demo-001"}
        assert client.post(f"/highlights/{first['id']}/accept", headers=headers).status_code == 403
        assert client.post(f"/highlights/{first['id']}/exposures", headers=headers, json={"display_reference": f"phase7-{role}"}).status_code == 403

    display = "phase7-display-unique"
    assert client.post(f"/highlights/{first['id']}/exposures", headers=clinician_one, json={"display_reference": display}).json() == {"recorded": True}
    assert client.post(f"/highlights/{first['id']}/exposures", headers=clinician_one, json={"display_reference": display}).json() == {"recorded": False}
    metrics = client.get("/patients/patient-demo-001/highlight-trust-metrics", headers=clinician_one).json()
    assert "Penicillin" not in json.dumps(metrics)
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        assert db.scalar(select(HighlightExposure).where(HighlightExposure.display_reference == display)) is not None
        assert db.query(HighlightExposure).filter(HighlightExposure.display_reference == display).count() == 1
        events = db.query(AuditLog).filter(AuditLog.entity_id.in_([first["id"], second["id"]])).all()
        assert all(set(event.metadata_json) == {"from_status", "to_status"} for event in events)
        assert "Penicillin" not in json.dumps([event.metadata_json for event in events])
        assert db.query(ImportancePreference).filter(ImportancePreference.clinic_id == "clinic-demo-002", ImportancePreference.category_value == "allergy").count() == 0
    finally:
        iterator.close()


def test_phase7_fresh_database_startup_and_seed_smoke(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'fresh-phase7.db'}")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    with Session() as db:
        seed_demo_data(db)
        assert db.get(Patient, SYNTHETIC_PATIENT_ID) is not None
        tables = set(inspect(engine).get_table_names())
        assert {"patients", "timeline_entries", "consult_sessions", "highlight_feedback", "patient_deliveries"} <= tables
    engine.dispose()


def test_phase7_current_synthetic_runtime_restart_is_idempotent(tmp_path):
    database = tmp_path / "runtime-phase7.db"
    engine = create_engine(f"sqlite:///{database}")
    Session = sessionmaker(bind=engine)
    Base.metadata.create_all(engine)
    with Session() as db:
        seed_demo_data(db)
        original_entries = db.query(TimelineEntry).count()
    engine.dispose()

    restarted = create_engine(f"sqlite:///{database}")
    Base.metadata.create_all(restarted)
    RestartedSession = sessionmaker(bind=restarted)
    with RestartedSession() as db:
        seed_demo_data(db)
        assert db.query(TimelineEntry).count() == original_entries
        assert db.get(Patient, SYNTHETIC_PATIENT_ID) is not None
    restarted.dispose()
