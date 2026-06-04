"""Run repeated boardroom experiments and write evaluation reports."""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

import analyze_debate_accuracy as debate_accuracy_module
from analyze_debate_accuracy import (
    analyze_baseline_rows,
    analyze_cases,
    render_report as render_debate_accuracy_report,
    write_case_stage_csv,
)
from boardroom_sim.baselines import predict_single_case
from boardroom_sim.config import ExperimentConfig, load_experiment_config
from boardroom_sim.evaluation import (
    evaluate_results,
    metrics_summary,
    read_result_rows,
    write_case_metrics_csv,
    write_metrics_json,
)
from boardroom_sim.llm import LLMClient, LLMConfig
from boardroom_sim.models import BoardCase, SimulationResult
from boardroom_sim.simulator import BoardroomSimulator
from run_experiment import load_cases


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for a batch experiment."""
    parser = argparse.ArgumentParser(description="Run repeated boardroom simulation experiments.")
    parser.add_argument(
        "--input",
        default="input/260524_02_03_pitchbook_sample_100_shared.xlsx",
        type=Path,
        help="Path to input JSONL cases or PitchBook XLSX workbook.",
    )
    parser.add_argument("--output-dir", type=Path, required=True, help="Directory for batch outputs.")
    parser.add_argument("--repeats", type=int, default=1, help="Number of repeated full experiment runs.")
    parser.add_argument("--config", type=Path, default=None, help="Path to experiment TOML config.")
    parser.add_argument(
        "--bargaining-rounds",
        type=int,
        default=None,
        help="Override the maximum discussion rounds from config.",
    )
    parser.add_argument("--case-limit", type=int, default=None, help="Optional maximum number of input cases to run.")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=None,
        help="Override config history limit. Use -1 for all history.",
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

    experiment_config = load_experiment_config(args.config)
    debate_accuracy_module.ROLE_WEIGHTS = dict(experiment_config.role_weights)
    bargaining_rounds = (
        args.bargaining_rounds if args.bargaining_rounds is not None else experiment_config.bargaining_rounds
    )
    history_limit = args.history_limit if args.history_limit is not None else experiment_config.history_limit
    args.bargaining_rounds = bargaining_rounds
    args.history_limit = history_limit

    args.output_dir.mkdir(parents=True, exist_ok=True)
    cases = load_cases(args.input, case_limit=args.case_limit, history_limit=history_limit)
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

    _write_manifest(args.output_dir / "manifest.json", args, cases, llm_config, experiment_config)

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
            rows, trace_cases = _run_cases_with_checkpoints(
                cases=cases,
                llm_client=llm_client,
                bargaining_rounds=bargaining_rounds,
                experiment_config=experiment_config,
                run_dir=run_dir,
                run_id=run_id,
                resume=args.resume,
                skip_traces=args.skip_traces,
            )
            token_delta = llm_client.total_tokens - tokens_before
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
                    role_policy_dir=experiment_config.role_policy_dir,
                    prompts_dir=experiment_config.prompts_dir,
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
    experiment_config: ExperimentConfig,
    run_id: str,
) -> List[SimulationResult]:
    simulator = BoardroomSimulator(
        llm_client=llm_client,
        bargaining_rounds=bargaining_rounds,
        config=experiment_config,
    )
    results: List[SimulationResult] = []
    for index, case in enumerate(cases, start=1):
        print(f"{run_id}: case {index}/{len(cases)} {case.case_id}", flush=True)
        results.append(simulator.simulate(case))
    return results


def _run_cases_with_checkpoints(
    *,
    cases: List[BoardCase],
    llm_client: LLMClient,
    bargaining_rounds: int,
    experiment_config: ExperimentConfig,
    run_dir: Path,
    run_id: str,
    resume: bool,
    skip_traces: bool,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]] | None]:
    """Run main simulation and persist results after every completed case."""
    simulator = BoardroomSimulator(
        llm_client=llm_client,
        bargaining_rounds=bargaining_rounds,
        config=experiment_config,
    )
    results_path = run_dir / "results.jsonl"
    traces_jsonl_path = run_dir / "traces.jsonl"
    traces_path = run_dir / "traces.json"
    metrics_path = run_dir / "metrics.json"
    case_metrics_path = run_dir / "case_metrics.csv"
    status_path = run_dir / "checkpoint_status.json"

    if resume:
        rows = _read_existing_rows(results_path, run_id=run_id)
        trace_cases = _read_existing_trace_cases(traces_jsonl_path, traces_path) if not skip_traces else None
    else:
        _truncate_file(results_path)
        if not skip_traces:
            _truncate_file(traces_jsonl_path)
        rows = []
        trace_cases = [] if not skip_traces else None

    completed_case_ids = {str(row.get("case_id", "")) for row in rows if row.get("case_id")}
    if completed_case_ids:
        print(f"{run_id}: resuming with {len(completed_case_ids)}/{len(cases)} completed cases.", flush=True)

    for index, case in enumerate(cases, start=1):
        if case.case_id in completed_case_ids:
            print(f"{run_id}: skip completed case {index}/{len(cases)} {case.case_id}", flush=True)
            continue

        print(f"{run_id}: case {index}/{len(cases)} {case.case_id}", flush=True)
        result = simulator.simulate(case)
        row_payload = result.to_dict(include_trace=False)
        _append_jsonl_row(results_path, row_payload)
        row = dict(row_payload)
        row["_source_file"] = str(results_path)
        row["_run_id"] = run_id
        rows.append(row)

        if not skip_traces:
            trace_payload = result.to_dict(include_trace=True)
            _append_jsonl_row(traces_jsonl_path, trace_payload)
            if trace_cases is not None:
                trace_cases.append(trace_payload)

        _write_partial_run_outputs(
            rows=rows,
            metrics_path=metrics_path,
            case_metrics_path=case_metrics_path,
            status_path=status_path,
            run_id=run_id,
            expected_count=len(cases),
            completed_count=len(rows),
            last_case_id=case.case_id,
            llm_client=llm_client,
        )

    if not skip_traces and trace_cases is not None:
        _write_trace_cases_json(traces_path, trace_cases)
    _write_checkpoint_status(
        status_path,
        run_id=run_id,
        expected_count=len(cases),
        completed_count=len(rows),
        last_case_id=rows[-1].get("case_id", "") if rows else "",
        llm_client=llm_client,
        status="completed" if len(rows) == len(cases) else "partial",
    )
    return rows, trace_cases


def _maybe_read_completed_run(results_path: Path, *, expected_count: int, resume: bool) -> List[Dict[str, Any]] | None:
    if not resume or not results_path.exists():
        return None
    rows = read_result_rows([results_path])
    if len(rows) == expected_count:
        return rows
    print(f"Found {results_path} with {len(rows)} rows; expected {expected_count}. Resuming remaining cases.")
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
    role_policy_dir: Path | None,
    prompts_dir: Path | None,
    resume: bool,
) -> List[Dict[str, Any]]:
    results_path = run_dir / f"{baseline_name}_results.jsonl"
    existing_rows = _maybe_read_completed_run(results_path, expected_count=len(cases), resume=resume)
    if existing_rows is not None:
        for row in existing_rows:
            row["_run_id"] = f"{run_id}/{baseline_name}"
        print(f"Skipping {run_id} {baseline_name}; found completed results at {results_path}.")
        return existing_rows

    print(f"Starting {run_id} {baseline_name}: {len(cases)} cases.")
    metrics_path = run_dir / f"{baseline_name}_metrics.json"
    case_metrics_path = run_dir / f"{baseline_name}_case_metrics.csv"
    status_path = run_dir / f"{baseline_name}_checkpoint_status.json"
    baseline_run_id = f"{run_id}/{baseline_name}"
    if resume:
        rows = _read_existing_rows(results_path, run_id=baseline_run_id)
    else:
        _truncate_file(results_path)
        rows = []

    completed_case_ids = {str(row.get("case_id", "")) for row in rows if row.get("case_id")}
    if completed_case_ids:
        print(
            f"{run_id} {baseline_name}: resuming with {len(completed_case_ids)}/{len(cases)} completed cases.",
            flush=True,
        )

    for index, case in enumerate(cases, start=1):
        if case.case_id in completed_case_ids:
            print(f"{run_id} {baseline_name}: skip completed case {index}/{len(cases)} {case.case_id}", flush=True)
            continue
        print(f"{run_id} {baseline_name}: case {index}/{len(cases)} {case.case_id}", flush=True)
        row_payload = predict_single_case(
            case,
            llm_client,
            include_role_rules=include_role_rules,
            baseline_name=baseline_name,
            role_policy_dir=role_policy_dir,
            prompts_dir=prompts_dir,
        )
        _append_jsonl_row(results_path, row_payload)
        row = dict(row_payload)
        row["_source_file"] = str(results_path)
        row["_run_id"] = baseline_run_id
        rows.append(row)
        _write_partial_run_outputs(
            rows=rows,
            metrics_path=metrics_path,
            case_metrics_path=case_metrics_path,
            status_path=status_path,
            run_id=baseline_run_id,
            expected_count=len(cases),
            completed_count=len(rows),
            last_case_id=case.case_id,
            llm_client=llm_client,
        )

    _write_checkpoint_status(
        status_path,
        run_id=baseline_run_id,
        expected_count=len(cases),
        completed_count=len(rows),
        last_case_id=rows[-1].get("case_id", "") if rows else "",
        llm_client=llm_client,
        status="completed" if len(rows) == len(cases) else "partial",
    )
    print(f"Finished {run_id} {baseline_name}.")
    return rows


def _write_rows_jsonl(path: Path, rows: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")


def _read_existing_rows(results_path: Path, *, run_id: str) -> List[Dict[str, Any]]:
    if not results_path.exists():
        return []
    rows = read_result_rows([results_path])
    for row in rows:
        row["_source_file"] = str(results_path)
        row["_run_id"] = run_id
    return _dedupe_rows_by_case(rows)


def _dedupe_rows_by_case(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Keep the first completed row for each case id, preserving file order."""
    seen = set()
    deduped = []
    for row in rows:
        case_id = str(row.get("case_id", ""))
        if not case_id or case_id in seen:
            continue
        seen.add(case_id)
        deduped.append(row)
    return deduped


def _read_existing_trace_cases(traces_jsonl_path: Path, traces_path: Path) -> List[Dict[str, Any]]:
    if traces_jsonl_path.exists():
        return _read_jsonl_objects(traces_jsonl_path)
    if traces_path.exists():
        return _read_trace_cases(traces_path)
    return []


def _read_jsonl_objects(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                item = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
            if not isinstance(item, dict):
                raise ValueError(f"Expected object on line {line_number} of {path}")
            rows.append(item)
    return _dedupe_rows_by_case(rows)


def _append_jsonl_row(path: Path, row: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, allow_nan=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _truncate_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def _write_trace_cases_json(path: Path, trace_cases: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(trace_cases, handle, ensure_ascii=False, indent=2, allow_nan=False)


def _write_partial_run_outputs(
    *,
    rows: List[Dict[str, Any]],
    metrics_path: Path,
    case_metrics_path: Path,
    status_path: Path,
    run_id: str,
    expected_count: int,
    completed_count: int,
    last_case_id: str,
    llm_client: LLMClient,
) -> None:
    metrics = evaluate_results(rows)
    write_metrics_json(metrics_path, metrics)
    write_case_metrics_csv(case_metrics_path, metrics["case_metrics"])
    _write_checkpoint_status(
        status_path,
        run_id=run_id,
        expected_count=expected_count,
        completed_count=completed_count,
        last_case_id=last_case_id,
        llm_client=llm_client,
        status="running",
    )


def _write_checkpoint_status(
    path: Path,
    *,
    run_id: str,
    expected_count: int,
    completed_count: int,
    last_case_id: str,
    llm_client: LLMClient,
    status: str,
) -> None:
    payload = {
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "run_id": run_id,
        "status": status,
        "expected_count": expected_count,
        "completed_count": completed_count,
        "remaining_count": max(0, expected_count - completed_count),
        "last_case_id": last_case_id,
        "total_tokens": llm_client.total_tokens,
        "total_prompt_tokens": llm_client.total_prompt_tokens,
        "total_completion_tokens": llm_client.total_completion_tokens,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")


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


def _write_manifest(
    output_path: Path,
    args: argparse.Namespace,
    cases: List[BoardCase],
    llm_config: LLMConfig,
    experiment_config: ExperimentConfig,
) -> None:
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "input": str(args.input),
        "output_dir": str(args.output_dir),
        "case_count": len(cases),
        "case_limit": args.case_limit,
        "history_limit": args.history_limit,
        "repeats": args.repeats,
        "bargaining_rounds": args.bargaining_rounds,
        "experiment_config": experiment_config.to_manifest_dict(),
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
