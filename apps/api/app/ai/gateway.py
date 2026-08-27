import re
from dataclasses import dataclass

import httpx

from app.core.config import Settings, get_settings

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)")


@dataclass(frozen=True)
class GatewayResult:
    text: str
    redacted_prompt: str


def redact_sensitive(text: str) -> str:
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return _PHONE_RE.sub("[REDACTED_PHONE]", text)


class LLMGateway:
    """Bounded, advisory-only OpenAI-compatible LLM client.

    The gateway returns text only. It exposes no mutation, shell, network-management,
    database-write, or external-message tool to the model.
    """

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def suggest(self, *, system_prompt: str, user_prompt: str) -> GatewayResult:
        if not self.settings.llm_enabled:
            raise RuntimeError("LLM assistance is disabled")

        redacted = redact_sensitive(user_prompt)
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if self.settings.llm_api_key:
            headers["Authorization"] = f"Bearer {self.settings.llm_api_key}"

        payload = {
            "model": self.settings.llm_model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": redacted},
            ],
        }
        with httpx.Client(timeout=self.settings.llm_timeout_seconds) as client:
            response = client.post(
                f"{self.settings.llm_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
        text = str(data["choices"][0]["message"]["content"]).strip()
        if not text:
            raise RuntimeError("LLM returned an empty response")
        return GatewayResult(text=text, redacted_prompt=redacted)
