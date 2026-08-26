import json
import os
from typing import Protocol
from urllib.request import Request, urlopen


class SummaryProvider(Protocol):
    name: str

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str: ...


class DeterministicMockProvider:
    name = "deterministic-mock"

    def summarize(self, redacted_text: str, *, interaction_type: str) -> str:
        normalized = " ".join(redacted_text.split())
        concise = normalized[:600].rstrip()
        if len(normalized) > 600:
            concise += "…"
        label = interaction_type.replace("_", " ").title()
        return f"{label} summary: {concise}"


class OpenAIResponsesProvider:
    name = "openai-responses"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

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
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed HTTPS endpoint
            body = json.loads(response.read().decode("utf-8"))
        summary = body.get("output_text")
        if not isinstance(summary, str):
            for output in body.get("output", []):
                if output.get("type") != "message":
                    continue
                for content in output.get("content", []):
                    if content.get("type") == "output_text" and isinstance(content.get("text"), str):
                        summary = content["text"]
                        break
                if isinstance(summary, str):
                    break
        if not isinstance(summary, str) or not summary.strip():
            raise RuntimeError("External summarizer returned no text")
        return summary.strip()


def get_summary_provider() -> SummaryProvider:
    provider_mode = os.getenv("AI_SCRIBE_PROVIDER", "mock").lower()
    api_key = os.getenv("OPENAI_API_KEY")
    if provider_mode == "openai" and api_key:
        return OpenAIResponsesProvider(
            api_key=api_key,
            model=os.getenv("OPENAI_MODEL", "gpt-5-mini"),
        )
    return DeterministicMockProvider()
