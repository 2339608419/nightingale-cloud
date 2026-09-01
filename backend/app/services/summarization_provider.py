import json
import os
import socket
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


DEFAULT_PROVIDER_TIMEOUT_SECONDS = 30.0
MIN_PROVIDER_TIMEOUT_SECONDS = 0.1
MAX_PROVIDER_TIMEOUT_SECONDS = 120.0


class ProviderFailure(Exception):
    """Sanitized provider failure safe to classify without retaining response text."""

    outcome: str


class ProviderTimeoutError(ProviderFailure):
    outcome = "provider_timeout"


class ProviderUnavailableError(ProviderFailure):
    outcome = "provider_unavailable"


class InvalidProviderResponseError(ProviderFailure):
    outcome = "invalid_provider_response"


class SummaryProvider(Protocol):
    name: str
    generation_mode: str

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str: ...


class DeterministicMockProvider:
    name = "deterministic-mock"
    generation_mode = "rule_derived_mock"

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str:
        normalized = " ".join(redacted_text.split())
        concise = normalized[:600].rstrip()
        if len(normalized) > 600:
            concise += "…"
        label = interaction_type.replace("_", " ").title()
        return f"{label} summary: {concise}"


class OpenAIResponsesProvider:
    name = "openai-responses"
    generation_mode = "external_model"

    def __init__(self, api_key: str, model: str, timeout_seconds: float) -> None:
        self.api_key = api_key
        self.model = model
        self.timeout_seconds = timeout_seconds

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str:
        payload = json.dumps(
            {
                "model": self.model,
                "instructions": (
                    "Summarize this already-redacted synthetic healthcare interaction concisely. "
                    "Do not infer or restore redacted identifiers."
                ),
                "input": f"Interaction type: {interaction_type}\n\n{redacted_text}",
            }
        ).encode("utf-8")
        request = Request(
            "https://api.openai.com/v1/responses",
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urlopen(  # noqa: S310 - fixed HTTPS endpoint
                request,
                timeout=self.timeout_seconds,
            ) as response:
                encoded_body = response.read()
        except (TimeoutError, socket.timeout) as error:
            raise ProviderTimeoutError() from error
        except HTTPError as error:
            # Never retain or surface the provider response body.
            raise ProviderUnavailableError() from error
        except URLError as error:
            if isinstance(error.reason, (TimeoutError, socket.timeout)):
                raise ProviderTimeoutError() from error
            raise ProviderUnavailableError() from error
        except OSError as error:
            raise ProviderUnavailableError() from error

        try:
            body = json.loads(encoded_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise InvalidProviderResponseError() from error
        if not isinstance(body, dict):
            raise InvalidProviderResponseError()
        summary = body.get("output_text")
        if not isinstance(summary, str):
            output_items = body.get("output", [])
            if not isinstance(output_items, list):
                raise InvalidProviderResponseError()
            for output in output_items:
                if not isinstance(output, dict):
                    continue
                if output.get("type") != "message":
                    continue
                content_items = output.get("content", [])
                if not isinstance(content_items, list):
                    continue
                for content in content_items:
                    if not isinstance(content, dict):
                        continue
                    if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                        summary = content["text"]
                        break
                if isinstance(summary, str):
                    break
        if not isinstance(summary, str) or not summary.strip():
            raise InvalidProviderResponseError()
        return summary.strip()


def get_provider_timeout_seconds() -> float:
    """Return a bounded timeout without logging or exposing configuration contents."""
    configured = os.getenv("AI_SCRIBE_PROVIDER_TIMEOUT_SECONDS")
    if configured is None:
        return DEFAULT_PROVIDER_TIMEOUT_SECONDS
    try:
        parsed = float(configured)
    except ValueError:
        return DEFAULT_PROVIDER_TIMEOUT_SECONDS
    if not MIN_PROVIDER_TIMEOUT_SECONDS <= parsed <= MAX_PROVIDER_TIMEOUT_SECONDS:
        return DEFAULT_PROVIDER_TIMEOUT_SECONDS
    return parsed


def get_summary_provider() -> SummaryProvider:
    provider_mode = os.getenv("AI_SCRIBE_PROVIDER", "mock").lower()
    api_key = os.getenv("OPENAI_API_KEY")
    if provider_mode == "openai" and api_key:
        return OpenAIResponsesProvider(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
            timeout_seconds=get_provider_timeout_seconds(),
        )
    return DeterministicMockProvider()
