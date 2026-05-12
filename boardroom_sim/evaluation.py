"""Offline evaluation helpers for boardroom simulation results."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, List, Optional, Sequence


ResultRow = Dict[str, Any]


CATEGORICAL_METRICS = [
    {
        "name": "financing_initiation",
        "prediction_field": "financing_initiation_decision",
        "label_field": "true_financing_initiated_label",
        "normalizer": "financing_intent",
        "drop_unknown_label": True,
    },
    {
        "name": "deal_type",
        "prediction_field": "predicted_deal_type",
        "label_field": "real_deal_type",
        "normalizer": "deal_type",
        "drop_unknown_label": True,
    },
    {
        "name": "valuation_direction",
        "prediction_field": "valuation_direction",
        "label_field": "real_valuation_direction_label",
        "normalizer": "valuation_direction",
        "drop_unknown_label": True,
    },
]


NUMERIC_METRICS = [
    {
        "name": "deal_size",
        "prediction_field": "predicted_deal_size_usd_m",
        "label_field": "real_deal_size_usd_m",
        "unit": "M USD",
        "positive_label_required": True,
    },
    {
        "name": "post_money_valuation",
        "prediction_field": "predicted_post_money_valuation_usd_m",
        "label_field": "real_post_money_valuation_usd_m",
        "unit": "M USD",
        "positive_label_required": True,
    },
    {
        "name": "investor_ownership",
        "prediction_field": "predicted_investor_ownership_pct",
        "label_field": "real_investor_ownership_pct",
        "unit": "pct",
        "positive_label_required": True,
    },
]


CASE_METRIC_FIELDS = [
    "source_file",
    "run_id",
    "case_id",
    "company_name",
    "pred_financing_initiation",
    "true_financing_initiation",
    "financing_initiation_correct",
    "pred_financing_completion",
    "true_financing_completion",
    "pred_deal_type",
    "true_deal_type",
    "deal_type_correct",
    "pred_valuation_direction",
    "true_valuation_direction",
    "valuation_direction_correct",
    "pred_deal_size_usd_m",
    "true_deal_size_usd_m",
    "deal_size_abs_error_usd_m",
    "deal_size_abs_pct_error",
    "deal_size_within_25pct",
    "deal_size_within_50pct",
    "pred_post_money_valuation_usd_m",
    "true_post_money_valuation_usd_m",
    "post_money_valuation_abs_error",
    "post_money_valuation_abs_pct_error",
    "post_money_valuation_within_25pct",
    "post_money_valuation_within_50pct",
    "pred_investor_ownership_pct",
    "true_investor_ownership_pct",
    "investor_ownership_abs_error",
    "investor_ownership_abs_pct_error",
    "investor_ownership_within_25pct",
    "investor_ownership_within_50pct",
]


def read_result_rows(paths: Sequence[Path]) -> List[ResultRow]:
    """Read one or more compact results JSONL files."""
    rows: List[ResultRow] = []
    for path in paths:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    row = json.loads(stripped)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"Invalid JSON on line {line_number} of {path}") from exc
                if not isinstance(row, dict):
                    raise ValueError(f"Expected object on line {line_number} of {path}")
                row.setdefault("_source_file", str(path))
                row.setdefault("_run_id", path.parent.name)
                rows.append(row)
    return rows


def evaluate_results(rows: Sequence[ResultRow]) -> Dict[str, Any]:
    """Compute categorical accuracy and numeric error metrics."""
    case_metrics = build_case_metrics(rows)
    categorical = {
        spec["name"]: _categorical_metric(rows, spec)
        for spec in CATEGORICAL_METRICS
    }
    numeric = {spec["name"]: _numeric_metric(rows, spec) for spec in NUMERIC_METRICS}
    return {
        "row_count": len(rows),
        "categorical": categorical,
        "numeric": numeric,
        "deal_size": numeric["deal_size"],
        "notes": [
            "Current data is positive-sample VC backtesting; financing initiation accuracy is a positive-sample hit rate unless negative samples are added.",
            "Financing completion is not counted in accuracy because almost all current target events are completed transactions.",
            "Valuation direction excludes rows whose true label is missing or unknown.",
            "Numeric metrics skip rows whose true numeric label is missing or non-positive.",
            "CEO replacement is intentionally excluded from current evaluation.",
        ],
        "case_metrics": case_metrics,
    }


def metrics_summary(metrics: Dict[str, Any]) -> str:
    """Return a compact human-readable metrics report."""
    lines = [f"Rows evaluated: {metrics.get('row_count', 0)}", "", "Categorical accuracy:"]
    for name, item in metrics.get("categorical", {}).items():
        evaluated = item.get("evaluated_count", 0)
        correct = item.get("correct_count", 0)
        accuracy = item.get("accuracy")
        accuracy_text = _format_pct(accuracy)
        skipped = item.get("skipped_count", 0)
        lines.append(f"  {name}: {correct}/{evaluated} = {accuracy_text} (skipped: {skipped})")

    lines.extend(["", "Numeric error:"])
    for name, item in metrics.get("numeric", {"deal_size": metrics.get("deal_size", {})}).items():
        unit = item.get("unit", "")
        unit_suffix = f" {unit}" if unit else ""
        lines.extend(
            [
                f"  {name}:",
                f"    evaluated: {item.get('evaluated_count', 0)} (skipped: {item.get('skipped_count', 0)})",
                f"    MAE: {_format_float(item.get('mae'))}{unit_suffix}",
                f"    RMSE: {_format_float(item.get('rmse'))}{unit_suffix}",
                f"    MAPE: {_format_pct(item.get('mape'))}",
                f"    Median APE: {_format_pct(item.get('median_ape'))}",
                f"    within +/-25%: {_format_pct(item.get('within_25pct_rate'))}",
                f"    within +/-50%: {_format_pct(item.get('within_50pct_rate'))}",
            ]
        )
    return "\n".join(lines)


def build_case_metrics(rows: Sequence[ResultRow]) -> List[Dict[str, Any]]:
    """Build one per-case metrics row for CSV inspection."""
    case_rows: List[Dict[str, Any]] = []
    for row in rows:
        labels = _labels(row)
        case_metric = {
            "source_file": row.get("_source_file", ""),
            "run_id": row.get("_run_id", ""),
            "case_id": row.get("case_id", ""),
            "company_name": row.get("company_name", ""),
        }

        _add_categorical_case_metric(
            case_metric,
            row,
            labels,
            metric_prefix="financing_initiation",
            prediction_field="financing_initiation_decision",
            label_field="true_financing_initiated_label",
            normalizer="financing_intent",
        )
        case_metric["pred_financing_completion"] = _normalize(row.get("financing_completion_view"), "completion")
        case_metric["true_financing_completion"] = _normalize(labels.get("real_deal_completed_label"), "completion")
        _add_categorical_case_metric(
            case_metric,
            row,
            labels,
            metric_prefix="deal_type",
            prediction_field="predicted_deal_type",
            label_field="real_deal_type",
            normalizer="deal_type",
        )
        _add_categorical_case_metric(
            case_metric,
            row,
            labels,
            metric_prefix="valuation_direction",
            prediction_field="valuation_direction",
            label_field="real_valuation_direction_label",
            normalizer="valuation_direction",
        )

        _add_numeric_case_metric(
            case_metric,
            row,
            labels,
            prefix="deal_size",
            prediction_field="predicted_deal_size_usd_m",
            label_field="real_deal_size_usd_m",
            prediction_column="pred_deal_size_usd_m",
            label_column="true_deal_size_usd_m",
            absolute_error_column="deal_size_abs_error_usd_m",
        )
        _add_numeric_case_metric(
            case_metric,
            row,
            labels,
            prefix="post_money_valuation",
            prediction_field="predicted_post_money_valuation_usd_m",
            label_field="real_post_money_valuation_usd_m",
            prediction_column="pred_post_money_valuation_usd_m",
            label_column="true_post_money_valuation_usd_m",
            absolute_error_column="post_money_valuation_abs_error",
        )
        _add_numeric_case_metric(
            case_metric,
            row,
            labels,
            prefix="investor_ownership",
            prediction_field="predicted_investor_ownership_pct",
            label_field="real_investor_ownership_pct",
            prediction_column="pred_investor_ownership_pct",
            label_column="true_investor_ownership_pct",
            absolute_error_column="investor_ownership_abs_error",
        )
        case_rows.append(case_metric)
    return case_rows


def write_metrics_json(path: Path, metrics: Dict[str, Any]) -> None:
    """Write aggregate metrics without embedding per-case rows."""
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(metrics)
    payload.pop("case_metrics", None)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, allow_nan=False)


def write_case_metrics_csv(path: Path, case_metrics: Iterable[Dict[str, Any]]) -> None:
    """Write per-case metric rows to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_METRIC_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in case_metrics:
            writer.writerow(row)


def _categorical_metric(rows: Sequence[ResultRow], spec: Dict[str, Any]) -> Dict[str, Any]:
    correct_count = 0
    evaluated_count = 0
    skipped_count = 0
    confusion: Dict[str, Dict[str, int]] = {}

    for row in rows:
        labels = _labels(row)
        prediction = _normalize(row.get(spec["prediction_field"]), spec["normalizer"])
        label = _normalize(labels.get(spec["label_field"]), spec["normalizer"])
        if _is_missing_label(label, spec.get("drop_unknown_label", True)):
            skipped_count += 1
            continue
        evaluated_count += 1
        predicted_key = prediction or "missing_prediction"
        label_key = label or "missing_label"
        confusion.setdefault(label_key, {})
        confusion[label_key][predicted_key] = confusion[label_key].get(predicted_key, 0) + 1
        if prediction == label:
            correct_count += 1

    accuracy = correct_count / evaluated_count if evaluated_count else None
    return {
        "prediction_field": spec["prediction_field"],
        "label_field": spec["label_field"],
        "evaluated_count": evaluated_count,
        "skipped_count": skipped_count,
        "correct_count": correct_count,
        "accuracy": accuracy,
        "confusion": confusion,
    }


def _numeric_metric(rows: Sequence[ResultRow], spec: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[float] = []
    squared_errors: List[float] = []
    pct_errors: List[float] = []
    predicted_values: List[float] = []
    true_values: List[float] = []
    skipped_count = 0

    for row in rows:
        labels = _labels(row)
        predicted = _optional_float(row.get(spec["prediction_field"]))
        true = _optional_float(labels.get(spec["label_field"]))
        if predicted is None or true is None or (spec.get("positive_label_required", True) and true <= 0):
            skipped_count += 1
            continue
        error = abs(predicted - true)
        errors.append(error)
        squared_errors.append(error**2)
        if true != 0:
            pct_errors.append(error / abs(true))
        predicted_values.append(predicted)
        true_values.append(true)

    evaluated_count = len(errors)
    metric = {
        "prediction_field": spec["prediction_field"],
        "label_field": spec["label_field"],
        "unit": spec.get("unit", ""),
        "evaluated_count": evaluated_count,
        "skipped_count": skipped_count,
        "mae": _mean(errors),
        "rmse": math.sqrt(_mean(squared_errors)) if squared_errors else None,
        "mape": _mean(pct_errors),
        "median_ape": median(pct_errors) if pct_errors else None,
        "within_25pct_rate": _mean([1.0 if value <= 0.25 else 0.0 for value in pct_errors]),
        "within_50pct_rate": _mean([1.0 if value <= 0.50 else 0.0 for value in pct_errors]),
        "mean_predicted": _mean(predicted_values),
        "mean_true": _mean(true_values),
    }
    if spec["name"] == "deal_size":
        metric["mae_usd_m"] = metric["mae"]
        metric["rmse_usd_m"] = metric["rmse"]
        metric["mean_predicted_usd_m"] = metric["mean_predicted"]
        metric["mean_true_usd_m"] = metric["mean_true"]
    return metric


def _deal_size_metric(rows: Sequence[ResultRow]) -> Dict[str, Any]:
    """Backward-compatible deal-size metric wrapper."""
    return _numeric_metric(rows, NUMERIC_METRICS[0])


def _add_categorical_case_metric(
    case_metric: Dict[str, Any],
    row: ResultRow,
    labels: Dict[str, Any],
    *,
    metric_prefix: str,
    prediction_field: str,
    label_field: str,
    normalizer: str,
) -> None:
    prediction = _normalize(row.get(prediction_field), normalizer)
    label = _normalize(labels.get(label_field), normalizer)
    short_prefix = {
        "financing_initiation": "financing_initiation",
        "financing_completion": "financing_completion",
        "deal_type": "deal_type",
        "valuation_direction": "valuation_direction",
    }[metric_prefix]
    case_metric[f"pred_{short_prefix}"] = prediction
    case_metric[f"true_{short_prefix}"] = label
    case_metric[f"{short_prefix}_correct"] = None if _is_missing_label(label, True) else prediction == label


def _add_numeric_case_metric(
    case_metric: Dict[str, Any],
    row: ResultRow,
    labels: Dict[str, Any],
    *,
    prefix: str,
    prediction_field: str,
    label_field: str,
    prediction_column: str,
    label_column: str,
    absolute_error_column: str,
) -> None:
    predicted = _optional_float(row.get(prediction_field))
    true = _optional_float(labels.get(label_field))
    case_metric[prediction_column] = predicted
    case_metric[label_column] = true
    pct_error_column = f"{prefix}_abs_pct_error"
    within_25_column = f"{prefix}_within_25pct"
    within_50_column = f"{prefix}_within_50pct"
    if predicted is not None and true is not None and true > 0:
        absolute_error = abs(predicted - true)
        absolute_pct_error = absolute_error / true
        case_metric[absolute_error_column] = absolute_error
        case_metric[pct_error_column] = absolute_pct_error
        case_metric[within_25_column] = absolute_pct_error <= 0.25
        case_metric[within_50_column] = absolute_pct_error <= 0.50
    else:
        case_metric[absolute_error_column] = None
        case_metric[pct_error_column] = None
        case_metric[within_25_column] = None
        case_metric[within_50_column] = None


def _labels(row: ResultRow) -> Dict[str, Any]:
    labels = row.get("labels", {})
    return labels if isinstance(labels, dict) else {}


def _normalize(value: Any, normalizer: str) -> Optional[str]:
    if _is_missing_value(value):
        return None
    if normalizer == "financing_intent":
        return _normalize_token(value)
    if normalizer == "completion":
        return _normalize_completion(value)
    if normalizer == "deal_type":
        return _normalize_deal_type(value)
    if normalizer == "valuation_direction":
        return _normalize_valuation_direction(value)
    return _normalize_token(value)


def _normalize_token(value: Any) -> Optional[str]:
    if _is_missing_value(value):
        return None
    text = str(value).strip().lower().replace("-", "_").replace(" ", "_")
    while "__" in text:
        text = text.replace("__", "_")
    return text or None


def _normalize_completion(value: Any) -> Optional[str]:
    token = _normalize_token(value)
    if token is None:
        return None
    completed = {"completed", "complete", "closed", "done", "likely_complete"}
    failed = {"cancelled", "canceled", "terminated", "failed", "dead", "unlikely_complete"}
    pending = {"announced", "pending", "in_progress", "open", "uncertain"}
    if token in completed:
        return "likely_complete"
    if token in failed:
        return "unlikely_complete"
    if token in pending:
        return "uncertain"
    return token


def _normalize_deal_type(value: Any) -> Optional[str]:
    if _is_missing_value(value):
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


def _normalize_valuation_direction(value: Any) -> Optional[str]:
    token = _normalize_token(str(value).lower().replace(" round", "")) if not _is_missing_value(value) else None
    if token in {"up", "upround", "up_round"}:
        return "up"
    if token in {"flat", "flattish", "flatround", "flat_round"}:
        return "flat"
    if token in {"down", "downround", "down_round"}:
        return "down"
    if token in {"unknown", "none", "nan", "n/a", "na"}:
        return None
    return token


def _is_missing_value(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and math.isnan(value):
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def _is_missing_label(value: Optional[str], drop_unknown_label: bool) -> bool:
    if value is None:
        return True
    return drop_unknown_label and value in {
        "unknown",
        "none",
        "nan",
        "n/a",
        "na",
        "unknown_deal_type",
        "unknown deal type",
    }


def _optional_float(value: Any) -> Optional[float]:
    if _is_missing_value(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _format_pct(value: Any) -> str:
    number = _optional_float(value)
    return "n/a" if number is None else f"{number * 100:.2f}%"


def _format_float(value: Any) -> str:
    number = _optional_float(value)
    return "n/a" if number is None else f"{number:.3f}"
