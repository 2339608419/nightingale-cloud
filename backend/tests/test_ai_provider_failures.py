import json
import logging
import socket
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.database import get_db
from app.main import app
from app.models import AuditLog
from app.services.ai_scribe_service import opaque_source_reference
from app.services.seed import SYNTHETIC_PATIENT_ID
from app.services.summarization_provider import (
    InvalidProviderResponseError,
    OpenAIResponsesProvider,
    ProviderTimeoutError,
    ProviderUnavailableError,
    get_summary_provider,
)
from app.services import summarization_provider


SYNTHETIC_TRANSCRIPT = (
    "John Tan S1234567A 91234567 reports Lisinopril 20 mg and dizziness."
)
PHI_SOURCE_ID = "John-Tan-S1234567A-91234567"
PHI_SOURCE_FRAGMENTS = ("John-Tan", "S1234567A", "91234567")


def payload(source_id: str) -> dict[str, object]:
    return {
        "patient_id": SYNTHETIC_PATIENT_ID,
        "interaction_type": "doctor_consult",
        "source_id": source_id,
        "transcript": SYNTHETIC_TRANSCRIPT,
        "synthetic": True,
    }


def entry_ids(client: TestClient) -> set[str]:
    response = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries")
    assert response.status_code == 200
    return {entry["id"] for entry in response.json()}


def audit_payloads() -> list[str]:
    override = app.dependency_overrides[get_db]
    session_generator = override()
    db = next(session_generator)
    try:
        rows = db.scalars(select(AuditLog)).all()
        return [
            json.dumps(
                {
                    "actor_id": row.actor_id,
                    "actor_role": row.actor_role,
                    "action": row.action,
                    "entity_type": row.entity_type,
                    "entity_id": row.entity_id,
                    "metadata": row.metadata_json,
                },
                sort_keys=True,
            )
            for row in rows
        ]
    finally:
        session_generator.close()


class FailureProvider:
    name = "failure-test-provider"
    generation_mode = "external_model"

    def __init__(self, error: Exception) -> None:
        self.error = error
        self.received: list[str] = []

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str:
        del interaction_type
        self.received.append(redacted_text)
        raise self.error


class EmptyProvider:
    name = "empty-test-provider"
    generation_mode = "external_model"

    def __init__(self) -> None:
        self.received: list[str] = []

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str:
        del interaction_type
        self.received.append(redacted_text)
        return "   "


@pytest.mark.parametrize(
    ("error", "expected_status", "expected_outcome"),
    [
        (ProviderTimeoutError(), 504, "provider_timeout"),
        (ProviderUnavailableError(), 503, "provider_unavailable"),
        (InvalidProviderResponseError(), 502, "invalid_provider_response"),
    ],
)
def test_typed_provider_failures_safely_abstain_without_entry_or_audit(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
    error: Exception,
    expected_status: int,
    expected_outcome: str,
) -> None:
    provider = FailureProvider(error)
    app.dependency_overrides[get_summary_provider] = lambda: provider
    before_entries = entry_ids(client)
    before_audits = audit_payloads()
    caplog.set_level(logging.WARNING)

    response = client.post(
        "/ai-scribe",
        json=payload(PHI_SOURCE_ID),
    )

    assert response.status_code == expected_status
    body = response.json()
    assert body["status"] == "withheld"
    assert body["outcome"] == expected_outcome
    assert body["safe_abstention"] is True
    assert body["generated_summary"] is None
    assert body["timeline_entry"] is None
    assert body["provenance_pointer"] is None
    assert entry_ids(client) == before_entries
    assert audit_payloads() == before_audits
    assert provider.received == [
        "[NAME] [ID] [PHONE] reports Lisinopril 20 mg and dizziness."
    ]
    combined_output = response.text + caplog.text + " ".join(audit_payloads())
    for sensitive_text in (
        "John Tan",
        "S1234567A",
        "91234567",
        "Lisinopril",
        "dizziness",
        *PHI_SOURCE_FRAGMENTS,
    ):
        assert sensitive_text not in combined_output


def test_empty_provider_response_is_invalid_and_not_persisted(client: TestClient) -> None:
    provider = EmptyProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider
    before = entry_ids(client)

    response = client.post("/ai-scribe", json=payload("empty-provider-response"))

    assert response.status_code == 502
    assert response.json()["outcome"] == "invalid_provider_response"
    assert response.json()["safe_abstention"] is True
    assert entry_ids(client) == before


def test_unexpected_provider_error_body_is_never_logged_or_returned(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = FailureProvider(RuntimeError(f"third-party body: {SYNTHETIC_TRANSCRIPT}"))
    app.dependency_overrides[get_summary_provider] = lambda: provider
    caplog.set_level(logging.WARNING)

    response = client.post("/ai-scribe", json=payload("unexpected-provider-error"))

    assert response.status_code == 503
    assert response.json()["outcome"] == "provider_unavailable"
    combined_output = response.text + caplog.text
    for sensitive_text in (
        "John Tan",
        "S1234567A",
        "91234567",
        "Lisinopril 20 mg",
        "reports Lisinopril 20 mg and dizziness",
    ):
        assert sensitive_text not in combined_output


def test_openai_provider_maps_http_503_without_reading_or_exposing_body(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    received: list[tuple[bytes, float]] = []

    def unavailable(request, timeout: float):
        received.append((request.data, timeout))
        raise HTTPError(
            request.full_url,
            503,
            f"provider secret body {SYNTHETIC_TRANSCRIPT}",
            hdrs=None,
            fp=None,
        )

    monkeypatch.setattr(summarization_provider, "urlopen", unavailable)
    provider = OpenAIResponsesProvider("synthetic-key", "test-model", timeout_seconds=1.25)
    app.dependency_overrides[get_summary_provider] = lambda: provider

    response = client.post("/ai-scribe", json=payload(PHI_SOURCE_ID))

    assert response.status_code == 503
    assert response.json()["outcome"] == "provider_unavailable"
    assert received[0][1] == 1.25
    sent_payload = received[0][0].decode("utf-8")
    assert "[NAME]" in sent_payload
    assert "John Tan" not in sent_payload
    assert "S1234567A" not in sent_payload
    assert "91234567" not in sent_payload
    assert SYNTHETIC_TRANSCRIPT not in response.text
    assert all(fragment not in response.text for fragment in PHI_SOURCE_FRAGMENTS)


def test_openai_provider_timeout_uses_configured_deadline_and_abstains(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed_timeouts: list[float] = []

    def hangs(_request, timeout: float):
        observed_timeouts.append(timeout)
        raise socket.timeout(f"hung with {SYNTHETIC_TRANSCRIPT}")

    monkeypatch.setenv("AI_SCRIBE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "synthetic-key")
    monkeypatch.setenv("AI_SCRIBE_PROVIDER_TIMEOUT_SECONDS", "0.25")
    monkeypatch.setattr(summarization_provider, "urlopen", hangs)

    response = client.post("/ai-scribe", json=payload(PHI_SOURCE_ID))

    assert response.status_code == 504
    assert response.json()["outcome"] == "provider_timeout"
    assert response.json()["timeline_entry"] is None
    assert observed_timeouts == [0.25]
    assert all(fragment not in response.text for fragment in PHI_SOURCE_FRAGMENTS)


def test_openai_provider_malformed_response_safely_abstains(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class MalformedResponse:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self) -> bytes:
            return b"not-json and never a clinical summary"

    monkeypatch.setattr(
        summarization_provider,
        "urlopen",
        lambda _request, timeout: MalformedResponse(),
    )
    provider = OpenAIResponsesProvider("synthetic-key", "test-model", timeout_seconds=0.5)
    app.dependency_overrides[get_summary_provider] = lambda: provider
    before = entry_ids(client)

    response = client.post("/ai-scribe", json=payload(PHI_SOURCE_ID))

    assert response.status_code == 502
    assert response.json()["outcome"] == "invalid_provider_response"
    assert response.json()["timeline_entry"] is None
    assert entry_ids(client) == before
    assert all(fragment not in response.text for fragment in PHI_SOURCE_FRAGMENTS)


def test_default_offline_mock_is_explicitly_rule_derived(client: TestClient) -> None:
    response = client.post("/ai-scribe", json=payload(PHI_SOURCE_ID))

    assert response.status_code == 201
    body = response.json()
    assert body["outcome"] == "success"
    assert body["generation_mode"] == "rule_derived_mock"
    assert body["safe_abstention"] is False
    assert "Rule-derived mock" in body["message"]


def test_external_source_id_is_stably_opaque_across_response_and_persistence(
    client: TestClient,
    caplog: pytest.LogCaptureFixture,
) -> None:
    source_ref = opaque_source_reference(PHI_SOURCE_ID)
    assert source_ref == opaque_source_reference(PHI_SOURCE_ID)
    assert source_ref.startswith("src_sha256_")
    assert len(source_ref) == len("src_sha256_") + 64
    assert all(fragment not in source_ref for fragment in PHI_SOURCE_FRAGMENTS)
    caplog.set_level(logging.INFO)
    before_audits = audit_payloads()

    response = client.post("/ai-scribe", json=payload(PHI_SOURCE_ID))

    assert response.status_code == 201
    body = response.json()
    entry = body["timeline_entry"]
    expected_provenance = f"synthetic://ai-scribe/{source_ref}#transcript"
    assert entry["provenance_pointer"] == expected_provenance
    assert body["provenance_pointer"] == expected_provenance
    assert source_ref in caplog.text
    versions_response = client.get(f"/entries/{entry['id']}/versions")
    assert versions_response.status_code == 200
    versions = versions_response.json()
    assert versions[0]["provenance_pointer"] == expected_provenance
    assert audit_payloads() == before_audits

    all_outputs = json.dumps(body, sort_keys=True) + caplog.text
    all_outputs += json.dumps(versions, sort_keys=True)
    all_outputs += " ".join(audit_payloads())
    all_outputs += entry["id"]
    assert PHI_SOURCE_ID not in all_outputs
    for fragment in PHI_SOURCE_FRAGMENTS:
        assert fragment not in all_outputs
