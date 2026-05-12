"""Single-agent baseline predictors for the boardroom simulation."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional

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
) -> List[Dict[str, Any]]:
    """Run a single-call baseline for each case."""
    rows: List[Dict[str, Any]] = []
    for case in cases:
        rows.append(predict_single_case(case, llm_client, include_role_rules=include_role_rules, baseline_name=baseline_name))
    return rows


def predict_single_case(
    case: BoardCase,
    llm_client: LLMClient,
    *,
    include_role_rules: bool,
    baseline_name: str,
) -> Dict[str, Any]:
    """Ask one LLM call to produce the same core prediction fields as the simulator."""
    raw = llm_client.complete_json(_baseline_messages(case, include_role_rules=include_role_rules))
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


def _baseline_messages(case: BoardCase, *, include_role_rules: bool) -> List[Dict[str, str]]:
    role_rules = (
        json.dumps(
            {name: policy.to_dict() for name, policy in build_role_policies().items()},
            ensure_ascii=False,
            indent=2,
        )
        if include_role_rules
        else "Not provided. Make a direct prediction from historical case fields only."
    )
    return [
        {
            "role": "system",
            "content": (
                "You are a single-agent baseline for a controlled startup financing backtest. "
                "Use only the provided historical point-in-time fields. Do not infer or reveal hidden labels. "
                "Return valid JSON only."
            ),
        },
        {
            "role": "user",
            "content": f"""
Historical point-in-time case fields:
{json.dumps(_historical_payload(case), ensure_ascii=False, indent=2)}

Role policy rules:
{role_rules}

Task:
Predict the financing outcome for this case. If role policy rules are provided, synthesize them in one single-agent judgment; do not simulate a debate.

Data handling rule:
- JSON null means missing or unobserved. Do not interpret null as zero.
- Do not use current target-deal labels; they are not included in the payload.
- predicted_post_money_valuation_usd_m is the expected post-money valuation in million USD.
- predicted_investor_ownership_pct is the expected investor ownership percentage after the financing, from 0 to 100.

Allowed labels:
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

Return one JSON object only with this schema:
{{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "rationale": ["short reason 1", "short reason 2"]
}}
""",
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
