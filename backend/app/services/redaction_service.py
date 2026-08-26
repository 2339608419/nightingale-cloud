import re
from dataclasses import dataclass


SINGAPORE_ID_PATTERN = re.compile(r"\b[STFGM]\d{7}[A-Z]\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<![A-Za-z0-9])(?:\+?65[\s-]?)?[689]\d{3}[\s-]?\d{4}(?!\w)")
GENERAL_NAME_PATTERN = re.compile(
    r"\b(?:(?:Mr|Mrs|Ms|Dr)\.?\s+)?[A-Z][a-z]{1,30}\s+[A-Z][a-z]{1,30}\b"
)


@dataclass(frozen=True)
class RedactionResult:
    text: str
    names_redacted: int
    ids_redacted: int
    phones_redacted: int

    @property
    def total_redactions(self) -> int:
        return self.names_redacted + self.ids_redacted + self.phones_redacted


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
