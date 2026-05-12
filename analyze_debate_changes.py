"""Analyze how boardroom predictions change during bargaining."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, median
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


ROLE_FIELDS = [
    "financing_intent",
    "completion_view",
    "predicted_deal_type",
    "valuation_direction",
]
NUMERIC_ROLE_FIELDS = [
    "predicted_deal_size_usd_m",
    "predicted_post_money_valuation_usd_m",
    "predicted_investor_ownership_pct",
    "satisfaction_score",
]
PROPOSAL_FIELDS = [
    "recommended_deal_type",
    "valuation_direction",
    "investor_protection_level",
    "tech_budget_protected",
]
NUMERIC_PROPOSAL_FIELDS = [
    "recommended_deal_size_usd_m",
    "recommended_post_money_valuation_usd_m",
    "recommended_investor_ownership_pct",
    "estimated_dilution_pct",
]
CASE_CSV_FIELDS = [
    "case_id",
    "company_name",
    "role_field_changes",
    "role_size_changes",
    "role_satisfaction_changes",
    "proposal_field_changes",
    "proposal_size_delta",
    "initial_proposal_size",
    "final_proposal_size",
    "initial_proposal_type",
    "final_proposal_type",
    "initial_proposal_valuation",
    "final_proposal_valuation",
    "final_deal_type",
    "true_deal_type",
    "final_valuation_direction",
    "true_valuation_direction",
    "final_deal_size_usd_m",
    "true_deal_size_usd_m",
]


@dataclass
class FieldChange:
    """Represent one field change caused during bargaining."""

    case_id: str
    role: str
    field: str
    before: Any
    after: Any
    round_label: str


@dataclass
class NumericChange:
    """Represent one numeric field movement caused during bargaining."""

    case_id: str
    role: str
    field: str
    before: Optional[float]
    after: Optional[float]
    delta: Optional[float]
    round_label: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Analyze prediction changes in boardroom trace files.")
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Trace JSON file, usually outputs/.../run_001/traces.json.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Optional Markdown report output path. If omitted, prints only to stdout.",
    )
    parser.add_argument(
        "--case-csv-output",
        type=Path,
        default=None,
        help="Optional CSV with one row per case summarizing debate changes.",
    )
    parser.add_argument("--top-cases", type=int, default=12, help="Number of most changed cases to show.")
    return parser.parse_args()


def main() -> None:
    """Read traces, analyze debate changes, and write a human-readable report."""
    args = parse_args()
    cases = read_trace_cases(args.input)
    analysis = analyze_cases(cases)
    report = render_report(analysis, top_cases=args.top_cases)
    print(report)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(report + "\n", encoding="utf-8")
        print(f"\nWrote debate-change report to {args.output}.")
    if args.case_csv_output is not None:
        write_case_csv(args.case_csv_output, analysis["case_summaries"])
        print(f"Wrote case-level debate-change CSV to {args.case_csv_output}.")


def read_trace_cases(path: Path) -> List[Dict[str, Any]]:
    """Read a trace JSON file with embedded per-case traces."""
    if path.suffix.lower() == ".jsonl":
        cases = []
        with path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                item = json.loads(stripped)
                if not isinstance(item, dict):
                    raise ValueError(f"Expected object on line {line_number} of {path}")
                cases.append(item)
    else:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            cases = data
        elif isinstance(data, dict):
            cases = [data]
        else:
            raise ValueError(f"Expected a JSON object or list in {path}")

    missing_trace = [item.get("case_id", "<unknown>") for item in cases if not item.get("trace")]
    if missing_trace:
        sample = ", ".join(missing_trace[:5])
        raise ValueError(
            "Input does not contain detailed traces. Use traces.json, not compact results.jsonl. "
            f"Missing trace for {len(missing_trace)} case(s), including: {sample}"
        )
    return cases


def analyze_cases(cases: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze role-level and proposal-level changes across cases."""
    role_field_changes: List[FieldChange] = []
    role_numeric_changes: List[NumericChange] = []
    round_field_changes: Counter[Tuple[str, str]] = Counter()
    round_numeric_changes: Counter[Tuple[str, str]] = Counter()
    proposal_field_changes: List[FieldChange] = []
    proposal_numeric_changes: List[NumericChange] = []
    case_summaries: List[Dict[str, Any]] = []

    for case in cases:
        case_id = str(case.get("case_id", "unknown_case"))
        company_name = str(case.get("company_name", ""))
        initial_decisions = _initial_role_decisions(case)
        final_decisions = _final_role_decisions(case)
        role_order = sorted(set(initial_decisions) | set(final_decisions))

        case_role_field_changes = 0
        case_role_size_changes = 0
        case_role_satisfaction_changes = 0
        case_proposal_field_changes = 0

        for role in role_order:
            before = initial_decisions.get(role, {})
            after = final_decisions.get(role, {})
            for field in ROLE_FIELDS:
                if _normalized(before.get(field)) != _normalized(after.get(field)):
                    change = FieldChange(case_id, role, field, before.get(field), after.get(field), "initial_to_final")
                    role_field_changes.append(change)
                    case_role_field_changes += 1
            for field in NUMERIC_ROLE_FIELDS:
                before_value = _optional_float(before.get(field))
                after_value = _optional_float(after.get(field))
                if _numeric_changed(before_value, after_value):
                    change = NumericChange(
                        case_id=case_id,
                        role=role,
                        field=field,
                        before=before_value,
                        after=after_value,
                        delta=_delta(before_value, after_value),
                        round_label="initial_to_final",
                    )
                    role_numeric_changes.append(change)
                    if field == "predicted_deal_size_usd_m":
                        case_role_size_changes += 1
                    elif field == "satisfaction_score":
                        case_role_satisfaction_changes += 1

        for change in _round_level_changes(case, initial_decisions):
            if isinstance(change, FieldChange):
                role_field_changes.append(change)
                round_field_changes[(change.round_label, change.field)] += 1
            else:
                role_numeric_changes.append(change)
                round_numeric_changes[(change.round_label, change.field)] += 1

        initial_proposal = _initial_proposal(case)
        final_proposal = _final_proposal(case)
        for field in PROPOSAL_FIELDS:
            if _normalized(initial_proposal.get(field)) != _normalized(final_proposal.get(field)):
                proposal_field_changes.append(
                    FieldChange(case_id, "system", field, initial_proposal.get(field), final_proposal.get(field), "initial_to_final")
                )
                case_proposal_field_changes += 1
        for field in NUMERIC_PROPOSAL_FIELDS:
            before_value = _optional_float(initial_proposal.get(field))
            after_value = _optional_float(final_proposal.get(field))
            if _numeric_changed(before_value, after_value):
                proposal_numeric_changes.append(
                    NumericChange(
                        case_id=case_id,
                        role="system",
                        field=field,
                        before=before_value,
                        after=after_value,
                        delta=_delta(before_value, after_value),
                        round_label="initial_to_final",
                    )
                )

        labels = case.get("labels", {}) if isinstance(case.get("labels", {}), dict) else {}
        case_summaries.append(
            {
                "case_id": case_id,
                "company_name": company_name,
                "role_field_changes": case_role_field_changes,
                "role_size_changes": case_role_size_changes,
                "role_satisfaction_changes": case_role_satisfaction_changes,
                "proposal_field_changes": case_proposal_field_changes,
                "proposal_size_delta": _delta(
                    _optional_float(initial_proposal.get("recommended_deal_size_usd_m")),
                    _optional_float(final_proposal.get("recommended_deal_size_usd_m")),
                ),
                "initial_proposal_size": _optional_float(initial_proposal.get("recommended_deal_size_usd_m")),
                "final_proposal_size": _optional_float(final_proposal.get("recommended_deal_size_usd_m")),
                "initial_proposal_type": initial_proposal.get("recommended_deal_type"),
                "final_proposal_type": final_proposal.get("recommended_deal_type"),
                "initial_proposal_valuation": initial_proposal.get("valuation_direction"),
                "final_proposal_valuation": final_proposal.get("valuation_direction"),
                "final_deal_type": case.get("predicted_deal_type"),
                "true_deal_type": labels.get("real_deal_type"),
                "final_valuation_direction": case.get("valuation_direction"),
                "true_valuation_direction": labels.get("real_valuation_direction_label"),
                "final_deal_size_usd_m": _optional_float(case.get("predicted_deal_size_usd_m")),
                "true_deal_size_usd_m": _optional_float(labels.get("real_deal_size_usd_m")),
            }
        )

    return {
        "case_count": len(cases),
        "role_field_changes": role_field_changes,
        "role_numeric_changes": role_numeric_changes,
        "round_field_changes": round_field_changes,
        "round_numeric_changes": round_numeric_changes,
        "proposal_field_changes": proposal_field_changes,
        "proposal_numeric_changes": proposal_numeric_changes,
        "case_summaries": case_summaries,
    }


def render_report(analysis: Dict[str, Any], *, top_cases: int) -> str:
    """Render a Markdown report describing debate-induced changes."""
    case_count = analysis["case_count"]
    role_field_changes: List[FieldChange] = analysis["role_field_changes"]
    role_numeric_changes: List[NumericChange] = analysis["role_numeric_changes"]
    proposal_field_changes: List[FieldChange] = analysis["proposal_field_changes"]
    proposal_numeric_changes: List[NumericChange] = analysis["proposal_numeric_changes"]
    case_summaries: List[Dict[str, Any]] = analysis["case_summaries"]

    final_role_field_changes = [item for item in role_field_changes if item.round_label == "initial_to_final"]
    final_role_numeric_changes = [item for item in role_numeric_changes if item.round_label == "initial_to_final"]
    size_changes = [item for item in final_role_numeric_changes if item.field == "predicted_deal_size_usd_m"]
    post_money_changes = [item for item in final_role_numeric_changes if item.field == "predicted_post_money_valuation_usd_m"]
    ownership_changes = [item for item in final_role_numeric_changes if item.field == "predicted_investor_ownership_pct"]
    satisfaction_changes = [item for item in final_role_numeric_changes if item.field == "satisfaction_score"]

    lines = [
        "# 辩论变化分析报告",
        "",
        "## 总览",
        "",
        f"- 分析案例数：{case_count}",
        f"- 角色分类字段在辩论前后发生变化：{len(final_role_field_changes)} 次",
        f"- 角色预测融资额在辩论前后发生变化：{len(size_changes)} 次",
        f"- 角色预测投后估值在辩论前后发生变化：{len(post_money_changes)} 次",
        f"- 角色预测投资人持股在辩论前后发生变化：{len(ownership_changes)} 次",
        f"- 角色满意度在辩论前后发生变化：{len(satisfaction_changes)} 次",
        f"- 最终提案分类字段在辩论前后发生变化：{len(proposal_field_changes)} 次",
        f"- 最终提案数值字段在辩论前后发生变化：{len(proposal_numeric_changes)} 次",
        "",
        "解释：这里的“辩论前后”指每个角色的初始 private assessment 与全部 bargaining 结束后的最终 role decision 之间的差异。",
        "",
        "## 角色字段变化",
        "",
        _render_counter_table(
            "按字段统计",
            Counter(change.field for change in final_role_field_changes),
            ["field", "changes"],
        ),
        "",
        _render_counter_table(
            "按角色统计",
            Counter(change.role for change in final_role_field_changes),
            ["role", "changes"],
        ),
        "",
        _render_transition_table("分类字段变化方向", final_role_field_changes),
        "",
        "## 数值字段变化",
        "",
        _render_numeric_summary("角色预测融资额", size_changes),
        "",
        _render_numeric_summary("角色预测投后估值", post_money_changes),
        "",
        _render_numeric_summary("角色预测投资人持股", ownership_changes),
        "",
        _render_numeric_summary("角色满意度", satisfaction_changes),
        "",
        "## 最终提案变化",
        "",
        _render_counter_table(
            "提案分类字段变化",
            Counter(change.field for change in proposal_field_changes),
            ["field", "changes"],
        ),
        "",
        _render_numeric_summary("提案数值字段变化", proposal_numeric_changes),
        "",
        "## 分轮变化",
        "",
        _render_round_table(analysis["round_field_changes"], analysis["round_numeric_changes"]),
        "",
        "## 变化最多的案例",
        "",
        _render_top_cases(case_summaries, top_cases),
    ]
    return "\n".join(line for line in lines if line is not None)


def write_case_csv(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """Write case-level debate summaries to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_CSV_FIELDS, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _initial_role_decisions(case: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    decisions: Dict[str, Dict[str, Any]] = {}
    for event in case.get("trace", []):
        if event.get("stage") == "private_assessment":
            actor = str(event.get("actor", ""))
            payload = event.get("payload", {})
            if actor and isinstance(payload, dict):
                decisions[actor] = payload
    return decisions


def _final_role_decisions(case: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    role_decisions = case.get("role_decisions", {})
    return role_decisions if isinstance(role_decisions, dict) else {}


def _initial_proposal(case: Dict[str, Any]) -> Dict[str, Any]:
    for event in case.get("trace", []):
        if event.get("stage") == "initial_proposal" and isinstance(event.get("payload"), dict):
            return event["payload"]
    return {}


def _final_proposal(case: Dict[str, Any]) -> Dict[str, Any]:
    proposal = case.get("proposal", {})
    return proposal if isinstance(proposal, dict) else {}


def _round_level_changes(case: Dict[str, Any], initial_decisions: Dict[str, Dict[str, Any]]) -> List[FieldChange | NumericChange]:
    changes: List[FieldChange | NumericChange] = []
    previous_by_role = {role: dict(decision) for role, decision in initial_decisions.items()}
    for event in case.get("trace", []):
        stage = str(event.get("stage", ""))
        if not stage.startswith("bargaining_round_"):
            continue
        actor = str(event.get("actor", ""))
        payload = event.get("payload", {}) if isinstance(event.get("payload", {}), dict) else {}
        updated = payload.get("updated_decision", {})
        if not actor or not isinstance(updated, dict):
            continue
        before = previous_by_role.get(actor, {})
        for field in ROLE_FIELDS:
            if _normalized(before.get(field)) != _normalized(updated.get(field)):
                changes.append(FieldChange(str(case.get("case_id", "")), actor, field, before.get(field), updated.get(field), stage))
        for field in NUMERIC_ROLE_FIELDS:
            before_value = _optional_float(before.get(field))
            after_value = _optional_float(updated.get(field))
            if _numeric_changed(before_value, after_value):
                changes.append(
                    NumericChange(
                        case_id=str(case.get("case_id", "")),
                        role=actor,
                        field=field,
                        before=before_value,
                        after=after_value,
                        delta=_delta(before_value, after_value),
                        round_label=stage,
                    )
                )
        previous_by_role[actor] = updated
    return changes


def _render_counter_table(title: str, counter: Counter[Any], headers: Sequence[str]) -> str:
    if not counter:
        return f"### {title}\n\n无变化。"
    lines = [f"### {title}", "", f"| {headers[0]} | {headers[1]} |", "| --- | ---: |"]
    for key, count in counter.most_common():
        lines.append(f"| {key} | {count} |")
    return "\n".join(lines)


def _render_transition_table(title: str, changes: Sequence[FieldChange]) -> str:
    if not changes:
        return f"### {title}\n\n无分类字段变化。"
    counter = Counter((item.field, _display(item.before), _display(item.after)) for item in changes)
    lines = ["### " + title, "", "| field | before | after | count |", "| --- | --- | --- | ---: |"]
    for (field, before, after), count in counter.most_common(25):
        lines.append(f"| {field} | {before} | {after} | {count} |")
    return "\n".join(lines)


def _render_numeric_summary(title: str, changes: Sequence[NumericChange]) -> str:
    if not changes:
        return f"### {title}\n\n无数值字段变化。"
    by_field: Dict[str, List[NumericChange]] = defaultdict(list)
    for change in changes:
        by_field[change.field].append(change)
    lines = [
        "### " + title,
        "",
        "| field | changes | increased | decreased | mean delta | median abs delta | max abs delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for field, items in sorted(by_field.items()):
        deltas = [item.delta for item in items if item.delta is not None]
        increased = sum(1 for value in deltas if value > 0)
        decreased = sum(1 for value in deltas if value < 0)
        abs_deltas = [abs(value) for value in deltas]
        lines.append(
            f"| {field} | {len(items)} | {increased} | {decreased} | "
            f"{_fmt(mean(deltas) if deltas else None)} | {_fmt(median(abs_deltas) if abs_deltas else None)} | "
            f"{_fmt(max(abs_deltas) if abs_deltas else None)} |"
        )
    return "\n".join(lines)


def _render_round_table(
    field_changes: Counter[Tuple[str, str]],
    numeric_changes: Counter[Tuple[str, str]],
) -> str:
    if not field_changes and not numeric_changes:
        return "未发现分轮变化。"
    all_rounds = sorted({round_label for round_label, _ in field_changes} | {round_label for round_label, _ in numeric_changes})
    all_fields = sorted({field for _, field in field_changes} | {field for _, field in numeric_changes})
    lines = ["| round | field | changes |", "| --- | --- | ---: |"]
    for round_label in all_rounds:
        for field in all_fields:
            count = field_changes.get((round_label, field), 0) + numeric_changes.get((round_label, field), 0)
            if count:
                lines.append(f"| {round_label} | {field} | {count} |")
    return "\n".join(lines)


def _render_top_cases(rows: Sequence[Dict[str, Any]], top_cases: int) -> str:
    ranked = sorted(
        rows,
        key=lambda row: (
            int(row.get("role_field_changes") or 0)
            + int(row.get("role_size_changes") or 0)
            + int(row.get("role_satisfaction_changes") or 0)
            + int(row.get("proposal_field_changes") or 0),
            abs(float(row.get("proposal_size_delta") or 0)),
        ),
        reverse=True,
    )[:top_cases]
    if not ranked:
        return "No cases available."
    lines = [
        "| case_id | role categorical | role size | role satisfaction | proposal categorical | proposal size delta | final type / true | final size / true |",
        "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in ranked:
        final_type = f"{_display(row.get('final_deal_type'))} / {_display(row.get('true_deal_type'))}"
        final_size = f"{_fmt(row.get('final_deal_size_usd_m'))} / {_fmt(row.get('true_deal_size_usd_m'))}"
        lines.append(
            f"| {row.get('case_id')} | {row.get('role_field_changes')} | {row.get('role_size_changes')} | "
            f"{row.get('role_satisfaction_changes')} | {row.get('proposal_field_changes')} | "
            f"{_fmt(row.get('proposal_size_delta'))} | {final_type} | {final_size} |"
        )
    return "\n".join(lines)


def _normalized(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    return " ".join(str(value).strip().lower().split())


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _numeric_changed(before: Optional[float], after: Optional[float], tolerance: float = 1e-9) -> bool:
    if before is None and after is None:
        return False
    if before is None or after is None:
        return True
    return abs(before - after) > tolerance


def _delta(before: Optional[float], after: Optional[float]) -> Optional[float]:
    if before is None or after is None:
        return None
    return after - before


def _fmt(value: Any) -> str:
    number = _optional_float(value)
    if number is None:
        return "n/a"
    return f"{number:.3f}"


def _display(value: Any) -> str:
    if value is None or value == "":
        return "n/a"
    return str(value)


if __name__ == "__main__":
    main()
