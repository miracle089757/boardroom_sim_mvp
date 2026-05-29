"""Single-agent baseline predictors for the boardroom simulation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from boardroom_sim.agents import (
    COMPLETION_VIEWS,
    FINANCING_INTENTS,
    VALUATION_CHOICES,
    coerce_choice,
    coerce_float,
    coerce_rationale,
    coerce_text,
)
from boardroom_sim.llm import LLMClient
from boardroom_sim.models import BoardCase
from boardroom_sim.prompts import PromptRenderer
from boardroom_sim.roles import build_role_policies


HISTORICAL_BASELINE_FIELDS = [
    "case_id",
    "company_id",
    "company_label",
    "decision_date",
    "year_founded",
    "company_age_at_decision_years",
    "primary_industry",
    "industry_group",
    "industry_sector",
    "verticals",
    "keywords",
    "description",
    "prior_vc_deal_count",
    "prior_deal_date",
    "prior_deal_type",
    "prior_vc_round",
    "prior_deal_size_usd_m",
    "prior_pre_money_valuation_usd_m",
    "prior_post_money_valuation_usd_m",
    "prior_raised_to_date_usd_m",
    "prior_investor_ownership_pct",
    "months_since_prior_deal",
    "prior_valuation_markup_multiple",
    "prior_valuation_direction_label",
    "prior_investor_count",
    "prior_new_investor_count",
    "prior_followon_investor_count",
    "prior_lead_investor_count",
    "prior_lead_investor_types",
    "prior_lead_investor_amount_share",
    "prior_lead_preferred_deal_size_min_usd_m",
    "prior_lead_preferred_deal_size_max_usd_m",
    "prior_lead_preferred_company_valuation_min_usd_m",
    "prior_lead_preferred_company_valuation_max_usd_m",
    "prior_company_deal_history",
    "prior_lead_investor_deal_history",
    "prior_followon_investor_deal_history",
    "employee_count_at_decision",
    "previous_employee_count",
    "employee_growth_rate",
    "engineering_role_count",
    "executive_role_count",
    "founder_count",
    "current_ceo_count",
    "current_ceo_is_founder",
    "board_member_count",
    "investor_board_member_count",
    "competitor_count",
    "similar_company_count",
]


def run_single_agent_baseline(
    cases: Iterable[BoardCase],
    llm_client: LLMClient,
    *,
    include_role_rules: bool,
    baseline_name: str,
    role_policy_dir: Path | None = None,
    prompts_dir: Path | None = None,
) -> List[Dict[str, Any]]:
    """Run a single-call baseline for each case."""
    rows: List[Dict[str, Any]] = []
    for case in cases:
        rows.append(
            predict_single_case(
                case,
                llm_client,
                include_role_rules=include_role_rules,
                baseline_name=baseline_name,
                role_policy_dir=role_policy_dir,
                prompts_dir=prompts_dir,
            )
        )
    return rows


def predict_single_case(
    case: BoardCase,
    llm_client: LLMClient,
    *,
    include_role_rules: bool,
    baseline_name: str,
    role_policy_dir: Path | None = None,
    prompts_dir: Path | None = None,
) -> Dict[str, Any]:
    """Ask one LLM call to produce the same core prediction fields as the simulator."""
    raw = llm_client.complete_json(
        _baseline_messages(
            case,
            include_role_rules=include_role_rules,
            role_policy_dir=role_policy_dir,
            prompts_dir=prompts_dir,
        )
    )
    prediction = _coerce_prediction(raw)
    return {
        "case_id": case.case_id,
        "company_name": case.company_label,
        "baseline_name": baseline_name,
        "baseline_include_role_rules": include_role_rules,
        **prediction,
        "proposal": {
            "recommended_deal_size_usd_m": prediction["predicted_deal_size_usd_m"],
            "recommended_post_money_valuation_usd_m": prediction["predicted_post_money_valuation_usd_m"],
            "recommended_investor_ownership_pct": prediction["predicted_investor_ownership_pct"],
            "recommended_deal_type": prediction["predicted_deal_type"],
            "valuation_direction": prediction["valuation_direction"],
        },
        "rationale": coerce_rationale(raw.get("rationale")),
        "labels": case.notes.get("labels", {}) if isinstance(case.notes.get("labels", {}), dict) else {},
    }


def _baseline_messages(
    case: BoardCase,
    *,
    include_role_rules: bool,
    role_policy_dir: Path | None = None,
    prompts_dir: Path | None = None,
) -> List[Dict[str, str]]:
    role_rules = (
        json.dumps(
            {name: policy.to_dict() for name, policy in build_role_policies(policy_dir=role_policy_dir).items()},
            ensure_ascii=False,
            indent=2,
        )
        if include_role_rules
        else "未提供。请只根据历史时点字段做直接预测。"
    )
    renderer = PromptRenderer(prompts_dir=prompts_dir)
    return [
        {
            "role": "system",
            "content": renderer.render("baseline_system"),
        },
        {
            "role": "user",
            "content": renderer.render(
                "baseline_single_agent",
                historical_payload_json=json.dumps(_historical_payload(case), ensure_ascii=False, indent=2),
                role_rules_json=role_rules,
            ),
        },
    ]


def _historical_payload(case: BoardCase) -> Dict[str, Any]:
    case_dict = case.to_dict()
    return {field: case_dict.get(field) for field in HISTORICAL_BASELINE_FIELDS}


def _coerce_prediction(raw: Dict[str, Any]) -> Dict[str, Any]:
    financing_intent = coerce_choice(raw.get("financing_intent"), FINANCING_INTENTS, "raise_now")
    completion_view = coerce_choice(raw.get("completion_view"), COMPLETION_VIEWS, "likely_complete")
    return {
        "financing_initiation_decision": financing_intent,
        "financing_completion_view": completion_view,
        "predicted_deal_size_usd_m": round(max(0.0, coerce_float(raw.get("predicted_deal_size_usd_m"), 0.0)), 6),
        "predicted_post_money_valuation_usd_m": round(
            max(0.0, coerce_float(raw.get("predicted_post_money_valuation_usd_m"), 0.0)),
            6,
        ),
        "predicted_investor_ownership_pct": round(
            min(100.0, max(0.0, coerce_float(raw.get("predicted_investor_ownership_pct"), 0.0))),
            6,
        ),
        "predicted_deal_type": coerce_text(raw.get("predicted_deal_type"), "unknown"),
        "valuation_direction": coerce_choice(raw.get("valuation_direction"), VALUATION_CHOICES, "flat"),
        "consensus_score": None,
        "deal_break_risk": None,
    }
