import hashlib
import re


PHONE_DIGEST_DOMAIN = "nightingale.synthetic-phone.v1"
TOKEN_DIGEST_DOMAIN = "nightingale.patient-token.v1"


def normalize_e164(value: str) -> str:
    normalized = re.sub(r"[\s()-]", "", value)
    if not re.fullmatch(r"\+[1-9]\d{7,14}", normalized):
        raise ValueError("Invalid synthetic phone format")
    return normalized


def _digest(domain: str, value: str) -> str:
    payload = f"{domain}\0{value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def phone_digest(phone_e164: str) -> str:
    return f"phone_sha256_{_digest(PHONE_DIGEST_DOMAIN, normalize_e164(phone_e164))}"


def token_digest(token: str) -> str:
    return f"token_sha256_{_digest(TOKEN_DIGEST_DOMAIN, token)}"


def mask_phone(phone_e164: str) -> str:
    normalized = normalize_e164(phone_e164)
    return f"{normalized[:3]}••••{normalized[-4:]}"
