#!/usr/bin/env python3
"""Command-line entry point for the boardroom simulation MVP."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from boardroom_sim.io import read_cases_jsonl, write_results_jsonl, write_traces_json
from boardroom_sim.llm import LLMClient, LLMConfig
from boardroom_sim.models import SimulationResult
from boardroom_sim.simulator import BoardroomSimulator


def parse_args() -> argparse.Namespace:
    """Parse Linux-friendly command-line arguments for one experiment run."""
    parser = argparse.ArgumentParser(description="Run the boardroom simulation MVP.")
    parser.add_argument("--input", type=Path, required=True, help="Path to input JSONL cases.")
    parser.add_argument("--output", type=Path, required=True, help="Path to compact output JSONL results.")
    parser.add_argument("--trace-output", type=Path, required=True, help="Path to detailed trace JSON output.")
    parser.add_argument("--bargaining-rounds", type=int, default=2, help="Number of deterministic bargaining rounds.")
    parser.add_argument("--api-key-env", default="BOARDROOM_LLM_API_KEY", help="Environment variable containing API key.")
    parser.add_argument("--model", default=None, help="LLM model name. Defaults to BOARDROOM_LLM_MODEL or glm-4.7-flash.")
    parser.add_argument("--base-url", default=None, help="OpenAI-compatible base URL. Defaults to BOARDROOM_LLM_BASE_URL.")
    parser.add_argument("--temperature", type=float, default=None, help="LLM temperature. Defaults to BOARDROOM_LLM_TEMPERATURE or 0.2.")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="HTTP timeout. Defaults to BOARDROOM_LLM_TIMEOUT_SECONDS or 120.")
    return parser.parse_args()


def run_experiment(input_path: Path, bargaining_rounds: int, llm_client: LLMClient) -> List[SimulationResult]:
    """Load cases and run the boardroom simulator for each case."""
    cases = read_cases_jsonl(input_path)
    simulator = BoardroomSimulator(llm_client=llm_client, bargaining_rounds=bargaining_rounds)
    return [simulator.simulate(case) for case in cases]


def main() -> None:
    """Run the command-line experiment and write both compact and trace outputs."""
    args = parse_args()
    llm_config = LLMConfig.from_env(
        api_key_env=args.api_key_env,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        timeout_seconds=args.timeout_seconds,
    )
    llm_client = LLMClient(llm_config)
    results = run_experiment(args.input, args.bargaining_rounds, llm_client)
    write_results_jsonl(args.output, results)
    write_traces_json(args.trace_output, results)
    print(f"Processed {len(results)} cases.")
    print(f"Wrote compact results to {args.output}.")
    print(f"Wrote detailed traces to {args.trace_output}.")
    print(f"LLM total tokens reported by provider: {llm_client.total_tokens}.")


if __name__ == "__main__":
    main()
