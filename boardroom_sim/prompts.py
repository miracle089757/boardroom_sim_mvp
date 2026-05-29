"""Prompt template loading and rendering."""

from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Dict

from boardroom_sim.config import PROJECT_ROOT


DEFAULT_PROMPTS_DIR = PROJECT_ROOT / "prompts"


class PromptRenderer:
    """Render Markdown prompt templates with simple placeholder substitution."""

    def __init__(self, prompts_dir: Path | None = None, response_generator: str = "critical") -> None:
        self.prompts_dir = prompts_dir or DEFAULT_PROMPTS_DIR
        self.response_generator = response_generator
        self.round_tasks: list[str] = []
        self._cache: Dict[str, str] = {}

    def render(self, template_name: str, **values: object) -> str:
        """Render a top-level prompt template such as system_agent.md."""
        text = self._read_template(self.prompts_dir / f"{template_name}.md")
        return Template(text).safe_substitute({key: str(value) for key, value in values.items()}).strip()

    def response_guidance(self) -> str:
        """Return the configured response-generator guidance block."""
        path = self.prompts_dir / "response_generators" / f"{self.response_generator}.md"
        if not path.exists():
            path = self.prompts_dir / "response_generators" / "critical.md"
        return self._read_template(path).strip()

    def _read_template(self, path: Path) -> str:
        key = str(path)
        if key not in self._cache:
            if not path.exists():
                raise FileNotFoundError(f"Prompt template not found: {path}")
            self._cache[key] = path.read_text(encoding="utf-8")
        return self._cache[key]
