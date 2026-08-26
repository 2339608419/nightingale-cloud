from app.services.redaction_service import redact_phi


def test_redacts_required_phi_examples() -> None:
    result = redact_phi("John Tan S1234567A 91234567")

    assert result.text == "[NAME] [ID] [PHONE]"
    assert result.names_redacted == 1
    assert result.ids_redacted == 1
    assert result.phones_redacted == 1
    assert result.total_redactions == 3


def test_redacts_known_patient_name_case_insensitively() -> None:
    result = redact_phi("MAYA CHEN called +65 8123-4567", known_names=("Maya Chen",))

    assert result.text == "[NAME] called [PHONE]"
