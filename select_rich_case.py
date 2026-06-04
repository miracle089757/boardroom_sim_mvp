"""Select a rich single case for repeatable boardroom simulation smoke tests."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

from boardroom_sim.config import ExperimentConfig, load_experiment_config
from boardroom_sim.io import write_cases_jsonl
from boardroom_sim.models import BoardCase
from boardroom_sim.pitchbook import build_cases_from_pitchbook
from boardroom_sim.roles import build_role_policies


DEFAULT_INPUT = Path("input/260524_02_03_pitchbook_sample_100_shared.xlsx")
DEFAULT_OUTPUT = Path("input/selected_rich_case.jsonl")
DEFAULT_REPORT = Path("input/selected_rich_case_profile.md")
DEFAULT_CONFIG = Path("configs/boardroom_default.toml")

MISSING_STRINGS = {
    "",
    "unknown",
    "unknown_company",
    "unknown_deal",
    "unknown_industry",
    "unknown_prior_deal_type",
    "unknown_prior_vc_round",
    "none",
    "nan",
    "nat",
}

COUNT_FIELDS = {
    "prior_vc_deal_count",
    "prior_investor_count",
    "prior_new_investor_count",
    "prior_followon_investor_count",
    "prior_lead_investor_count",
    "engineering_role_count",
    "executive_role_count",
    "founder_count",
    "current_ceo_count",
    "board_member_count",
    "investor_board_member_count",
    "competitor_count",
    "similar_company_count",
}

CATEGORY_WEIGHTS = {
    "公司基础信息": 0.16,
    "历史融资信息": 0.24,
    "投资人上下文": 0.20,
    "Revelio/治理画像": 0.20,
    "市场/竞争信息": 0.06,
    "真实标签": 0.14,
}

CATEGORY_FIELDS: Dict[str, List[Tuple[str, float]]] = {
    "公司基础信息": [
        ("company_label", 0.6),
        ("decision_date", 0.8),
        ("business_status", 0.8),
        ("company_financing_status", 0.8),
        ("ownership_status", 0.6),
        ("year_founded", 0.8),
        ("company_age_at_decision_years", 1.0),
        ("primary_industry", 1.0),
        ("industry_group", 0.8),
        ("industry_sector", 0.8),
        ("verticals", 1.0),
        ("keywords", 1.5),
        ("description", 2.0),
    ],
    "历史融资信息": [
        ("prior_vc_deal_count", 1.5),
        ("prior_deal_date", 1.0),
        ("prior_deal_type", 1.0),
        ("prior_vc_round", 1.0),
        ("prior_deal_size_usd_m", 2.0),
        ("prior_pre_money_valuation_usd_m", 2.0),
        ("prior_post_money_valuation_usd_m", 2.0),
        ("prior_raised_to_date_usd_m", 1.0),
        ("prior_investor_ownership_pct", 1.5),
        ("months_since_prior_deal", 1.0),
        ("prior_valuation_markup_multiple", 1.2),
        ("prior_valuation_direction_label", 1.0),
        ("prior_company_deal_history", 2.5),
    ],
    "投资人上下文": [
        ("prior_investor_count", 1.0),
        ("prior_new_investor_count", 1.0),
        ("prior_followon_investor_count", 1.0),
        ("prior_lead_investor_count", 1.0),
        ("prior_lead_investor_types", 1.0),
        ("prior_lead_investor_amount_share", 1.0),
        ("prior_lead_preferred_deal_size_min_usd_m", 1.0),
        ("prior_lead_preferred_deal_size_max_usd_m", 1.0),
        ("prior_lead_preferred_company_valuation_min_usd_m", 1.0),
        ("prior_lead_preferred_company_valuation_max_usd_m", 1.0),
        ("prior_lead_investor_deal_history", 2.5),
        ("prior_followon_investor_deal_history", 2.0),
    ],
    "Revelio/治理画像": [
        ("employee_count_at_decision", 1.4),
        ("previous_employee_count", 1.0),
        ("employee_growth_rate", 1.4),
        ("engineering_role_count", 1.0),
        ("executive_role_count", 1.0),
        ("founder_count", 1.0),
        ("current_ceo_count", 1.0),
        ("current_ceo_is_founder", 0.8),
        ("board_member_count", 1.5),
        ("investor_board_member_count", 1.5),
    ],
    "市场/竞争信息": [
        ("competitor_count", 1.0),
        ("similar_company_count", 1.0),
        ("verticals", 0.5),
        ("keywords", 0.5),
    ],
    "真实标签": [
        ("labels.true_financing_initiated_label", 1.0),
        ("labels.real_deal_completed_label", 1.0),
        ("labels.real_deal_size_usd_m", 1.5),
        ("labels.real_deal_type", 1.0),
        ("labels.real_pre_money_valuation_usd_m", 1.2),
        ("labels.real_post_money_valuation_usd_m", 1.5),
        ("labels.real_investor_ownership_pct", 1.2),
        ("labels.real_valuation_direction_label", 1.0),
    ],
}

KEY_SNAPSHOT_FIELDS = [
    "case_id",
    "company_id",
    "target_deal_id",
    "company_label",
    "decision_date",
    "primary_industry",
    "industry_group",
    "industry_sector",
    "verticals",
    "keywords",
    "description",
    "prior_vc_deal_count",
    "prior_deal_date",
    "prior_vc_round",
    "prior_deal_size_usd_m",
    "prior_pre_money_valuation_usd_m",
    "prior_post_money_valuation_usd_m",
    "prior_investor_ownership_pct",
    "employee_count_at_decision",
    "employee_growth_rate",
    "engineering_role_count",
    "executive_role_count",
    "founder_count",
    "current_ceo_count",
    "board_member_count",
    "investor_board_member_count",
    "competitor_count",
    "similar_company_count",
]


@dataclass
class CaseScore:
    case: BoardCase
    overall_score: float
    category_scores: Dict[str, float]
    category_present: Dict[str, int]
    category_total: Dict[str, int]
    eligibility_checks: Dict[str, bool]

    @property
    def eligibility_count(self) -> int:
        return sum(1 for value in self.eligibility_checks.values() if value)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Select the richest BoardCase for repeated one-case smoke tests.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT, help="Path to PitchBook/Revelio XLSX workbook.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSONL path for the selected case.")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT, help="Markdown report explaining the selection.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="Experiment config used for role visibility.")
    parser.add_argument(
        "--history-limit",
        type=int,
        default=None,
        help="History limit passed to build_cases_from_pitchbook. Defaults to config history_limit.",
    )
    parser.add_argument("--top-k", type=int, default=10, help="Number of ranked candidates to include in the report.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = load_experiment_config(args.config)
    history_limit = args.history_limit if args.history_limit is not None else config.history_limit
    cases = build_cases_from_pitchbook(args.input, history_limit=history_limit)
    if not cases:
        raise ValueError(f"No cases could be built from {args.input}.")

    scored = sorted((score_case(case) for case in cases), key=score_sort_key, reverse=True)
    selected = scored[0]
    write_cases_jsonl(args.output, [selected.case])
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(render_report(selected, scored[: args.top_k], args, config), encoding="utf-8")

    print(f"Selected case_id={selected.case.case_id}")
    print(f"Overall score={selected.overall_score:.3f}")
    print(f"Wrote {safe_console_path(args.output)}")
    print(f"Wrote {safe_console_path(args.report)}")


def score_case(case: BoardCase) -> CaseScore:
    case_dict = case.to_dict()
    category_scores: Dict[str, float] = {}
    category_present: Dict[str, int] = {}
    category_total: Dict[str, int] = {}

    for category, fields in CATEGORY_FIELDS.items():
        total_weight = sum(weight for _, weight in fields)
        weighted_present = 0.0
        present_count = 0
        for field_name, weight in fields:
            value = get_field_value(case_dict, field_name)
            field_score = presence_score(value, field_name, case_dict)
            weighted_present += weight * field_score
            if field_score > 0:
                present_count += 1
        category_scores[category] = weighted_present / total_weight if total_weight else 0.0
        category_present[category] = present_count
        category_total[category] = len(fields)

    overall = sum(CATEGORY_WEIGHTS[name] * category_scores[name] for name in CATEGORY_WEIGHTS)
    eligibility_checks = {
        "有业务描述或关键词": bool(
            presence_score(case.description, "description", case_dict)
            or presence_score(case.keywords, "keywords", case_dict)
        ),
        "有历史融资": bool(
            case.prior_vc_deal_count > 0
            or presence_score(case.prior_company_deal_history, "prior_company_deal_history", case_dict)
        ),
        "有投资人上下文": category_scores["投资人上下文"] >= 0.25,
        "有 Revelio/治理画像": category_scores["Revelio/治理画像"] >= 0.25,
        "有主要真实标签": category_scores["真实标签"] >= 0.40,
    }

    return CaseScore(
        case=case,
        overall_score=overall,
        category_scores=category_scores,
        category_present=category_present,
        category_total=category_total,
        eligibility_checks=eligibility_checks,
    )


def score_sort_key(score: CaseScore) -> Tuple[int, float, float, float, str]:
    front_information = (
        score.category_scores["公司基础信息"]
        + score.category_scores["历史融资信息"]
        + score.category_scores["投资人上下文"]
        + score.category_scores["Revelio/治理画像"]
    ) / 4
    return (
        score.eligibility_count,
        score.overall_score,
        front_information,
        score.category_scores["真实标签"],
        score.case.case_id,
    )


def get_field_value(case_dict: Dict[str, Any], field_name: str) -> Any:
    if field_name.startswith("labels."):
        labels = case_dict.get("notes", {}).get("labels", {})
        if isinstance(labels, dict):
            return labels.get(field_name.split(".", 1)[1])
        return None
    return case_dict.get(field_name)


def presence_score(value: Any, field_name: str, case_dict: Dict[str, Any]) -> float:
    if value is None:
        return 0.0
    if isinstance(value, bool):
        if field_name == "current_ceo_is_founder":
            return 1.0 if numeric_value(case_dict.get("current_ceo_count")) > 0 else 0.0
        return 1.0
    if isinstance(value, str):
        normalized = value.strip().lower()
        return 0.0 if normalized in MISSING_STRINGS else 1.0
    if isinstance(value, (list, tuple, set)):
        clean_items = [item for item in value if presence_score(item, field_name, case_dict) > 0]
        if not clean_items:
            return 0.0
        if field_name.endswith("_history"):
            return min(1.0, len(clean_items) / 3.0)
        return min(1.0, len(clean_items) / 2.0)
    if isinstance(value, dict):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return 0.0
        if field_name in COUNT_FIELDS:
            return 1.0 if value > 0 else 0.0
        return 1.0
    return 1.0 if str(value).strip() else 0.0


def numeric_value(value: Any) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return 0.0
    return result if math.isfinite(result) else 0.0


def render_report(selected: CaseScore, top_scores: List[CaseScore], args: argparse.Namespace, config: ExperimentConfig) -> str:
    policies = build_role_policies(config.role_policy_dir, config.role_order)
    case = selected.case
    case_dict = case.to_dict()
    lines = [
        "# 最完整单案例选择报告",
        "",
        "## 选择结果",
        "",
        markdown_table(
            ["项目", "值"],
            [
                ["输入文件", str(args.input)],
                ["输出 JSONL", str(args.output)],
                ["case_id", case.case_id],
                ["company_id", case.company_id],
                ["target_deal_id", case.target_deal_id],
                ["公司标签", case.company_label],
                ["行业", case.primary_industry],
                ["决策日期", case.decision_date],
                ["总分", f"{selected.overall_score:.3f}"],
                ["通过关键筛选数", f"{selected.eligibility_count}/{len(selected.eligibility_checks)}"],
            ],
        ),
        "",
        "## 为什么选择这个 case",
        "",
        "- 它优先满足用于观察董事会行为的关键条件：业务信息、历史融资、投资人上下文、Revelio/治理画像和真实标签。",
        "- 输出的 JSONL 只包含这一行 case，可作为后续每次修改实验后的固定 smoke test 输入。",
        "- 真实标签保存在 `notes.labels`，仅用于事后评估，不会进入角色可见字段。",
        "",
        "## 关键筛选条件",
        "",
        markdown_table(["条件", "是否满足"], [[name, yes_no(value)] for name, value in selected.eligibility_checks.items()]),
        "",
        "## 分类完整度得分",
        "",
        markdown_table(
            ["类别", "得分", "非空字段数"],
            [
                [
                    category,
                    f"{selected.category_scores[category]:.3f}",
                    f"{selected.category_present[category]}/{selected.category_total[category]}",
                ]
                for category in CATEGORY_WEIGHTS
            ],
        ),
        "",
        "## 关键信息快照",
        "",
        markdown_table(
            ["字段", "值"],
            [[field, render_value(get_field_value(case_dict, field))] for field in KEY_SNAPSHOT_FIELDS],
        ),
        "",
        "## 真实标签快照",
        "",
        render_labels(case_dict),
        "",
        "## Top 候选案例",
        "",
        markdown_table(
            ["排名", "case_id", "公司", "行业", "总分", "关键条件", "基础", "历史", "投资人", "Revelio/治理", "标签"],
            [
                [
                    index,
                    score.case.case_id,
                    score.case.company_label,
                    score.case.primary_industry,
                    f"{score.overall_score:.3f}",
                    f"{score.eligibility_count}/{len(score.eligibility_checks)}",
                    f"{score.category_scores['公司基础信息']:.2f}",
                    f"{score.category_scores['历史融资信息']:.2f}",
                    f"{score.category_scores['投资人上下文']:.2f}",
                    f"{score.category_scores['Revelio/治理画像']:.2f}",
                    f"{score.category_scores['真实标签']:.2f}",
                ]
                for index, score in enumerate(top_scores, start=1)
            ],
        ),
        "",
        "## 角色可见字段覆盖",
        "",
    ]

    for role_name in config.role_order:
        policy = policies.get(role_name)
        if policy is None:
            continue
        visible_rows = []
        present_count = 0
        for field_name in policy.layer_2_attention_fields:
            value = case_dict.get(field_name)
            present = presence_score(value, field_name, case_dict) > 0
            present_count += int(present)
            visible_rows.append([field_name, yes_no(present), render_value(value)])
        lines.extend(
            [
                f"### {role_name}",
                "",
                f"可见字段覆盖：{present_count}/{len(policy.layer_2_attention_fields)}",
                "",
                markdown_table(["字段", "是否非空", "值"], visible_rows),
                "",
            ]
        )

    lines.extend(
        [
            "## 固定单案例运行命令",
            "",
            "```bash",
            "python run_experiment.py \\",
            f"  --input {args.output.as_posix()} \\",
            "  --output outputs/one_case/results.jsonl \\",
            "  --trace-output outputs/one_case/traces.json \\",
            "  --readable-output outputs/one_case/boardroom_trace.md \\",
            f"  --config {args.config.as_posix()} \\",
            "  --case-limit 1",
            "```",
            "",
        ]
    )
    return "\n".join(lines)


def render_labels(case_dict: Dict[str, Any]) -> str:
    labels = case_dict.get("notes", {}).get("labels", {})
    if not isinstance(labels, dict) or not labels:
        return "该 case 未包含 `notes.labels`。"
    return markdown_table(["标签字段", "值"], [[key, render_value(value)] for key, value in sorted(labels.items())])


def markdown_table(headers: Iterable[Any], rows: Iterable[Iterable[Any]]) -> str:
    header_list = [table_cell(header) for header in headers]
    lines = [
        "| " + " | ".join(header_list) + " |",
        "| " + " | ".join("---" for _ in header_list) + " |",
    ]
    for row in rows:
        row_values = [table_cell(value) for value in row]
        padded = row_values + [""] * (len(header_list) - len(row_values))
        lines.append("| " + " | ".join(padded[: len(header_list)]) + " |")
    return "\n".join(lines)


def table_cell(value: Any) -> str:
    return render_value(value).replace("\n", " ").replace("|", "\\|")


def render_value(value: Any, limit: int = 220) -> str:
    if value is None:
        return "未记录"
    if isinstance(value, float):
        if not math.isfinite(value):
            return "未记录"
        return f"{value:.6g}"
    if isinstance(value, (dict, list, tuple)):
        text = json.dumps(value, ensure_ascii=False, separators=(",", ": "))
    elif isinstance(value, bool):
        text = "是" if value else "否"
    else:
        text = str(value).strip()
    if not text:
        return "未记录"
    return text if len(text) <= limit else text[: limit - 1] + "…"


def yes_no(value: bool) -> str:
    return "是" if value else "否"


def safe_console_path(path: Path) -> str:
    return str(path).encode("gbk", errors="backslashreplace").decode("gbk")


if __name__ == "__main__":
    main()
