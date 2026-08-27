import re
import time
from dataclasses import dataclass
from threading import Lock

import httpx
import redis

from app.core.config import Settings, get_settings
from app.db.redis_client import get_redis

_EMAIL_RE = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_RE = re.compile(r"(?<!\d)(?:\+?\d[\d ()-]{7,}\d)(?!\d)")
_CIRCUIT_OPEN_KEY = "csp:llm:circuit:open"
_CIRCUIT_FAILURES_KEY = "csp:llm:circuit:failures"


@dataclass(frozen=True)
class GatewayResult:
    text: str
    redacted_prompt: str


def redact_sensitive(text: str) -> str:
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return _PHONE_RE.sub("[REDACTED_PHONE]", text)


class LLMGateway:
    """Bounded, advisory-only OpenAI-compatible LLM client.

    The gateway returns text only and exposes no mutation or execution tools.
    Circuit state is stored in Redis so all API workers observe the same breaker.
    A process-local breaker remains as a fail-safe if Redis itself is unavailable.
    """

    _lock = Lock()
    _failures = 0
    _opened_until = 0.0

    def __init__(
        self,
        settings: Settings | None = None,
        redis_client: redis.Redis | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.redis = redis_client or get_redis()

    @classmethod
    def reset_circuit(cls) -> None:
        with cls._lock:
            cls._failures = 0
            cls._opened_until = 0.0

    def _reset_distributed_circuit(self) -> None:
        try:
            self.redis.delete(_CIRCUIT_OPEN_KEY, _CIRCUIT_FAILURES_KEY)
        except redis.RedisError:
            pass

    def _assert_circuit_closed(self) -> None:
        try:
            if self.redis.exists(_CIRCUIT_OPEN_KEY):
                raise RuntimeError("LLM circuit breaker is open")
        except redis.RedisError:
            self._assert_local_circuit_closed()

    @classmethod
    def _assert_local_circuit_closed(cls) -> None:
        now = time.monotonic()
        with cls._lock:
            if cls._opened_until > now:
                raise RuntimeError("LLM circuit breaker is open")
            if cls._opened_until and cls._opened_until <= now:
                cls._failures = 0
                cls._opened_until = 0.0

    def _record_failure(self) -> None:
        threshold = max(1, self.settings.llm_circuit_failure_threshold)
        cooldown = max(1, self.settings.llm_circuit_cooldown_seconds)
        try:
            failures = int(self.redis.incr(_CIRCUIT_FAILURES_KEY))
            self.redis.expire(_CIRCUIT_FAILURES_KEY, cooldown)
            if failures >= threshold:
                self.redis.set(_CIRCUIT_OPEN_KEY, "1", ex=cooldown)
                self.redis.delete(_CIRCUIT_FAILURES_KEY)
            return
        except redis.RedisError:
            pass

        cls = type(self)
        with cls._lock:
            cls._failures += 1
            if cls._failures >= threshold:
                cls._opened_until = time.monotonic() + cooldown

    def _record_success(self) -> None:
        type(self).reset_circuit()
        self._reset_distributed_circuit()

    def suggest(self, *, system_prompt: str, user_prompt: str) -> GatewayResult:
        if not self.settings.llm_enabled:
            raise RuntimeError("LLM assistance is disabled")
        self._assert_circuit_closed()

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
        try:
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
        except Exception:
            self._record_failure()
            raise

        self._record_success()
        return GatewayResult(text=text, redacted_prompt=redacted)
