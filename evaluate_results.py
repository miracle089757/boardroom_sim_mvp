"""Evaluate compact boardroom simulation result JSONL files."""

from __future__ import annotations

import argparse
from pathlib import Path

from boardroom_sim.evaluation import (
    evaluate_results,
    metrics_summary,
    read_result_rows,
    write_case_metrics_csv,
    write_metrics_json,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for offline result evaluation."""
    parser = argparse.ArgumentParser(description="Evaluate boardroom simulation result JSONL files.")
    parser.add_argument("--input", type=Path, nargs="+", required=True, help="One or more compact results JSONL files.")
    parser.add_argument("--metrics-output", type=Path, default=None, help="Optional aggregate metrics JSON path.")
    parser.add_argument("--case-metrics-output", type=Path, default=None, help="Optional per-case metrics CSV path.")
    return parser.parse_args()


def main() -> None:
    """Read result files, compute metrics, and optionally write reports."""
    args = parse_args()
    rows = read_result_rows(args.input)
    metrics = evaluate_results(rows)
    print(metrics_summary(metrics))

    if args.metrics_output is not None:
        write_metrics_json(args.metrics_output, metrics)
        print(f"Wrote aggregate metrics to {args.metrics_output}.")
    if args.case_metrics_output is not None:
        write_case_metrics_csv(args.case_metrics_output, metrics["case_metrics"])
        print(f"Wrote per-case metrics to {args.case_metrics_output}.")


if __name__ == "__main__":
    main()
