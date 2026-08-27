import re
from dataclasses import dataclass


SINGAPORE_ID_PATTERN = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\w)")
GENERAL_NAME_PATTERN = re.compile(
    r"\b(?:(?:Mr|Mrs|Ms|Dr)\.?\s+)?[A-Z][a-z]{1,30}\s+[A-Z][a-z]{1,30}\b"
)
DOSAGE_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml)\b", re.IGNORECASE)
KNOWN_SYNTHETIC_NAMES = ("John Tan", "Maya Chen", "Jordan Lee")
PROTECTED_CLINICAL_TERMS = ("penicillin", "lisinopril", "allergy", "allergic")


@dataclass(frozen=True)
class RedactionResult:
    text: str
    names_redacted: int
    ids_redacted: int
    phones_redacted: int

    @property
    def total_redactions(self) -> int:
        return self.names_redacted + self.ids_redacted + self.phones_redacted


@dataclass(frozen=True)
class RedactionValidationResult:
    passed: bool
    detected_redactions: int
    remaining_phi_patterns: tuple[str, ...]
    protected_terms_preserved: bool
    missing_protected_terms: tuple[str, ...]
    output_integrity_valid: bool
    reason: str


def redact_phi(text: str, *, known_names: tuple[str, ...] = ()) -> RedactionResult:
    """Return safe text and counts; callers must use only the returned text downstream."""
    redacted, ids_redacted = SINGAPORE_ID_PATTERN.subn("[ID]", text)
    redacted, phones_redacted = PHONE_PATTERN.subn("[PHONE]", redacted)

    names_redacted = 0
    for name in sorted({name.strip() for name in known_names if name.strip()}, key=len, reverse=True):
        redacted, count = re.subn(re.escape(name), "[NAME]", redacted, flags=re.IGNORECASE)
        names_redacted += count
    redacted, generic_count = GENERAL_NAME_PATTERN.subn("[NAME]", redacted)
    names_redacted += generic_count

    return RedactionResult(
        text=redacted,
        names_redacted=names_redacted,
        ids_redacted=ids_redacted,
        phones_redacted=phones_redacted,
    )


def validate_redaction(
    original_text: str,
    redaction: RedactionResult,
    *,
    known_names: tuple[str, ...] = (),
) -> RedactionValidationResult:
    """Validate privacy and protected clinical content without exposing matched PHI."""
    remaining: list[str] = []
    if SINGAPORE_ID_PATTERN.search(redaction.text):
        remaining.append("singapore_id")
    if PHONE_PATTERN.search(redaction.text):
        remaining.append("phone")
    names_to_check = {
        name.strip().lower()
        for name in (*KNOWN_SYNTHETIC_NAMES, *known_names)
        if name.strip()
    }
    lowered_redacted = redaction.text.lower()
    if any(re.search(rf"\b{re.escape(name)}\b", lowered_redacted) for name in names_to_check):
        remaining.append("known_name")

    lowered_original = original_text.lower()
    protected_present = {
        term
        for term in PROTECTED_CLINICAL_TERMS
        if re.search(rf"\b{re.escape(term)}\b", lowered_original)
    }
    protected_present.update(match.group(0).lower() for match in DOSAGE_PATTERN.finditer(original_text))
    missing = tuple(
        sorted(term for term in protected_present if term not in lowered_redacted)
    )

    without_placeholders = re.sub(r"\[(?:NAME|ID|PHONE)\]", " ", redaction.text)
    output_integrity_valid = bool(re.search(r"[A-Za-z0-9]", without_placeholders))
    passed = not remaining and not missing and output_integrity_valid
    if remaining:
        reason = "Redaction review required: PHI pattern remains after redaction."
    elif missing:
        reason = "Redaction review required: protected clinical content was not preserved."
    elif not output_integrity_valid:
        reason = "Redaction review required: no meaningful content remains for summarization."
    else:
        reason = "Redaction validated: PHI removed and protected clinical content preserved."
    return RedactionValidationResult(
        passed=passed,
        detected_redactions=redaction.total_redactions,
        remaining_phi_patterns=tuple(remaining),
        protected_terms_preserved=not missing,
        missing_protected_terms=missing,
        output_integrity_valid=output_integrity_valid,
        reason=reason,
    )
