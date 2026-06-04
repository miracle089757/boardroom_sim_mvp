"""OpenAI-compatible LLM client used by the boardroom simulation."""

from __future__ import annotations

import http.client
import json
import os
import re
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

RETRYABLE_HTTP_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
RETRYABLE_NETWORK_EXCEPTIONS = (
    urllib.error.URLError,
    http.client.RemoteDisconnected,
    http.client.IncompleteRead,
    ConnectionResetError,
    ConnectionAbortedError,
    TimeoutError,
    socket.timeout,
    ssl.SSLEOFError,
)


@dataclass
class LLMConfig:
    """Configuration for an OpenAI-compatible chat-completions endpoint."""

    api_key: str
    model: str
    base_url: str = "https://api.z.ai/api/paas/v4"
    temperature: float = 0.2
    timeout_seconds: int = 120
    http_max_retries: int = 6
    retry_base_seconds: float = 2.0

    @classmethod
    def from_env(
        cls,
        *,
        api_key: Optional[str] = None,
        api_key_env: str = "BOARDROOM_LLM_API_KEY",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[int] = None,
        http_max_retries: Optional[int] = None,
        retry_base_seconds: Optional[float] = None,
    ) -> "LLMConfig":
        """Create configuration from environment variables and CLI overrides."""
        api_key = api_key or os.environ.get(api_key_env, "").strip()
        if not api_key:
            raise ValueError(f"Missing API key. Please set environment variable {api_key_env} or pass --api-key.")

        resolved_model = model or os.environ.get("BOARDROOM_LLM_MODEL", "glm-4.7-flash")
        resolved_base_url = base_url or os.environ.get("BOARDROOM_LLM_BASE_URL", cls.base_url)
        resolved_temperature = (
            temperature
            if temperature is not None
            else float(os.environ.get("BOARDROOM_LLM_TEMPERATURE", cls.temperature))
        )
        resolved_timeout = (
            timeout_seconds
            if timeout_seconds is not None
            else int(os.environ.get("BOARDROOM_LLM_TIMEOUT_SECONDS", cls.timeout_seconds))
        )
        resolved_http_max_retries = (
            http_max_retries
            if http_max_retries is not None
            else int(os.environ.get("BOARDROOM_LLM_HTTP_MAX_RETRIES", cls.http_max_retries))
        )
        resolved_retry_base_seconds = (
            retry_base_seconds
            if retry_base_seconds is not None
            else float(os.environ.get("BOARDROOM_LLM_RETRY_BASE_SECONDS", cls.retry_base_seconds))
        )

        return cls(
            api_key=api_key,
            model=resolved_model,
            base_url=resolved_base_url,
            temperature=resolved_temperature,
            timeout_seconds=resolved_timeout,
            http_max_retries=resolved_http_max_retries,
            retry_base_seconds=resolved_retry_base_seconds,
        )


class LLMClient:
    """Small standard-library client for JSON-oriented LLM calls."""

    def __init__(self, config: LLMConfig) -> None:
        """Initialize the client from a validated LLM configuration."""
        self.config = config
        self.total_prompt_tokens = 0
        self.total_completion_tokens = 0
        self.total_tokens = 0

    def complete_text(self, messages: List[Dict[str, str]]) -> str:
        """Call the chat-completions endpoint and return assistant text."""
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
        }
        body = json.dumps(payload).encode("utf-8")

        for attempt in range(self.config.http_max_retries + 1):
            request = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                },
                method="POST",
            )
            try:
                with urllib.request.urlopen(request, timeout=self.config.timeout_seconds) as response:
                    response_payload = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                error_body = exc.read().decode("utf-8", errors="replace")
                if self._should_retry_http(exc.code, attempt):
                    retry_after = exc.headers.get("Retry-After") if exc.headers else None
                    self._sleep_before_retry(attempt, f"HTTP {exc.code}", retry_after)
                    continue
                raise RuntimeError(f"LLM HTTP error {exc.code}: {error_body}") from exc
            except RETRYABLE_NETWORK_EXCEPTIONS as exc:
                if attempt < self.config.http_max_retries:
                    self._sleep_before_retry(attempt, self._network_error_reason(exc))
                    continue
                raise RuntimeError(
                    f"LLM request failed after {attempt + 1} attempts: "
                    f"{type(exc).__name__}: {exc}"
                ) from exc

        self._update_usage(response_payload.get("usage", {}))
        try:
            return response_payload["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError, TypeError) as exc:
            raise RuntimeError(f"Unexpected LLM response format: {response_payload}") from exc

    def complete_json(self, messages: List[Dict[str, str]], max_retries: int = 2) -> Dict[str, Any]:
        """Call the LLM and parse the response as a JSON object."""
        attempt_messages = list(messages)
        last_text = ""
        for attempt in range(max_retries + 1):
            last_text = self.complete_text(attempt_messages)
            try:
                return extract_json_object(last_text)
            except ValueError:
                if attempt >= max_retries:
                    break
                attempt_messages.extend(
                    [
                        {"role": "assistant", "content": last_text},
                        {
                            "role": "user",
                            "content": "你上一次的回答不是合法 JSON。请只返回一个 JSON 对象，不要输出 Markdown 或解释。",
                        },
                    ]
                )
        raise ValueError(f"LLM did not return valid JSON after retries. Last response: {last_text}")

    def _update_usage(self, usage: Dict[str, Any]) -> None:
        """Update token counters when the provider returns usage metadata."""
        self.total_prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        self.total_completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        self.total_tokens += int(usage.get("total_tokens", 0) or 0)

    def _should_retry_http(self, status_code: int, attempt: int) -> bool:
        """Return whether an HTTP failure is transient enough to retry."""
        return status_code in RETRYABLE_HTTP_STATUS_CODES and attempt < self.config.http_max_retries

    def _sleep_before_retry(self, attempt: int, reason: str, retry_after: Optional[str] = None) -> None:
        """Sleep with bounded exponential backoff before retrying a transient LLM error."""
        delay = self._retry_delay_seconds(attempt, retry_after)
        print(
            f"LLM request failed with {reason}; retrying in {delay:.1f}s "
            f"({attempt + 1}/{self.config.http_max_retries}).",
            file=sys.stderr,
        )
        time.sleep(delay)

    def _network_error_reason(self, exc: BaseException) -> str:
        """Return a compact retry reason for transient network failures."""
        if isinstance(exc, urllib.error.URLError):
            reason = getattr(exc, "reason", exc)
            return f"network error {type(reason).__name__}"
        return f"network error {type(exc).__name__}"

    def _retry_delay_seconds(self, attempt: int, retry_after: Optional[str] = None) -> float:
        """Compute retry delay, honoring Retry-After when the provider sends it."""
        if retry_after:
            try:
                return min(60.0, max(0.0, float(retry_after)))
            except ValueError:
                pass
        return min(60.0, self.config.retry_base_seconds * (2**attempt))


def extract_json_object(text: str) -> Dict[str, Any]:
    """Extract one JSON object from raw model text."""
    cleaned = text.strip()
    fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, flags=re.DOTALL)
    if fenced_match:
        cleaned = fenced_match.group(1).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        object_match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if not object_match:
            raise ValueError(f"No JSON object found in response: {text}")
        parsed = json.loads(object_match.group(0))

    if not isinstance(parsed, dict):
        raise ValueError(f"Expected a JSON object but received: {type(parsed).__name__}")
    return parsed
