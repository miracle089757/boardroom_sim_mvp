"""Run repeated boardroom experiments and write evaluation reports."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from analyze_debate_accuracy import (
    analyze_baseline_rows,
    analyze_cases,
    render_report as render_debate_accuracy_report,
    write_case_stage_csv,
)
from boardroom_sim.baselines import run_single_agent_baseline
from boardroom_sim.evaluation import (
    evaluate_results,
    metrics_summary,
    read_result_rows,
    write_case_metrics_csv,
    write_metrics_json,
)
from boardroom_sim.io import write_results_jsonl, write_traces_json
from boardroom_sim.llm import LLMClient, LLMConfig
from boardroom_sim.models import BoardCase, SimulationResult
from boardroom_sim.simulator import BoardroomSimulator
from run_experiment import load_cases


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for a batch experiment."""
    parser = argparse.ArgumentParser(description="Run repeated boardroom simulation experiments.")
    parser.add_argument(
        "--input",
        default="data/sample_cases.jsonl",
        type=Path,
        required=True,
        help="Path to input JSONL cases or PitchBook XLSX workbook.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for batch outputs.")
    parser.add_argument("--repeats", type=int, default=1, help="Number of repeated full experiment runs.")
    parser.add_argument("--bargaining-rounds", type=int, default=3, help="Number of bargaining rounds per case.")
    parser.add_argument("--case-limit", type=int, default=None, help="Optional maximum number of input cases to run.")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=10,
        help="Maximum number of recent historical records per history field. Use -1 for all history.",
    )
    parser.add_argument("--resume", action="store_true", help="Skip completed run directories with full result files.")
    parser.add_argument("--skip-traces", action="store_true", help="Do not write detailed trace JSON files.")
    parser.add_argument("--skip-baselines", action="store_true", help="Do not run the two single-agent baselines.")
    parser.add_argument(
        "--skip-debate-accuracy-report",
        action="store_true",
        help="Do not write debate_accuracy_report.md and debate_accuracy_cases.csv for each run.",
    )
    parser.add_argument(
        "--deal-size-tolerance",
        type=float,
        default=0.50,
        help="Relative tolerance used by debate accuracy report numeric correctness. Default: 0.50.",
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


def main() -> None:
    """Run batch experiments and write per-run plus aggregate metrics."""
    args = parse_args()
    if args.repeats < 1:
        raise ValueError("--repeats must be at least 1.")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases(args.input, case_limit=args.case_limit, history_limit=args.history_limit)
    if not cases:
        raise ValueError(f"No cases loaded from {args.input}.")

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

    _write_manifest(args.output_dir / "manifest.json", args, cases, llm_config)

    all_rows: List[Dict[str, Any]] = []
    baseline_rows_by_name: Dict[str, List[Dict[str, Any]]] = {
        "baseline_history_only": [],
        "baseline_history_with_roles": [],
    }
    for repeat_index in range(1, args.repeats + 1):
        run_id = f"run_{repeat_index:03d}"
        run_dir = args.output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        results_path = run_dir / "results.jsonl"
        traces_path = run_dir / "traces.json"
        trace_cases: List[Dict[str, Any]] | None = None

        rows = _maybe_read_completed_run(results_path, expected_count=len(cases), resume=args.resume)
        if rows is None:
            print(f"Starting {run_id}: {len(cases)} cases.")
            tokens_before = llm_client.total_tokens
            results = _run_cases(cases, llm_client, args.bargaining_rounds, run_id)
            token_delta = llm_client.total_tokens - tokens_before
            write_results_jsonl(results_path, results)
            if not args.skip_traces:
                write_traces_json(traces_path, results)
            rows = _result_rows(results, results_path, run_id)
            trace_cases = [result.to_dict(include_trace=True) for result in results]
            print(f"Finished {run_id}; provider-reported tokens this run: {token_delta}.")
        else:
            print(f"Skipping {run_id}; found completed results at {results_path}.")
            if traces_path.exists():
                trace_cases = _read_trace_cases(traces_path)

        run_metrics = evaluate_results(rows)
        write_metrics_json(run_dir / "metrics.json", run_metrics)
        write_case_metrics_csv(run_dir / "case_metrics.csv", run_metrics["case_metrics"])
        print(metrics_summary(run_metrics))
        print("")
        all_rows.extend(rows)

        run_baseline_rows_by_name: Dict[str, List[Dict[str, Any]]] = {}
        if not args.skip_baselines:
            for baseline_name, include_role_rules in [
                ("baseline_history_only", False),
                ("baseline_history_with_roles", True),
            ]:
                baseline_rows = _run_or_resume_baseline(
                    cases=cases,
                    llm_client=llm_client,
                    run_dir=run_dir,
                    run_id=run_id,
                    baseline_name=baseline_name,
                    include_role_rules=include_role_rules,
                    resume=args.resume,
                )
                baseline_metrics = evaluate_results(baseline_rows)
                write_metrics_json(run_dir / f"{baseline_name}_metrics.json", baseline_metrics)
                write_case_metrics_csv(run_dir / f"{baseline_name}_case_metrics.csv", baseline_metrics["case_metrics"])
                baseline_rows_by_name[baseline_name].extend(baseline_rows)
                run_baseline_rows_by_name[baseline_name] = baseline_rows
                print(f"{baseline_name} metrics:")
                print(metrics_summary(baseline_metrics))
                print("")

        if not args.skip_debate_accuracy_report:
            if trace_cases is not None:
                _write_debate_accuracy_report(
                    run_dir,
                    trace_cases,
                    args.deal_size_tolerance,
                    baseline_rows_by_name=run_baseline_rows_by_name,
                )
            else:
                print(f"Cannot write debate accuracy report for {run_id}; missing {traces_path}.")

    aggregate_metrics = evaluate_results(all_rows)
    write_metrics_json(args.output_dir / "aggregate_metrics.json", aggregate_metrics)
    write_case_metrics_csv(args.output_dir / "case_metrics.csv", aggregate_metrics["case_metrics"])
    print("Aggregate metrics across all runs:")
    print(metrics_summary(aggregate_metrics))
    if not args.skip_baselines:
        for baseline_name, baseline_rows in baseline_rows_by_name.items():
            baseline_metrics = evaluate_results(baseline_rows)
            write_metrics_json(args.output_dir / f"{baseline_name}_aggregate_metrics.json", baseline_metrics)
            write_case_metrics_csv(args.output_dir / f"{baseline_name}_case_metrics.csv", baseline_metrics["case_metrics"])
            print(f"Aggregate {baseline_name} metrics:")
            print(metrics_summary(baseline_metrics))
    print(f"Wrote aggregate metrics to {args.output_dir / 'aggregate_metrics.json'}.")
    print(f"Wrote aggregate per-case metrics to {args.output_dir / 'case_metrics.csv'}.")
    print(f"LLM total tokens reported by provider: {llm_client.total_tokens}.")


def _run_cases(
    cases: List[BoardCase],
    llm_client: LLMClient,
    bargaining_rounds: int,
    run_id: str,
) -> List[SimulationResult]:
    simulator = BoardroomSimulator(llm_client=llm_client, bargaining_rounds=bargaining_rounds)
    results: List[SimulationResult] = []
    for index, case in enumerate(cases, start=1):
        print(f"{run_id}: case {index}/{len(cases)} {case.case_id}")
        results.append(simulator.simulate(case))
    return results


def _maybe_read_completed_run(results_path: Path, *, expected_count: int, resume: bool) -> List[Dict[str, Any]] | None:
    if not resume or not results_path.exists():
        return None
    rows = read_result_rows([results_path])
    if len(rows) == expected_count:
        return rows
    print(f"Found {results_path} with {len(rows)} rows; expected {expected_count}. Rerunning this run.")
    return None


def _result_rows(results: List[SimulationResult], results_path: Path, run_id: str) -> List[Dict[str, Any]]:
    rows = []
    for result in results:
        row = result.to_dict(include_trace=False)
        row["_source_file"] = str(results_path)
        row["_run_id"] = run_id
        rows.append(row)
    return rows


def _run_or_resume_baseline(
    *,
    cases: List[BoardCase],
    llm_client: LLMClient,
    run_dir: Path,
    run_id: str,
    baseline_name: str,
    include_role_rules: bool,
    resume: bool,
) -> List[Dict[str, Any]]:
    results_path = run_dir / f"{baseline_name}_results.jsonl"
    existing_rows = _maybe_read_completed_run(results_path, expected_count=len(cases), resume=resume)
    if existing_rows is not None:
        print(f"Skipping {run_id} {baseline_name}; found completed results at {results_path}.")
        return existing_rows

    print(f"Starting {run_id} {baseline_name}: {len(cases)} cases.")
    rows = run_single_agent_baseline(
        cases,
        llm_client,
        include_role_rules=include_role_rules,
        baseline_name=baseline_name,
    )
    for row in rows:
        row["_source_file"] = str(results_path)
        row["_run_id"] = f"{run_id}/{baseline_name}"
    _write_rows_jsonl(results_path, rows)
    print(f"Finished {run_id} {baseline_name}.")
    return rows


def _write_rows_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def _write_debate_accuracy_report_from_results(
    run_dir: Path,
    results: List[SimulationResult],
    deal_size_tolerance: float,
    baseline_rows_by_name: Dict[str, List[Dict[str, Any]]] | None = None,
) -> None:
    cases = [result.to_dict(include_trace=True) for result in results]
    _write_debate_accuracy_report(run_dir, cases, deal_size_tolerance, baseline_rows_by_name=baseline_rows_by_name)


def _write_debate_accuracy_report_from_trace_file(
    run_dir: Path,
    traces_path: Path,
    deal_size_tolerance: float,
    baseline_rows_by_name: Dict[str, List[Dict[str, Any]]] | None = None,
) -> None:
    _write_debate_accuracy_report(
        run_dir,
        _read_trace_cases(traces_path),
        deal_size_tolerance,
        baseline_rows_by_name=baseline_rows_by_name,
    )


def _read_trace_cases(traces_path: Path) -> List[Dict[str, Any]]:
    data = json.loads(traces_path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else [data]


def _write_debate_accuracy_report(
    run_dir: Path,
    cases: List[Dict[str, Any]],
    deal_size_tolerance: float,
    *,
    baseline_rows_by_name: Dict[str, List[Dict[str, Any]]] | None = None,
) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    analysis = analyze_cases(cases, deal_size_tolerance=deal_size_tolerance)
    baseline_metrics = {
        name: analyze_baseline_rows(rows, baseline_name=name, deal_size_tolerance=deal_size_tolerance)
        for name, rows in (baseline_rows_by_name or {}).items()
    }
    report = render_debate_accuracy_report(
        analysis,
        deal_size_tolerance=deal_size_tolerance,
        baseline_metrics=baseline_metrics,
    )
    report_path = run_dir / "debate_accuracy_report.md"
    report_path.write_text(report + "\n", encoding="utf-8")
    write_case_stage_csv(run_dir / "debate_accuracy_cases.csv", analysis["case_stage_rows"])
    print(f"Wrote debate accuracy report to {report_path}.")


def _write_manifest(output_path: Path, args: argparse.Namespace, cases: List[BoardCase], llm_config: LLMConfig) -> None:
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input": str(args.input),
        "output_dir": str(args.output_dir),
        "case_count": len(cases),
        "case_limit": args.case_limit,
        "history_limit": args.history_limit,
        "repeats": args.repeats,
        "bargaining_rounds": args.bargaining_rounds,
        "resume": args.resume,
        "skip_traces": args.skip_traces,
        "skip_baselines": args.skip_baselines,
        "skip_debate_accuracy_report": args.skip_debate_accuracy_report,
        "deal_size_tolerance": args.deal_size_tolerance,
        "llm": {
            "api_key_env": args.api_key_env,
            "api_key_passed": bool(args.api_key),
            "model": llm_config.model,
            "base_url": llm_config.base_url,
            "temperature": llm_config.temperature,
            "timeout_seconds": llm_config.timeout_seconds,
            "http_max_retries": llm_config.http_max_retries,
            "retry_base_seconds": llm_config.retry_base_seconds,
        },
        "case_ids": [case.case_id for case in cases],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)


if __name__ == "__main__":
    main()
