"""Input and output helpers for JSONL boardroom simulation files."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, List

from boardroom_sim.models import BoardCase, SimulationResult


def read_cases_jsonl(path: Path) -> List[BoardCase]:
    """Read board simulation cases from a JSONL file."""
    cases: List[BoardCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                raw = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
            cases.append(BoardCase.from_dict(raw))
    return cases


def write_results_jsonl(path: Path, results: Iterable[SimulationResult]) -> None:
    """Write compact simulation results to a JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for result in results:
            handle.write(json.dumps(result.to_dict(include_trace=False), ensure_ascii=False) + "\n")


def write_traces_json(path: Path, results: Iterable[SimulationResult]) -> None:
    """Write detailed simulation traces to one JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [result.to_dict(include_trace=True) for result in results]
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
