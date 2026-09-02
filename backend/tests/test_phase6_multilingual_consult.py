import json

from fastapi.testclient import TestClient
from sqlalchemy import inspect, select

from app.database import get_db
from app.main import app
from app.models import (
    AuditLog, ClinicalCapture, ConsultSession, ConsultState, ConsultSummary, EntryVersion,
    PatientInstructionApproval, ProvisionalSafetySignal, TimelineEntry, TranscriptSegment,
)
from app.services import consult_service
from app.services.seed import SYNTHETIC_PATIENT_ID
from app.services.summarization_provider import get_summary_provider


CLINICIAN = {"X-User-Id": "clinician-phase6", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-001"}
STAFF = {"X-User-Id": "nurse-phase6", "X-Role": "staff", "X-Clinic-Id": "clinic-demo-001"}
PATIENT = {"X-User-Id": SYNTHETIC_PATIENT_ID, "X-Role": "patient", "X-Clinic-Id": "clinic-demo-001"}
ADMIN = {"X-User-Id": "admin-phase6", "X-Role": "admin", "X-Clinic-Id": "clinic-demo-001"}
CLINIC_B = {"X-User-Id": "clinician-b", "X-Role": "clinician", "X-Clinic-Id": "clinic-demo-002"}


def start(client: TestClient) -> dict:
    response = client.post("/consults", headers=CLINICIAN, json={
        "patient_id": SYNTHETIC_PATIENT_ID, "synthetic": True,
        "mode": "synthetic_text_stream", "noise_profile": "simulated_clinic_noise",
    })
    assert response.status_code == 201
    return response.json()


def segment(client: TestClient, session_id: str, sequence: int, text: str, languages: list[tuple[int, int, str]], *, state: str = "final", start_ms: int = 0) -> dict:
    response = client.post(f"/consults/{session_id}/segments", headers=CLINICIAN, json={
        "sequence_number": sequence, "start_offset_ms": start_ms,
        "end_offset_ms": start_ms + 1000, "speaker": "patient",
        "original_synthetic_text": text,
        "language_spans": [{"start": a, "end": b, "language": language} for a, b, language in languages],
        "state": state, "alternatives": [],
    })
    assert response.status_code == 201, response.text
    return response.json()


def test_code_switching_spans_and_post_asr_minute_two_signal(client: TestClient) -> None:
    session = start(client)
    text = "I have allergy, saya sakit, wa bo ho."
    item = segment(client, session["id"], 1, text, [(0, 15, "english"), (16, 26, "malay"), (27, len(text), "hokkien")], start_ms=120_000)
    assert [span["language"] for span in item["language_spans"]] == ["english", "malay", "hokkien"]
    signals = client.get(f"/consults/{session['id']}/signals", headers=CLINICIAN).json()
    assert len(signals) == 1
    assert signals[0]["source_offset_ms"] == 120_000
    assert signals[0]["status"] == "needs_confirmation"
    assert signals[0]["risk_level"] == "high"
    assert signals[0]["provenance_pointer"] == item["provenance_pointer"]
    assert client.get(f"/consults/{session['id']}/summaries", headers=CLINICIAN).json() == []
    assert session["mode"] == "synthetic_text_stream"
    assert session["noise_profile"] == "simulated_clinic_noise"


def test_partial_unsupported_language_and_state_machine_fail_closed(client: TestClient) -> None:
    assert client.post("/consults", headers=CLINICIAN, json={
        "patient_id": SYNTHETIC_PATIENT_ID, "synthetic": False,
        "mode": "synthetic_text_stream", "noise_profile": "simulated_quiet",
    }).status_code == 422
    session = start(client)
    text = "可能对药物敏感"
    partial = segment(client, session["id"], 1, text, [(0, len(text), "unsupported-language")], state="partial")
    assert client.get(f"/consults/{session['id']}/signals", headers=CLINICIAN).json() == []
    duplicate = client.post(f"/consults/{session['id']}/segments", headers=CLINICIAN, json={
        "sequence_number": 1, "start_offset_ms": 1000, "end_offset_ms": 2000,
        "speaker": "patient", "original_synthetic_text": "duplicate",
        "language_spans": [{"start": 0, "end": 9, "language": "english"}], "state": "final",
    })
    assert duplicate.status_code == 409
    assert client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN).status_code == 422
    assert partial["state"] == "partial"


def test_mandarin_tamil_readiness_and_unknown_content_needs_confirmation(client: TestClient) -> None:
    session = start(client)
    text = "I feel unwell 我不舒服 எனக்கு உடல்நிலை சரியில்லை"
    item = segment(client, session["id"], 1, text, [(0, 13, "english"), (14, 18, "mandarin"), (19, len(text), "tamil")])
    assert {span["language"] for span in item["language_spans"]} == {"english", "mandarin", "tamil"}
    assert item["original_synthetic_text"] == text
    unsupported = start(client)
    phrase = "Unknown clinical phrase allergy concern"
    segment(client, unsupported["id"], 1, phrase, [(0, len(phrase), "unsupported-language")])
    captures = client.get(f"/consults/{unsupported['id']}/captures", headers=CLINICIAN).json()
    assert captures[0]["state"] == "needs_confirmation"
    assert captures[0]["confirmed_value"] is None


def test_montelukast_ambiguity_reference_boundary_and_clinician_confirmation(client: TestClient) -> None:
    class ForbiddenProvider:
        name = "must-not-run"
        def summarize(self, *_args, **_kwargs):
            raise AssertionError("Phase 6 confidence and rule summaries must not call an LLM")
    app.dependency_overrides[get_summary_provider] = lambda: ForbiddenProvider()
    session = start(client)
    phrase = "Montelukast — was it 20 mg or 50 mg?"
    source = segment(client, session["id"], 1, phrase, [(0, len(phrase), "english")])
    capture = client.get(f"/consults/{session['id']}/captures", headers=CLINICIAN).json()[0]
    assert capture["captured_term"] == "Montelukast"
    assert capture["exact_source_phrase"] == "Montelukast — was it 20 mg or 50 mg"
    assert capture["candidate_values"] == ["20 mg", "50 mg"]
    assert capture["state"] == "needs_confirmation" and capture["confirmed_value"] is None
    assert "not the patient's actual dose" in capture["reference_scope"]
    assert capture["provenance_pointer"] == source["provenance_pointer"]
    for headers in (STAFF, PATIENT, ADMIN):
        assert client.post(f"/consults/{session['id']}/captures/{capture['id']}/confirm", headers=headers, json={"selected_value": "20 mg"}).status_code == 403
    confirmed = client.post(f"/consults/{session['id']}/captures/{capture['id']}/confirm", headers=CLINICIAN, json={"selected_value": "20 mg"})
    assert confirmed.status_code == 200
    assert confirmed.json()["confirmed_value"] == "20 mg"
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        audit = db.scalar(select(AuditLog).where(AuditLog.entity_id == capture["id"]))
        assert audit.action == "clinical_capture.confirmed"
        assert set(audit.metadata_json) == {"from_status", "to_status"}
        assert "Montelukast" not in json.dumps(audit.metadata_json)
    finally:
        iterator.close()


def test_distinct_audience_summaries_patient_gate_and_clinic_scope(client: TestClient) -> None:
    session = start(client)
    phrase = "Montelukast — was it 20 mg or 50 mg?"
    segment(client, session["id"], 1, phrase, [(0, len(phrase), "english")])
    completed = client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN)
    assert completed.status_code == 200, completed.text
    summaries = completed.json()
    assert {item["audience"] for item in summaries} == {"clinician", "staff", "patient"}
    by_audience = {item["audience"]: item for item in summaries}
    assert "Unresolved uncertainty" in by_audience["clinician"]["timeline_entry"]["content"]
    assert "Arrange clinician review" in by_audience["staff"]["timeline_entry"]["content"]
    patient_entry = by_audience["patient"]["timeline_entry"]
    assert "20 mg" not in patient_entry["content"] and "50 mg" not in patient_entry["content"]
    assert patient_entry["patient_facing_status"] == "draft"
    assert all(item["generation_mode"] == "rule_derived" for item in summaries)
    assert all(item["source_provenance"] for item in summaries)
    patient_entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=PATIENT).json()
    assert patient_entry["id"] not in {item["id"] for item in patient_entries}
    staff_summaries = client.get(f"/consults/{session['id']}/summaries", headers=STAFF).json()
    assert [item["audience"] for item in staff_summaries] == ["staff"]
    assert client.get(f"/consults/{session['id']}", headers=PATIENT).status_code == 403
    for suffix in ("", "/segments", "/captures", "/signals", "/summaries"):
        assert client.get(f"/consults/{session['id']}{suffix}", headers=CLINIC_B).status_code == 404
    for headers in (STAFF, PATIENT, ADMIN):
        assert client.post(f"/entries/{patient_entry['id']}/patient-facing/approve", headers=headers).status_code == 403
    assert client.post(f"/entries/{patient_entry['id']}/patient-facing/approve", headers=CLINICIAN).status_code == 200
    patient_entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=PATIENT).json()
    assert patient_entry["id"] in {item["id"] for item in patient_entries}
    delivery = client.post(f"/entries/{patient_entry['id']}/deliveries", headers=CLINICIAN, json={
        "channel": "whatsapp_mock", "purpose": "instruction", "replaces_delivery_id": None,
    })
    assert delivery.status_code == 201
    assert delivery.json()["approved_version_number"] == 1


def test_correction_preserves_history_stales_summary_and_invalidates_approval(client: TestClient) -> None:
    session = start(client)
    phrase = "Montelukast — was it 20 mg or 50 mg?"
    source = segment(client, session["id"], 1, phrase, [(0, len(phrase), "english")])
    patient_entry = next(item for item in client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN).json() if item["audience"] == "patient")["timeline_entry"]
    assert client.post(f"/entries/{patient_entry['id']}/patient-facing/approve", headers=CLINICIAN).status_code == 200
    delivery = client.post(f"/entries/{patient_entry['id']}/deliveries", headers=CLINICIAN, json={
        "channel": "whatsapp_mock", "purpose": "instruction", "replaces_delivery_id": None,
    }).json()
    corrected_phrase = "Montelukast dose remains uncertain."
    corrected = client.post(f"/consults/{session['id']}/segments/{source['id']}/correct", headers=CLINICIAN, json={
        "original_synthetic_text": corrected_phrase,
        "language_spans": [{"start": 0, "end": len(corrected_phrase), "language": "english"}],
        "alternatives": [],
    })
    assert corrected.status_code == 200, corrected.text
    history = client.get(f"/consults/{session['id']}/segments", headers=CLINICIAN).json()
    assert len(history) == 2
    assert history[0]["state"] == "superseded" and history[0]["is_current"] is False
    assert history[0]["provenance_pointer"] == source["provenance_pointer"]
    assert history[1]["version_number"] == 2 and history[1]["is_current"] is True
    captures = client.get(f"/consults/{session['id']}/captures", headers=CLINICIAN).json()
    assert any(item["state"] == "superseded" and item["segment_version_number"] == 1 for item in captures)
    summaries = client.get(f"/consults/{session['id']}/summaries", headers=CLINICIAN).json()
    assert all(item["source_status"] == "stale" for item in summaries)
    patient_entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=PATIENT).json()
    assert patient_entry["id"] not in {item["id"] for item in patient_entries}
    deliveries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/deliveries", headers=CLINICIAN).json()
    assert next(item for item in deliveries if item["id"] == delivery["id"])["status"] == "superseded"


def test_safe_logs_runtime_tables_and_late_write_rejection(client: TestClient, caplog) -> None:
    session = start(client)
    text = "John Tan S1234567A 91234567 says Penicillin allergy."
    segment(client, session["id"], 1, text, [(0, len(text), "english")])
    assert client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN).status_code == 200
    late = client.post(f"/consults/{session['id']}/segments", headers=CLINICIAN, json={
        "sequence_number": 2, "start_offset_ms": 2000, "end_offset_ms": 3000,
        "speaker": "patient", "original_synthetic_text": "late text",
        "language_spans": [{"start": 0, "end": 9, "language": "english"}], "state": "final",
    })
    assert late.status_code == 409
    assert all(secret not in caplog.text for secret in ("John Tan", "S1234567A", "91234567", "Penicillin allergy"))
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        tables = set(inspect(db.bind).get_table_names())
        assert {"consult_sessions", "transcript_segments", "clinical_captures", "provisional_safety_signals", "consult_summaries"} <= tables
        audits = json.dumps([item.metadata_json for item in db.scalars(select(AuditLog))])
        assert all(secret not in audits for secret in ("John Tan", "S1234567A", "91234567", text))
    finally:
        iterator.close()


def test_finalization_is_atomic_and_failure_marks_session_failed(client: TestClient, monkeypatch) -> None:
    session = start(client)
    text = "Penicillin allergy reviewed."
    segment(client, session["id"], 1, text, [(0, len(text), "english")])
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        before = {
            "entries": db.query(TimelineEntry).count(),
            "versions": db.query(EntryVersion).count(),
            "approvals": db.query(PatientInstructionApproval).count(),
            "summaries": db.query(ConsultSummary).count(),
            "audits": db.query(AuditLog).filter(AuditLog.action == "consult.finalized").count(),
        }
    finally:
        iterator.close()
    original = consult_service.create_patient_entry
    calls = 0

    def fail_on_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("injected summary failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(consult_service, "create_patient_entry", fail_on_second)
    response = client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN)
    assert response.status_code == 503
    assert response.json() == {"detail": "Consult finalization failed safely"}
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        assert db.get(ConsultSession, session["id"]).state == ConsultState.FAILED
        assert db.query(TimelineEntry).count() == before["entries"]
        assert db.query(EntryVersion).count() == before["versions"]
        assert db.query(PatientInstructionApproval).count() == before["approvals"]
        assert db.query(ConsultSummary).count() == before["summaries"]
        assert db.query(AuditLog).filter(AuditLog.action == "consult.finalized").count() == before["audits"]
    finally:
        iterator.close()
    assert client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN).status_code == 409


def test_finalize_once_creates_exactly_three_summaries(client: TestClient) -> None:
    session = start(client)
    text = "Penicillin allergy reviewed."
    segment(client, session["id"], 1, text, [(0, len(text), "english")])
    first = client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN)
    assert first.status_code == 200 and len(first.json()) == 3
    assert client.post(f"/consults/{session['id']}/finalize", headers=CLINICIAN).status_code == 409
    assert len(client.get(f"/consults/{session['id']}/summaries", headers=CLINICIAN).json()) == 3


def test_correction_reuses_span_validation_without_mutation(client: TestClient) -> None:
    session = start(client)
    text = "Montelukast — was it 20 mg or 50 mg?"
    source = segment(client, session["id"], 1, text, [(0, len(text), "english")])
    patient_entry = next(item for item in client.post(
        f"/consults/{session['id']}/finalize", headers=CLINICIAN
    ).json() if item["audience"] == "patient")["timeline_entry"]
    assert client.post(f"/entries/{patient_entry['id']}/patient-facing/approve", headers=CLINICIAN).status_code == 200
    before_summaries = client.get(f"/consults/{session['id']}/summaries", headers=CLINICIAN).json()
    bad_payloads = [
        {"original_synthetic_text": "short", "language_spans": [{"start": 0, "end": 9, "language": "english"}]},
        {"original_synthetic_text": "overlap", "language_spans": [{"start": 0, "end": 4, "language": "english"}, {"start": 3, "end": 7, "language": "malay"}]},
        {"original_synthetic_text": "empty spans", "language_spans": []},
    ]
    for payload in bad_payloads:
        assert client.post(
            f"/consults/{session['id']}/segments/{source['id']}/correct",
            headers=CLINICIAN, json={**payload, "alternatives": []},
        ).status_code == 422
    history = client.get(f"/consults/{session['id']}/segments", headers=CLINICIAN).json()
    assert len(history) == 1 and history[0]["state"] == "final" and history[0]["is_current"] is True
    assert client.get(f"/consults/{session['id']}/summaries", headers=CLINICIAN).json() == before_summaries
    patient_entries = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries", headers=PATIENT).json()
    assert patient_entry["id"] in {item["id"] for item in patient_entries}
    iterator = app.dependency_overrides[get_db]()
    db = next(iterator)
    try:
        assert db.query(AuditLog).filter(AuditLog.action == "consult_segment.corrected").count() == 0
    finally:
        iterator.close()


def test_partial_finalization_is_append_only_and_only_final_derives(client: TestClient) -> None:
    session = start(client)
    text = "Penicillin allergy reported."
    partial = segment(client, session["id"], 1, text, [(0, len(text), "english")], state="partial")
    assert client.get(f"/consults/{session['id']}/signals", headers=CLINICIAN).json() == []
    finalized_text = "Penicillin allergy confirmed in post-ASR text."
    response = client.post(
        f"/consults/{session['id']}/segments/{partial['id']}/finalize", headers=STAFF,
        json={
            "original_synthetic_text": finalized_text,
            "language_spans": [{"start": 0, "end": len(finalized_text), "language": "english"}],
            "alternatives": [],
        },
    )
    assert response.status_code == 200, response.text
    final = response.json()
    assert final["version_number"] == 2 and final["state"] == "final" and final["is_current"] is True
    assert final["provenance_pointer"] != partial["provenance_pointer"]
    history = client.get(f"/consults/{session['id']}/segments", headers=CLINICIAN).json()
    assert [(item["state"], item["is_current"]) for item in history] == [("superseded", False), ("final", True)]
    signals = client.get(f"/consults/{session['id']}/signals", headers=CLINICIAN).json()
    assert len(signals) == 1 and signals[0]["provenance_pointer"] == final["provenance_pointer"]
    assert client.post(
        f"/consults/{session['id']}/segments/{partial['id']}/finalize", headers=STAFF,
        json={"original_synthetic_text": finalized_text, "language_spans": [{"start": 0, "end": len(finalized_text), "language": "english"}], "alternatives": []},
    ).status_code == 409
