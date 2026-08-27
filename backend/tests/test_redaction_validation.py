import logging

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ai_scribe_service
from app.services.redaction_service import (
    RedactionResult,
    redact_phi,
    validate_redaction,
)
from app.services.seed import SYNTHETIC_PATIENT_ID
from app.services.summarization_provider import get_summary_provider


class CapturingProvider:
    name = "validation-capturing-fake"

    def __init__(self) -> None:
        self.received: list[str] = []

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str:
        self.received.append(redacted_text)
        return f"Validated {interaction_type} summary: {redacted_text}"


def _payload(transcript: str) -> dict[str, object]:
    return {
        "patient_id": SYNTHETIC_PATIENT_ID,
        "interaction_type": "doctor_consult",
        "source_id": "redaction-validation-source",
        "transcript": transcript,
        "synthetic": True,
    }


def _unsafe_redactor(text: str, *, known_names: tuple[str, ...] = ()) -> RedactionResult:
    del known_names
    return RedactionResult(
        text=text,
        names_redacted=0,
        ids_redacted=0,
        phones_redacted=0,
    )


def test_valid_redaction_proceeds_with_only_validated_text(client: TestClient) -> None:
    provider = CapturingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider

    response = client.post(
        "/ai-scribe",
        json=_payload(
            "John Tan reports Penicillin allergy and takes Lisinopril 20 mg daily. "
            "ID S1234567A phone 91234567."
        ),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "created"
    assert body["validation"]["passed"] is True
    assert body["validation"]["remaining_phi_patterns"] == []
    assert body["validation"]["protected_terms_preserved"] is True
    assert len(provider.received) == 1
    assert "John Tan" not in provider.received[0]
    assert "S1234567A" not in provider.received[0]
    assert "91234567" not in provider.received[0]
    assert "Penicillin" in provider.received[0]
    assert "Lisinopril 20 mg" in provider.received[0]


def test_remaining_phone_and_id_withhold_without_provider_or_entry(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    provider = CapturingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider
    monkeypatch.setattr(ai_scribe_service, "redact_phi", _unsafe_redactor)
    before = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries").json()

    response = client.post(
        "/ai-scribe",
        json=_payload("John Tan ID S1234567A phone 91234567 reports dizziness."),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "withheld"
    assert body["message"] == "AI scribe withheld pending redaction review"
    assert body["generated_summary"] is None
    assert body["timeline_entry"] is None
    assert body["provenance_pointer"] is None
    assert body["validation"]["passed"] is False
    assert set(body["validation"]["remaining_phi_patterns"]) == {
        "singapore_id",
        "phone",
        "known_name",
    }
    assert provider.received == []
    after = client.get(f"/patients/{SYNTHETIC_PATIENT_ID}/entries").json()
    assert {entry["id"] for entry in after} == {entry["id"] for entry in before}


def test_protected_medication_allergy_terms_and_dosage_survive_redaction() -> None:
    original = (
        "John Tan has a Penicillin allergy and takes Lisinopril 20 mg daily. "
        "Phone 91234567."
    )
    redaction = redact_phi(original, known_names=("John Tan",))
    validation = validate_redaction(original, redaction, known_names=("John Tan",))

    assert validation.passed is True
    assert validation.protected_terms_preserved is True
    assert validation.missing_protected_terms == ()
    assert "Penicillin" in redaction.text
    assert "allergy" in redaction.text
    assert "Lisinopril" in redaction.text
    assert "20 mg" in redaction.text


def test_corrupted_protected_term_fails_validation() -> None:
    original = "Lisinopril 20 mg daily for Penicillin allergy review."
    corrupted = RedactionResult(
        text="[NAME] daily for review.",
        names_redacted=1,
        ids_redacted=0,
        phones_redacted=0,
    )

    validation = validate_redaction(original, corrupted)

    assert validation.passed is False
    assert validation.protected_terms_preserved is False
    assert set(validation.missing_protected_terms) == {
        "lisinopril",
        "20 mg",
        "penicillin",
        "allergy",
    }


def test_validation_failure_logs_no_raw_phi(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    provider = CapturingProvider()
    app.dependency_overrides[get_summary_provider] = lambda: provider
    monkeypatch.setattr(ai_scribe_service, "redact_phi", _unsafe_redactor)
    caplog.set_level(logging.WARNING)
    transcript = "John Tan S1234567A 91234567 reports dizziness."

    response = client.post("/ai-scribe", json=_payload(transcript))

    assert response.json()["status"] == "withheld"
    assert provider.received == []
    assert "John Tan" not in caplog.text
    assert "S1234567A" not in caplog.text
    assert "91234567" not in caplog.text
    assert "redaction-validation-source" in caplog.text
