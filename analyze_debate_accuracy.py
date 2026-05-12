"""Compare pre- and post-bargaining prediction accuracy from trace files."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from boardroom_sim.evaluation import read_result_rows
from boardroom_sim.simulator import ROLE_WEIGHTS


CATEGORICAL_METRICS = [
    {
        "name": "financing_initiation",
        "prediction_field": "financing_initiation_decision",
        "role_field": "financing_intent",
        "label_field": "true_financing_initiated_label",
        "normalizer": "financing_intent",
    },
    {
        "name": "deal_type",
        "prediction_field": "predicted_deal_type",
        "role_field": "predicted_deal_type",
        "label_field": "real_deal_type",
        "normalizer": "deal_type",
    },
    {
        "name": "valuation_direction",
        "prediction_field": "valuation_direction",
        "role_field": "valuation_direction",
        "label_field": "real_valuation_direction_label",
        "normalizer": "valuation_direction",
    },
]
NUMERIC_METRICS = [
    {
        "name": "deal_size",
        "prediction_field": "predicted_deal_size_usd_m",
        "role_field": "predicted_deal_size_usd_m",
        "label_field": "real_deal_size_usd_m",
        "unit": "M USD",
    },
    {
        "name": "post_money_valuation",
        "prediction_field": "predicted_post_money_valuation_usd_m",
        "role_field": "predicted_post_money_valuation_usd_m",
        "label_field": "real_post_money_valuation_usd_m",
        "unit": "M USD",
    },
    {
        "name": "investor_ownership",
        "prediction_field": "predicted_investor_ownership_pct",
        "role_field": "predicted_investor_ownership_pct",
        "label_field": "real_investor_ownership_pct",
        "unit": "pct",
    },
]
METRIC_NAMES = [item["name"] for item in CATEGORICAL_METRICS] + [item["name"] for item in NUMERIC_METRICS]
CASE_CSV_FIELDS = [
    "case_id",
    "stage",
    "financing_initiation_prediction",
    "financing_initiation_correct",
    "financing_completion_prediction",
    "deal_type_prediction",
    "deal_type_correct",
    "valuation_direction_prediction",
    "valuation_direction_correct",
    "deal_size_prediction",
    "deal_size_true",
    "deal_size_abs_error",
    "deal_size_abs_pct_error",
    "deal_size_within_tolerance",
    "post_money_valuation_prediction",
    "post_money_valuation_true",
    "post_money_valuation_abs_error",
    "post_money_valuation_abs_pct_error",
    "post_money_valuation_within_tolerance",
    "investor_ownership_prediction",
    "investor_ownership_true",
    "investor_ownership_abs_error",
    "investor_ownership_abs_pct_error",
    "investor_ownership_within_tolerance",
]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Analyze whether bargaining improves prediction accuracy.")
    parser.add_argument("--input", type=Path, required=True, help="Trace JSON file, usually outputs/.../traces.json.")
    parser.add_argument("--output", type=Path, default=None, help="Optional Markdown report output path.")
    parser.add_argument("--case-csv-output", type=Path, default=None, help="Optional per-case stage CSV output path.")
    parser.add_argument(
        "--baseline-results",
        action="append",
        default=[],
        help="Optional baseline result JSONL in NAME=PATH format. Can be passed more than once.",
    )
    parser.add_argument(
        "--deal-size-tolerance",
        type=float,
        default=0.50,
        help="Relative tolerance for treating deal-size prediction as correct. Default: 0.50.",
    )
    return parser.parse_args()


def main() -> None:
    """Generate an accuracy-change report from a trace file."""
    args = parse_args()
    if args.deal_size_tolerance < 0:
        raise ValueError("--deal-size-tolerance must be non-negative.")
    cases = read_trace_cases(args.input)
    analysis = analyze_cases(cases, deal_size_tolerance=args.deal_size_tolerance)
    baseline_metrics = read_baseline_metrics(args.baseline_results, deal_size_tolerance=args.deal_size_tolerance)
    report = render_report(
        analysis,
        deal_size_tolerance=args.deal_size_tolerance,
        baseline_metrics=baseline_metrics,
    )
    print(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"\nWrote debate-accuracy report to {args.output}.")
    if args.case_csv_output is not None:
        write_case_stage_csv(args.case_csv_output, analysis["case_stage_rows"])
        print(f"Wrote per-case stage accuracy CSV to {args.case_csv_output}.")


def read_trace_cases(path: Path) -> List[Dict[str, Any]]:
    """Read traces from JSON or JSONL."""
    if path.suffix.lower() == ".jsonl":
        items: List[Dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                item = json.loads(stripped)
                if not isinstance(item, dict):
                    raise ValueError(f"Expected object on line {line_number} of {path}")
                items.append(item)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = [data]
        else:
            raise ValueError(f"Expected JSON object or list in {path}")
    if any(not item.get("trace") for item in items):
        raise ValueError("This analysis requires detailed traces. Use traces.json, not compact results.jsonl.")
    return items


def analyze_cases(cases: Sequence[Dict[str, Any]], *, deal_size_tolerance: float) -> Dict[str, Any]:
    """Analyze stage-level accuracy and correctness transitions."""
    case_sequences = [build_case_sequence(case, deal_size_tolerance=deal_size_tolerance) for case in cases]
    stages = ordered_stages(case_sequences)
    stage_metrics = {stage: compute_stage_metrics(case_sequences, stage) for stage in stages}
    transitions = compute_transitions(case_sequences, stages)
    initial_to_final = compute_transitions(case_sequences, ["initial", "final"])
    return {
        "case_count": len(cases),
        "stages": stages,
        "stage_metrics": stage_metrics,
        "transitions": transitions,
        "initial_to_final": initial_to_final,
        "case_stage_rows": flatten_case_stage_rows(case_sequences),
    }


def analyze_baseline_rows(
    rows: Sequence[Dict[str, Any]],
    *,
    baseline_name: str,
    deal_size_tolerance: float,
) -> Dict[str, Any]:
    """Score single-agent baseline result rows as one final-stage predictor."""
    case_sequences = []
    for row in rows:
        labels = row.get("labels", {}) if isinstance(row.get("labels", {}), dict) else {}
        prediction = {
            "financing_initiation_decision": row.get("financing_initiation_decision"),
            "financing_completion_view": row.get("financing_completion_view"),
            "predicted_deal_size_usd_m": row.get("predicted_deal_size_usd_m"),
            "predicted_post_money_valuation_usd_m": row.get("predicted_post_money_valuation_usd_m"),
            "predicted_investor_ownership_pct": row.get("predicted_investor_ownership_pct"),
            "predicted_deal_type": row.get("predicted_deal_type"),
            "valuation_direction": row.get("valuation_direction"),
        }
        case_sequences.append(
            {
                "case_id": row.get("case_id", ""),
                "labels": labels,
                "stages": [score_prediction(baseline_name, prediction, labels, deal_size_tolerance)],
            }
        )
    return compute_stage_metrics(case_sequences, baseline_name)


def read_baseline_metrics(specs: Sequence[str], *, deal_size_tolerance: float) -> Dict[str, Dict[str, Any]]:
    """Read optional NAME=PATH baseline specs and score them for report rendering."""
    metrics: Dict[str, Dict[str, Any]] = {}
    for spec in specs:
        if "=" not in spec:
            raise ValueError(f"--baseline-results must use NAME=PATH format, got: {spec}")
        name, raw_path = spec.split("=", 1)
        name = name.strip()
        path = Path(raw_path.strip())
        if not name:
            raise ValueError(f"Baseline name is empty in spec: {spec}")
        rows = read_result_rows([path])
        metrics[name] = analyze_baseline_rows(rows, baseline_name=name, deal_size_tolerance=deal_size_tolerance)
    return metrics


def build_case_sequence(case: Dict[str, Any], *, deal_size_tolerance: float) -> Dict[str, Any]:
    """Build one case's aggregate prediction sequence across bargaining stages."""
    labels = case.get("labels", {}) if isinstance(case.get("labels", {}), dict) else {}
    context: Dict[str, Dict[str, Any]] = {}
    stages: List[Dict[str, Any]] = []

    for event in case.get("trace", []):
        stage = event.get("stage")
        actor = event.get("actor")
        payload = event.get("payload", {}) if isinstance(event.get("payload", {}), dict) else {}
        if stage == "private_assessment" and actor:
            context[str(actor)] = payload

    stages.append(stage_snapshot("initial", context, labels, deal_size_tolerance))

    context = {role: dict(decision) for role, decision in context.items()}
    for event in case.get("trace", []):
        stage = str(event.get("stage", ""))
        actor = str(event.get("actor", ""))
        payload = event.get("payload", {}) if isinstance(event.get("payload", {}), dict) else {}
        if stage.startswith("bargaining_round_"):
            updated = payload.get("updated_decision", {})
            if actor and isinstance(updated, dict):
                context[actor] = updated
            continue
        if stage.startswith("proposal_after_round_"):
            round_name = "round_" + stage.rsplit("_", 1)[-1]
            stages.append(stage_snapshot(round_name, context, labels, deal_size_tolerance))

    final_prediction = {
        "financing_initiation_decision": case.get("financing_initiation_decision"),
        "financing_completion_view": case.get("financing_completion_view"),
        "predicted_deal_size_usd_m": case.get("predicted_deal_size_usd_m"),
        "predicted_post_money_valuation_usd_m": case.get("predicted_post_money_valuation_usd_m"),
        "predicted_investor_ownership_pct": case.get("predicted_investor_ownership_pct"),
        "predicted_deal_type": case.get("predicted_deal_type"),
        "valuation_direction": case.get("valuation_direction"),
    }
    stages.append(score_prediction("final", final_prediction, labels, deal_size_tolerance))
    return {
        "case_id": case.get("case_id", ""),
        "labels": labels,
        "stages": stages,
    }


def stage_snapshot(
    stage: str,
    context: Dict[str, Dict[str, Any]],
    labels: Dict[str, Any],
    deal_size_tolerance: float,
) -> Dict[str, Any]:
    """Aggregate role decisions and score the stage."""
    prediction = {
        "financing_initiation_decision": weighted_choice(context, "financing_intent", "raise_now"),
        "financing_completion_view": weighted_choice(context, "completion_view", "likely_complete"),
        "predicted_deal_size_usd_m": aggregate_deal_size(context),
        "predicted_post_money_valuation_usd_m": aggregate_positive_numeric(
            context,
            "predicted_post_money_valuation_usd_m",
        ),
        "predicted_investor_ownership_pct": aggregate_positive_numeric(
            context,
            "predicted_investor_ownership_pct",
        ),
        "predicted_deal_type": weighted_choice(context, "predicted_deal_type", "unknown"),
        "valuation_direction": weighted_choice(context, "valuation_direction", "flat"),
    }
    return score_prediction(stage, prediction, labels, deal_size_tolerance)


def score_prediction(
    stage: str,
    prediction: Dict[str, Any],
    labels: Dict[str, Any],
    deal_size_tolerance: float,
) -> Dict[str, Any]:
    """Score one aggregate prediction against labels."""
    scored: Dict[str, Any] = {"stage": stage, "prediction": prediction, "scores": {}}
    for metric in CATEGORICAL_METRICS:
        pred = normalize(prediction.get(metric["prediction_field"]), metric["normalizer"])
        label = normalize(labels.get(metric["label_field"]), metric["normalizer"])
        scored["scores"][metric["name"]] = {
            "prediction": pred,
            "label": label,
            "correct": None if is_missing_label(label) else pred == label,
        }

    for metric in NUMERIC_METRICS:
        predicted = optional_float(prediction.get(metric["prediction_field"]))
        true = optional_float(labels.get(metric["label_field"]))
        if predicted is None or true is None or true <= 0:
            numeric_score = {
                "prediction": predicted,
                "label": true,
                "correct": None,
                "abs_error": None,
                "abs_pct_error": None,
            }
        else:
            abs_error = abs(predicted - true)
            abs_pct_error = abs_error / true
            numeric_score = {
                "prediction": predicted,
                "label": true,
                "correct": abs_pct_error <= deal_size_tolerance,
                "abs_error": abs_error,
                "abs_pct_error": abs_pct_error,
            }
        scored["scores"][metric["name"]] = numeric_score
    return scored


def compute_stage_metrics(case_sequences: Sequence[Dict[str, Any]], stage: str) -> Dict[str, Any]:
    """Compute accuracy and error metrics for one stage."""
    snapshots = [get_stage(case, stage) for case in case_sequences]
    snapshots = [item for item in snapshots if item is not None]
    metrics: Dict[str, Any] = {"case_count": len(snapshots)}
    for metric in METRIC_NAMES:
        scores = [snapshot["scores"][metric] for snapshot in snapshots]
        evaluated = [score for score in scores if score["correct"] is not None]
        correct_count = sum(1 for score in evaluated if score["correct"])
        item = {
            "evaluated_count": len(evaluated),
            "skipped_count": len(scores) - len(evaluated),
            "correct_count": correct_count,
            "accuracy": correct_count / len(evaluated) if evaluated else None,
        }
        if metric in {item["name"] for item in NUMERIC_METRICS}:
            pct_errors = [score["abs_pct_error"] for score in scores if score.get("abs_pct_error") is not None]
            abs_errors = [score["abs_error"] for score in scores if score.get("abs_error") is not None]
            item.update(
                {
                    "mae_usd_m": mean(abs_errors) if abs_errors else None,
                    "mape": mean(pct_errors) if pct_errors else None,
                    "median_ape": median(pct_errors) if pct_errors else None,
                }
            )
        metrics[metric] = item
    return metrics


def compute_transitions(case_sequences: Sequence[Dict[str, Any]], stages: Sequence[str]) -> Dict[str, Any]:
    """Compute correctness transitions between adjacent stages."""
    transitions: Dict[str, Any] = {}
    for before_stage, after_stage in zip(stages, stages[1:]):
        key = f"{before_stage}_to_{after_stage}"
        transitions[key] = {}
        for metric in METRIC_NAMES:
            counter: Counter[str] = Counter()
            error_counter: Counter[str] = Counter()
            evaluated = 0
            for case in case_sequences:
                before = get_stage(case, before_stage)
                after = get_stage(case, after_stage)
                if before is None or after is None:
                    continue
                before_score = before["scores"][metric]
                after_score = after["scores"][metric]
                before_correct = before_score["correct"]
                after_correct = after_score["correct"]
                if before_correct is None or after_correct is None:
                    counter["skipped"] += 1
                    continue
                evaluated += 1
                counter[transition_label(before_correct, after_correct)] += 1
                if metric in {item["name"] for item in NUMERIC_METRICS}:
                    before_error = before_score.get("abs_pct_error")
                    after_error = after_score.get("abs_pct_error")
                    error_counter[error_change_label(before_error, after_error)] += 1
            transitions[key][metric] = {
                "evaluated_count": evaluated,
                "skipped_count": counter["skipped"],
                "counts": dict(counter),
                "rates": {name: count / evaluated for name, count in counter.items() if name != "skipped" and evaluated},
                "numeric_error_change_counts": dict(error_counter) if metric in {item["name"] for item in NUMERIC_METRICS} else None,
                "deal_size_error_change_counts": dict(error_counter) if metric == "deal_size" else None,
            }
    return transitions


def render_report(
    analysis: Dict[str, Any],
    *,
    deal_size_tolerance: float,
    baseline_metrics: Optional[Dict[str, Dict[str, Any]]] = None,
) -> str:
    """Render a Markdown report."""
    section = 1
    lines = [
        "# 辩论前后准确度变化报告",
        "",
        f"- 分析案例数：{analysis['case_count']}",
        f"- 数值指标正确判定阈值：预测值相对真实值误差 <= {deal_size_tolerance:.0%}",
        "- 交易完成判断暂不计入准确率，因为当前样本几乎全部是已完成交易。",
        "",
        f"## {section}. 各阶段预测准确度",
        "",
        render_stage_accuracy_table(analysis["stage_metrics"], analysis["stages"]),
        "",
    ]
    section += 1
    if baseline_metrics:
        lines.extend(
            [
                f"## {section}. 单 Agent Baseline 对比",
                "",
                render_baseline_comparison_table(analysis, baseline_metrics),
                "",
            ]
        )
        section += 1

    lines.extend(
        [
        f"## {section}. 辩论前 vs 辩论后",
        "",
        render_transition_block(analysis["initial_to_final"], "initial_to_final"),
        "",
        f"## {section + 1}. 随辩论轮次推进的正确性变化",
        "",
        render_all_transitions(analysis["transitions"]),
        "",
        f"## {section + 2}. 数值预测是否更接近真实值",
        "",
        render_numeric_error_transitions(analysis["initial_to_final"], analysis["transitions"]),
        "",
        f"## {section + 3}. 数值误差随阶段变化",
        "",
        render_numeric_error_table(analysis["stage_metrics"], analysis["stages"]),
        ]
    )
    return "\n".join(lines)


def render_stage_accuracy_table(stage_metrics: Dict[str, Any], stages: Sequence[str]) -> str:
    """Render stage-level accuracy table."""
    headers = ["stage", "financing_initiation", "deal_type", "valuation_direction", "deal_size", "post_money_valuation", "investor_ownership"]
    lines = ["| " + " | ".join(headers) + " |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
    for stage in stages:
        metrics = stage_metrics[stage]
        values = []
        for metric in headers[1:]:
            item = metrics[metric]
            values.append(f"{item['correct_count']}/{item['evaluated_count']} ({format_pct(item['accuracy'])})")
        lines.append(f"| {stage} | " + " | ".join(values) + " |")
    return "\n".join(lines)


def render_baseline_comparison_table(
    analysis: Dict[str, Any],
    baseline_metrics: Dict[str, Dict[str, Any]],
) -> str:
    """Render final multi-agent accuracy next to single-agent baselines."""
    headers = ["system", "rows", "financing_initiation", "deal_type", "valuation_direction", "deal_size", "post_money_valuation", "investor_ownership"]
    lines = ["| " + " | ".join(headers) + " |", "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |"]
    final_stage = "final" if "final" in analysis["stage_metrics"] else analysis["stages"][-1]
    rows: List[Tuple[str, Dict[str, Any]]] = [("multi_agent_final", analysis["stage_metrics"][final_stage])]
    rows.extend(baseline_metrics.items())
    for name, metrics in rows:
        values = [name, str(metrics.get("case_count", 0))]
        for metric in headers[2:]:
            item = metrics[metric]
            values.append(f"{item['correct_count']}/{item['evaluated_count']} ({format_pct(item['accuracy'])})")
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def render_transition_block(transitions: Dict[str, Any], transition_key: str) -> str:
    """Render one transition table."""
    if transition_key not in transitions:
        return "无可用变化。"
    lines = [
        f"### {transition_key}",
        "",
        "| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for metric, item in transitions[transition_key].items():
        counts = item["counts"]
        evaluated = item["evaluated_count"]
        lines.append(
            f"| {metric} | {count_rate(counts.get('wrong_to_correct', 0), evaluated)} | "
            f"{count_rate(counts.get('correct_to_wrong', 0), evaluated)} | "
            f"{count_rate(counts.get('correct_to_correct', 0), evaluated)} | "
            f"{count_rate(counts.get('wrong_to_wrong', 0), evaluated)} | {evaluated} |"
        )
    return "\n".join(lines)


def render_all_transitions(transitions: Dict[str, Any]) -> str:
    """Render all adjacent-stage transition tables."""
    return "\n\n".join(render_transition_block(transitions, key) for key in transitions)


def render_numeric_error_table(stage_metrics: Dict[str, Any], stages: Sequence[str]) -> str:
    """Render continuous numeric error by stage."""
    lines = [
        "| metric | stage | evaluated | MAE | MAPE | Median APE |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for metric in NUMERIC_METRICS:
        name = metric["name"]
        unit = metric.get("unit", "")
        unit_suffix = f" {unit}" if unit else ""
        for stage in stages:
            item = stage_metrics[stage][name]
            lines.append(
                f"| {name} | {stage} | {item['evaluated_count']} | {format_float(item.get('mae_usd_m'))}{unit_suffix} | "
                f"{format_pct(item.get('mape'))} | {format_pct(item.get('median_ape'))} |"
            )
    return "\n".join(lines)


def render_numeric_error_transitions(initial_to_final: Dict[str, Any], transitions: Dict[str, Any]) -> str:
    """Render whether continuous numeric errors became closer or farther."""
    rows: List[Tuple[str, str, Dict[str, Any]]] = []
    if "initial_to_final" in initial_to_final:
        for metric in NUMERIC_METRICS:
            name = metric["name"]
            rows.append((name, "initial_to_final", initial_to_final["initial_to_final"][name]))
    for key, item in transitions.items():
        for metric in NUMERIC_METRICS:
            name = metric["name"]
            rows.append((name, key, item[name]))
    if not rows:
        return "无可用数值误差变化。"

    lines = [
        "| metric | transition | closer | farther | same | evaluated |",
        "| --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for metric, transition, item in rows:
        counts = item.get("numeric_error_change_counts") or item.get("deal_size_error_change_counts") or {}
        total = sum(counts.get(name, 0) for name in ("closer", "farther", "same"))
        lines.append(
            f"| {metric} | {transition} | {count_rate(counts.get('closer', 0), total)} | "
            f"{count_rate(counts.get('farther', 0), total)} | "
            f"{count_rate(counts.get('same', 0), total)} | {total} |"
        )
    return "\n".join(lines)


def write_case_stage_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """Write per-case stage-level correctness rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def flatten_case_stage_rows(case_sequences: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten case stage snapshots for CSV inspection."""
    rows: List[Dict[str, Any]] = []
    for case in case_sequences:
        for snapshot in case["stages"]:
            scores = snapshot["scores"]
            rows.append(
                {
                    "case_id": case["case_id"],
                    "stage": snapshot["stage"],
                    "financing_initiation_prediction": scores["financing_initiation"]["prediction"],
                    "financing_initiation_correct": scores["financing_initiation"]["correct"],
                    "financing_completion_prediction": snapshot["prediction"].get("financing_completion_view"),
                    "deal_type_prediction": scores["deal_type"]["prediction"],
                    "deal_type_correct": scores["deal_type"]["correct"],
                    "valuation_direction_prediction": scores["valuation_direction"]["prediction"],
                    "valuation_direction_correct": scores["valuation_direction"]["correct"],
                    "deal_size_prediction": scores["deal_size"]["prediction"],
                    "deal_size_true": scores["deal_size"]["label"],
                    "deal_size_abs_error": scores["deal_size"]["abs_error"],
                    "deal_size_abs_pct_error": scores["deal_size"]["abs_pct_error"],
                    "deal_size_within_tolerance": scores["deal_size"]["correct"],
                    "post_money_valuation_prediction": scores["post_money_valuation"]["prediction"],
                    "post_money_valuation_true": scores["post_money_valuation"]["label"],
                    "post_money_valuation_abs_error": scores["post_money_valuation"]["abs_error"],
                    "post_money_valuation_abs_pct_error": scores["post_money_valuation"]["abs_pct_error"],
                    "post_money_valuation_within_tolerance": scores["post_money_valuation"]["correct"],
                    "investor_ownership_prediction": scores["investor_ownership"]["prediction"],
                    "investor_ownership_true": scores["investor_ownership"]["label"],
                    "investor_ownership_abs_error": scores["investor_ownership"]["abs_error"],
                    "investor_ownership_abs_pct_error": scores["investor_ownership"]["abs_pct_error"],
                    "investor_ownership_within_tolerance": scores["investor_ownership"]["correct"],
                }
            )
    return rows


def ordered_stages(case_sequences: Sequence[Dict[str, Any]]) -> List[str]:
    """Return stable stage names across all cases."""
    names = []
    for case in case_sequences:
        for snapshot in case["stages"]:
            name = snapshot["stage"]
            if name not in names:
                names.append(name)
    round_names = sorted([name for name in names if name.startswith("round_")], key=lambda name: int(name.split("_")[1]))
    result = ["initial"] + round_names + ["final"]
    return [name for name in result if name in names]


def get_stage(case: Dict[str, Any], stage: str) -> Optional[Dict[str, Any]]:
    """Return one named stage snapshot."""
    for snapshot in case["stages"]:
        if snapshot["stage"] == stage:
            return snapshot
    return None


def weighted_choice(context: Dict[str, Dict[str, Any]], field: str, default: str) -> str:
    """Weighted modal choice matching the simulator."""
    scores: Counter[str] = Counter()
    for role, decision in context.items():
        value = decision.get(field, default)
        if value:
            scores[str(value)] += ROLE_WEIGHTS.get(role, 1.0)
    if not scores:
        return default
    return scores.most_common(1)[0][0]


def aggregate_deal_size(context: Dict[str, Dict[str, Any]]) -> Optional[float]:
    """Weighted average deal size matching the simulator."""
    return aggregate_positive_numeric(context, "predicted_deal_size_usd_m")


def aggregate_positive_numeric(context: Dict[str, Dict[str, Any]], field: str) -> Optional[float]:
    """Weighted average of a positive numeric role prediction matching the simulator."""
    weighted_total = 0.0
    weight_total = 0.0
    observed_count = 0
    for role, decision in context.items():
        if field not in decision:
            continue
        value = optional_float(decision.get(field))
        if value is not None:
            observed_count += 1
        if value is None or value <= 0 or decision.get("financing_intent") == "avoid":
            continue
        weight = ROLE_WEIGHTS.get(role, 1.0)
        weighted_total += value * weight
        weight_total += weight
    if observed_count <= 0:
        return None
    if weight_total <= 0:
        return 0.0
    return round(weighted_total / weight_total, 6)


def transition_label(before_correct: bool, after_correct: bool) -> str:
    """Name a correctness transition."""
    if not before_correct and after_correct:
        return "wrong_to_correct"
    if before_correct and not after_correct:
        return "correct_to_wrong"
    if before_correct and after_correct:
        return "correct_to_correct"
    return "wrong_to_wrong"


def error_change_label(before_error: Optional[float], after_error: Optional[float], tolerance: float = 1e-9) -> str:
    """Name continuous error movement."""
    if before_error is None or after_error is None:
        return "skipped"
    if after_error < before_error - tolerance:
        return "closer"
    if after_error > before_error + tolerance:
        return "farther"
    return "same"


def normalize(value: Any, normalizer: str) -> Optional[str]:
    """Normalize predictions and labels for comparison."""
    if is_missing_value(value):
        return None
    if normalizer == "completion":
        return normalize_completion(value)
    if normalizer == "deal_type":
        return normalize_deal_type(value)
    if normalizer == "valuation_direction":
        return normalize_valuation_direction(value)
    return normalize_token(value)


def normalize_token(value: Any) -> Optional[str]:
    """Normalize simple categorical text."""
    if is_missing_value(value):
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text or None


def normalize_completion(value: Any) -> Optional[str]:
    """Normalize deal completion labels."""
    token = normalize_token(value)
    if token is None:
        return None
    if token in {"completed", "complete", "closed", "done", "likely_complete"}:
        return "likely_complete"
    if token in {"cancelled", "canceled", "terminated", "failed", "dead", "unlikely_complete"}:
        return "unlikely_complete"
    if token in {"announced", "pending", "in_progress", "open", "uncertain"}:
        return "uncertain"
    return token


def normalize_deal_type(value: Any) -> Optional[str]:
    """Normalize deal-type labels."""
    if is_missing_value(value):
        return None
    text = " ".join(str(value).strip().lower().replace("-", " ").replace("_", " ").split())
    aliases = {
        "seed": "seed round",
        "seed vc": "seed round",
        "early stage": "early stage vc",
        "early stage venture": "early stage vc",
        "later stage": "later stage vc",
        "later stage venture": "later stage vc",
        "venture capital": "other",
    }
    return aliases.get(text, text)


def normalize_valuation_direction(value: Any) -> Optional[str]:
    """Normalize valuation-direction labels."""
    token = normalize_token(str(value).lower().replace(" round", "")) if not is_missing_value(value) else None
    if token in {"up", "upround", "up_round"}:
        return "up"
    if token in {"flat", "flattish", "flatround", "flat_round"}:
        return "flat"
    if token in {"down", "downround", "down_round"}:
        return "down"
    if token in {"unknown", "none", "nan", "n/a", "na"}:
        return None
    return token


def is_missing_label(value: Optional[str]) -> bool:
    """Return whether a normalized label should be skipped."""
    return value is None or value in {"unknown", "none", "nan", "n/a", "na", "unknown_deal_type", "unknown deal type"}


def is_missing_value(value: Any) -> bool:
    """Return whether a raw value is missing."""
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def optional_float(value: Any) -> Optional[float]:
    """Parse a finite float."""
    if is_missing_value(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def count_rate(count: int, total: int) -> str:
    """Format count and rate."""
    if total <= 0:
        return f"{count} (n/a)"
    return f"{count} ({count / total:.2%})"


def format_pct(value: Any) -> str:
    """Format a nullable float percentage."""
    number = optional_float(value)
    return "n/a" if number is None else f"{number:.2%}"


def format_float(value: Any) -> str:
    """Format a nullable float."""
    number = optional_float(value)
    return "n/a" if number is None else f"{number:.3f}"


if __name__ == "__main__":
    main()
