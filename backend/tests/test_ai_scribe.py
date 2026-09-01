import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.ai_scribe_service import opaque_source_reference
from app.services.summarization_provider import get_summary_provider


class CapturingProvider:
    name = "capturing-fake"

    def __init__(self) -> None:
        self.received: list[tuple[str, str]] = []

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str:
        self.received.append((redacted_text, interaction_type))
        return f"Safe synthetic summary: {redacted_text}"


def payload(interaction_type: str = "doctor_consult") -> dict[str, object]:
    return {
        "patient_id": "patient-demo-001",
        "interaction_type": interaction_type,
        "source_id": f"source-{interaction_type}-001",
        "transcript": "John Tan reported ID S1234567A and phone 91234567.",
        "synthetic": True,
    }


def test_provider_receives_only_redacted_text(client: TestClient) -> None:
    provider = CapturingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider

    response = client.post("/ai-scribe", json=payload())

    assert response.status_code == 201
    assert response.json()["status"] == "created"
    assert response.json()["validation"]["passed"] is True
    assert provider.received == [
        ("[NAME] reported ID [ID] and phone [PHONE].", "doctor_consult")
    ]
    received_text = provider.received[0][0]
    assert "John Tan" not in received_text
    assert "S1234567A" not in received_text
    assert "91234567" not in received_text


def test_ai_entry_has_stable_provenance_and_no_raw_transcript(client: TestClient) -> None:
    provider = CapturingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider

    response = client.post("/ai-scribe", json=payload("nurse_consult"))

    assert response.status_code == 201
    body = response.json()
    expected_source_ref = opaque_source_reference("source-nurse_consult-001")
    assert body["provenance_pointer"] == (
        f"synthetic://ai-scribe/{expected_source_ref}#transcript"
    )
    assert body["timeline_entry"]["provenance_pointer"] == body["provenance_pointer"]
    assert body["timeline_entry"]["author_role"] == "system"
    assert body["timeline_entry"]["version"] == 1
    assert "John Tan" not in body["timeline_entry"]["content"]
    assert "S1234567A" not in body["timeline_entry"]["content"]
    assert "91234567" not in body["timeline_entry"]["content"]
    versions = client.get(f"/entries/{body['timeline_entry']['id']}/versions").json()
    persisted_snapshots = " ".join(version["content"] for version in versions)
    assert "John Tan" not in persisted_snapshots
    assert "S1234567A" not in persisted_snapshots
    assert "91234567" not in persisted_snapshots


def test_raw_phi_is_not_logged(client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    provider = CapturingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider
    caplog.set_level(logging.INFO)

    response = client.post("/ai-scribe", json=payload())

    assert response.status_code == 201
    log_output = caplog.text
    assert "John Tan" not in log_output
    assert "S1234567A" not in log_output
    assert "91234567" not in log_output
    source_ref = opaque_source_reference("source-doctor_consult-001")
    assert source_ref in log_output
    assert "source-doctor_consult-001" not in log_output


@pytest.mark.parametrize(
    ("interaction_type", "entry_type"),
    [
        ("doctor_consult", "ai_doctor_consult_summary"),
        ("nurse_consult", "ai_nurse_consult_summary"),
        ("patient_session", "ai_patient_session_summary"),
    ],
)
def test_supported_interactions_create_correct_entry_types(
    client: TestClient,
    interaction_type: str,
    entry_type: str,
) -> None:
    provider = CapturingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider

    response = client.post("/ai-scribe", json=payload(interaction_type))

    assert response.status_code == 201
    assert response.json()["timeline_entry"]["type"] == entry_type
    assert response.json()["timeline_entry"]["author_role"] == "system"


def test_request_must_be_explicitly_synthetic(client: TestClient) -> None:
    request = payload()
    request["synthetic"] = False
    assert client.post("/ai-scribe", json=request).status_code == 422


def test_patient_cannot_ingest_ai_scribe(client: TestClient) -> None:
    response = client.post(
        "/ai-scribe",
        headers={
            "X-User-Id": "patient-demo-001",
            "X-Role": "patient",
            "X-Clinic-Id": "clinic-demo-001",
        },
        json=payload(),
    )
    assert response.status_code == 403


def test_ai_scribe_enforces_clinic_scope(client: TestClient) -> None:
    response = client.post(
        "/ai-scribe",
        headers={
            "X-User-Id": "clinician-other-001",
            "X-Role": "clinician",
            "X-Clinic-Id": "clinic-demo-002",
        },
        json=payload(),
    )
    assert response.status_code == 403
