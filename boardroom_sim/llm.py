"""OpenAI-compatible LLM client used by the boardroom simulation."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class LLMConfig:
    """Configuration for an OpenAI-compatible chat-completions endpoint."""

    api_key: str
    model: str
    base_url: str = "https://api.z.ai/api/paas/v4"
    temperature: float = 0.2
    timeout_seconds: int = 120

    @classmethod
    def from_env(
        cls,
        *,
        api_key_env: str = "BOARDROOM_LLM_API_KEY",
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        temperature: Optional[float] = None,
        timeout_seconds: Optional[int] = None,
    ) -> "LLMConfig":
        """Create configuration from environment variables and CLI overrides."""
        api_key = os.environ.get(api_key_env, "").strip()
        if not api_key:
            raise ValueError(f"Missing API key. Please set environment variable {api_key_env}.")

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

        return cls(
            api_key=api_key,
            model=resolved_model,
            base_url=resolved_base_url,
            temperature=resolved_temperature,
            timeout_seconds=resolved_timeout,
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
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"LLM HTTP error {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"LLM request failed: {exc}") from exc

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
                            "content": "Your previous answer was not valid JSON. Return one JSON object only.",
                        },
                    ]
                )
        raise ValueError(f"LLM did not return valid JSON after retries. Last response: {last_text}")

    def _update_usage(self, usage: Dict[str, Any]) -> None:
        """Update token counters when the provider returns usage metadata."""
        self.total_prompt_tokens += int(usage.get("prompt_tokens", 0) or 0)
        self.total_completion_tokens += int(usage.get("completion_tokens", 0) or 0)
        self.total_tokens += int(usage.get("total_tokens", 0) or 0)


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
