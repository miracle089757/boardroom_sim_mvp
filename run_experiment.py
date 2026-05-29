"""Command-line entry point for the boardroom simulation MVP."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from boardroom_sim.config import ExperimentConfig, load_experiment_config
from boardroom_sim.io import read_cases_jsonl, write_results_jsonl, write_traces_json
from boardroom_sim.llm import LLMClient, LLMConfig
from boardroom_sim.models import BoardCase, SimulationResult
from boardroom_sim.pitchbook import build_cases_from_pitchbook
from boardroom_sim.simulator import BoardroomSimulator


def parse_args() -> argparse.Namespace:
    """Parse Linux-friendly command-line arguments for one experiment run."""
    parser = argparse.ArgumentParser(description="Run the boardroom simulation MVP.")
    parser.add_argument(
        "--input",
        default="input/260524_02_03_pitchbook_sample_100_shared.xlsx",
        type=Path,
        help="Path to input JSONL cases or PitchBook XLSX workbook.",
    )
    parser.add_argument("--output", type=Path, required=True, help="Path to compact output JSONL results.")
    parser.add_argument("--trace-output", type=Path, required=True, help="Path to detailed trace JSON output.")
    parser.add_argument("--config", type=Path, default=None, help="Path to experiment TOML config.")
    parser.add_argument("--bargaining-rounds", type=int, default=None, help="Override bargaining rounds from config.")
    parser.add_argument("--case-limit", type=int, default=None, help="Optional maximum number of input cases to run.")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=None,
        help="Override config history limit. Use -1 for all history.",
    )
    parser.add_argument("--api-key", default=None, help="API key. Defaults to BOARDROOM_LLM_API_KEY.")
    parser.add_argument("--api-key-env", default="BOARDROOM_LLM_API_KEY", help="Environment variable containing API key.")
    parser.add_argument("--model", default="GLM-4-Flash-250414", help="LLM model name. Defaults to GLM-4-Flash-250414.")
    parser.add_argument("--base-url", default="https://api.z.ai/api/paas/v4", help="OpenAI-compatible base URL. Defaults to zhipuai.")
    parser.add_argument("--temperature", type=float, default=None, help="LLM temperature. Defaults to BOARDROOM_LLM_TEMPERATURE or 0.2.")
    parser.add_argument("--timeout-seconds", type=int, default=None, help="HTTP timeout. Defaults to BOARDROOM_LLM_TIMEOUT_SECONDS or 120.")
    parser.add_argument("--http-max-retries", type=int, default=None, help="HTTP retry count for transient LLM errors. Defaults to BOARDROOM_LLM_HTTP_MAX_RETRIES or 6.")
    parser.add_argument("--retry-base-seconds", type=float, default=None, help="Base seconds for exponential retry backoff. Defaults to BOARDROOM_LLM_RETRY_BASE_SECONDS or 2.0.")
    return parser.parse_args()


def load_cases(
    input_path: Path,
    case_limit: int | None = None,
    history_limit: int | None = 10,
) -> List[BoardCase]:
    """Load cases from either normalized JSONL or the PitchBook workbook."""
    if input_path.suffix.lower() in {".xlsx", ".xlsm"}:
        return build_cases_from_pitchbook(input_path, limit=case_limit, history_limit=history_limit)
    cases = read_cases_jsonl(input_path)
    return cases[:case_limit] if case_limit is not None else cases


def run_experiment(
    input_path: Path,
    bargaining_rounds: int,
    llm_client: LLMClient,
    case_limit: int | None = None,
    history_limit: int | None = 10,
    experiment_config: ExperimentConfig | None = None,
) -> List[SimulationResult]:
    """Load cases and run the boardroom simulator for each case."""
    cases = load_cases(input_path, case_limit=case_limit, history_limit=history_limit)
    simulator = BoardroomSimulator(
        llm_client=llm_client,
        bargaining_rounds=bargaining_rounds,
        config=experiment_config,
    )
    return [simulator.simulate(case) for case in cases]


def main() -> None:
    """Run the command-line experiment and write both compact and trace outputs."""
    args = parse_args()
    experiment_config = load_experiment_config(args.config)
    bargaining_rounds = (
        args.bargaining_rounds if args.bargaining_rounds is not None else experiment_config.bargaining_rounds
    )
    history_limit = args.history_limit if args.history_limit is not None else experiment_config.history_limit
    llm_config = LLMConfig.from_env(
        api_key=args.api_key,
        api_key_env=args.api_key_env,
        model=args.model,
        base_url=args.base_url,
        temperature=args.temperature,
        timeout_seconds=args.timeout_seconds,
        http_max_retries=args.http_max_retries,
        retry_base_seconds=args.retry_base_seconds,
    )
    llm_client = LLMClient(llm_config)
    results = run_experiment(
        args.input,
        bargaining_rounds,
        llm_client,
        case_limit=args.case_limit,
        history_limit=history_limit,
        experiment_config=experiment_config,
    )
    write_results_jsonl(args.output, results)
    write_traces_json(args.trace_output, results)
    print(f"Processed {len(results)} cases.")
    print(f"Wrote compact results to {args.output}.")
    print(f"Wrote detailed traces to {args.trace_output}.")
    print(f"LLM total tokens reported by provider: {llm_client.total_tokens}.")


if __name__ == "__main__":
    main()
