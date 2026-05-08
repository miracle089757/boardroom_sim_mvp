"""LLM-backed board agents for the MVP simulation."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from boardroom_sim.llm import LLMClient
from boardroom_sim.models import (
    BoardCase,
    CeoReplacementView,
    DealCompletionView,
    FinancingIntent,
    RoleDecision,
    RolePolicy,
    TermSheetProposal,
    ValuationDirection,
)


FINANCING_INTENTS = {"raise_now", "wait", "avoid"}
COMPLETION_VIEWS = {"likely_complete", "unlikely_complete"}
VALUATION_CHOICES = {"up", "flat", "down"}
CEO_CHOICES = {"keep", "monitor", "replace"}


def clamp_score(value: float) -> float:
    """Clamp a satisfaction score to the inclusive range 0 to 100."""
    return max(0.0, min(100.0, value))


def coerce_choice(value: Any, allowed: Iterable[str], default: str) -> str:
    """Normalize an LLM string choice into one of the allowed labels."""
    if isinstance(value, str):
        normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
        if normalized in allowed:
            return normalized
    return default


def coerce_float(value: Any, default: float = 50.0) -> float:
    """Normalize an LLM numeric value into a float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def coerce_text(value: Any, default: str) -> str:
    """Normalize an LLM text field into a non-empty string."""
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def coerce_rationale(value: Any) -> List[str]:
    """Normalize LLM rationale into a short list of strings."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return ["LLM returned no explicit rationale."]


class BoardAgent:
    """One LLM-backed board agent governed by a strict four-layer role policy."""

    def __init__(self, policy: RolePolicy, llm_client: LLMClient) -> None:
        """Initialize an agent with its role policy and shared LLM client."""
        self.policy = policy
        self.role_name = policy.role_name
        self.llm_client = llm_client

    def observe(self, case: BoardCase) -> Dict[str, Any]:
        """Return only the fields this role is allowed to attend to."""
        case_dict = case.to_dict()
        return {field: case_dict.get(field) for field in self.policy.layer_2_attention_fields}

    def evaluate(self, case: BoardCase, context: Dict[str, RoleDecision]) -> RoleDecision:
        """Ask the LLM to predict financing outcomes from this role's perspective."""
        observed_fields = self.observe(case)
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": self._decision_prompt(
                    case=case,
                    observed_fields=observed_fields,
                    context=context,
                ),
            },
        ]
        raw = self.llm_client.complete_json(messages)
        return self._decision_from_json(raw, observed_fields)

    def opening_statement(self, decision: RoleDecision) -> str:
        """Create a compact opening statement based on the role prediction."""
        return (
            f"{self.role_name} starts with intent={decision.financing_intent}, "
            f"size={decision.predicted_deal_size_usd_m:.2f}M, "
            f"type={decision.predicted_deal_type}, "
            f"valuation={decision.valuation_direction}, ceo={decision.ceo_replacement_view}. "
            f"Reason: {self.rationale_line(decision.rationale)}"
        )

    def bargaining_step(
        self,
        case: BoardCase,
        decision: RoleDecision,
        proposal: TermSheetProposal,
        round_index: int,
        context: Dict[str, RoleDecision],
        prior_messages: List[Dict[str, Any]],
    ) -> Tuple[str, RoleDecision]:
        """Ask the LLM to produce one bargaining message and an updated prediction."""
        messages = [
            {"role": "system", "content": self._system_prompt()},
            {
                "role": "user",
                "content": self._bargaining_prompt(
                    case=case,
                    decision=decision,
                    proposal=proposal,
                    round_index=round_index,
                    context=context,
                    prior_messages=prior_messages,
                ),
            },
        ]
        raw = self.llm_client.complete_json(messages)
        message = str(raw.get("message", "")).strip() or self.opening_statement(decision)
        updated_decision = self._decision_from_json(raw, self.observe(case), fallback=decision)
        return message, updated_decision

    def rationale_line(self, rationale: List[str]) -> str:
        """Join rationale fragments into one readable trace line."""
        if not rationale:
            return "No major rationale recorded."
        return " ".join(rationale)

    def _system_prompt(self) -> str:
        """Return the stable system prompt shared by all board agents."""
        return (
            "You are an LLM agent in a controlled social simulation of startup boardroom governance. "
            "You must strictly follow the assigned four-layer role policy. This is a point-in-time "
            "positive-sample backtest: the current target transaction outcomes are hidden from you. "
            "Use only visible pre-decision fields, role policy, and prior board context. Return valid JSON only."
        )

    def _role_policy_text(self) -> str:
        """Format the four-layer role policy for an LLM prompt."""
        return json.dumps(self.policy.to_dict(), ensure_ascii=False, indent=2)

    def _decision_prompt(
        self,
        *,
        case: BoardCase,
        observed_fields: Dict[str, Any],
        context: Dict[str, RoleDecision],
    ) -> str:
        """Build the initial prediction prompt."""
        context_payload = {role: self._decision_payload(decision) for role, decision in context.items()}
        return f"""
You are now acting as role: {self.role_name}.

Strict four-layer role policy:
{self._role_policy_text()}

Visible pre-decision fields for this role only:
{json.dumps(observed_fields, ensure_ascii=False, indent=2)}

Minimal shared case metadata:
{json.dumps({
    "case_id": case.case_id,
    "company_label": case.company_label,
    "company_id": case.company_id,
    "decision_date": case.decision_date,
    "primary_industry": case.primary_industry,
}, ensure_ascii=False, indent=2)}

Data handling rule:
- JSON null means the value is missing or unobserved. Do not interpret null as zero.
- Treat PitchBook snapshot company status fields as unavailable unless they appear in your visible fields.

Prior board context from roles that have already spoken:
{json.dumps(context_payload, ensure_ascii=False, indent=2)}

Task:
Predict this role's point-in-time board stance. Do not assume or reveal current target-deal labels.

Hard consistency rules:
- If financing_intent is "raise_now", predicted_deal_size_usd_m must be greater than 0.
- If financing_intent is "wait" or "avoid", predicted_deal_size_usd_m may be 0.
- When financing_intent is "raise_now" and exact amount is not clear, estimate a plausible positive amount from visible prior_deal_size_usd_m, prior_raised_to_date_usd_m, prior_vc_round, company age, and role policy. Do not use hidden current-deal labels.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Do not copy numeric placeholders from the schema. Return values that are consistent with your own rationale.

Allowed labels:
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down
- ceo_replacement_view: keep, monitor, replace

Return one JSON object only with this schema:
{{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "ceo_replacement_view": "keep|monitor|replace",
  "satisfaction_score": 50,
  "rationale": ["short reason 1", "short reason 2"]
}}
"""

    def _bargaining_prompt(
        self,
        *,
        case: BoardCase,
        decision: RoleDecision,
        proposal: TermSheetProposal,
        round_index: int,
        context: Dict[str, RoleDecision],
        prior_messages: List[Dict[str, Any]],
    ) -> str:
        """Build the prompt for one bargaining-round utterance and decision update."""
        context_payload = {role: self._decision_payload(item) for role, item in context.items()}
        return f"""
You are now acting as role: {self.role_name}.

Strict four-layer role policy:
{self._role_policy_text()}

Visible pre-decision fields for this role only:
{json.dumps(self.observe(case), ensure_ascii=False, indent=2)}

Current aggregated proposal:
{json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2)}

Your current prediction:
{json.dumps(self._decision_payload(decision), ensure_ascii=False, indent=2)}

Board context:
{json.dumps(context_payload, ensure_ascii=False, indent=2)}

Prior bargaining messages:
{json.dumps(prior_messages, ensure_ascii=False, indent=2)}

Data handling rule:
- JSON null means the value is missing or unobserved. Do not interpret null as zero.
- Treat PitchBook snapshot company status fields as unavailable unless they appear in your visible fields.

Hard consistency rules:
- If financing_intent is "raise_now", predicted_deal_size_usd_m must be greater than 0.
- If financing_intent is "wait" or "avoid", predicted_deal_size_usd_m may be 0.
- When financing_intent is "raise_now" and exact amount is not clear, estimate a plausible positive amount from visible prior_deal_size_usd_m, prior_raised_to_date_usd_m, prior_vc_round, company age, current proposal, bargaining history, and role policy. Do not use hidden current-deal labels.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Do not copy numeric placeholders from the schema. Return values that are consistent with your updated rationale.

Write one concise boardroom bargaining message for round {round_index + 1}, then update your prediction if the discussion changes your stance.
The message must:
- focus on financing timing, financing amount, deal type, valuation direction, or CEO replacement;
- reflect your role's L1 goals, L2 attention, L3 heuristics, and L4 protocol;
- avoid generic corporate slogans;
- be one to three sentences.

Return one JSON object only:
{{
  "message": "your boardroom message",
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "ceo_replacement_view": "keep|monitor|replace",
  "satisfaction_score": 50,
  "rationale": ["short reason 1", "short reason 2"]
}}
"""

    def _decision_from_json(
        self,
        raw: Dict[str, Any],
        observed_fields: Dict[str, Any],
        fallback: Optional[RoleDecision] = None,
    ) -> RoleDecision:
        """Convert a parsed LLM JSON object into a validated RoleDecision."""
        financing_intent = coerce_choice(
            raw.get("financing_intent"),
            FINANCING_INTENTS,
            fallback.financing_intent if fallback else "raise_now",
        )
        completion_view = coerce_choice(
            raw.get("completion_view"),
            COMPLETION_VIEWS,
            fallback.completion_view if fallback and fallback.completion_view in COMPLETION_VIEWS else "likely_complete",
        )
        predicted_deal_size = max(
            0.0,
            coerce_float(
                raw.get("predicted_deal_size_usd_m"),
                fallback.predicted_deal_size_usd_m if fallback else 0.0,
            ),
        )
        predicted_deal_type = coerce_text(
            raw.get("predicted_deal_type"),
            fallback.predicted_deal_type if fallback else "unknown",
        )
        valuation_direction = coerce_choice(
            raw.get("valuation_direction"),
            VALUATION_CHOICES,
            fallback.valuation_direction if fallback and fallback.valuation_direction in VALUATION_CHOICES else "flat",
        )
        ceo_replacement_view = coerce_choice(
            raw.get("ceo_replacement_view"),
            CEO_CHOICES,
            fallback.ceo_replacement_view if fallback else "monitor",
        )
        satisfaction_score = clamp_score(
            coerce_float(raw.get("satisfaction_score"), fallback.satisfaction_score if fallback else 50.0)
        )
        rationale = coerce_rationale(raw.get("rationale")) if "rationale" in raw else (fallback.rationale if fallback else [])

        return RoleDecision(
            role_name=self.role_name,
            financing_intent=financing_intent,  # type: ignore[arg-type]
            completion_view=completion_view,  # type: ignore[arg-type]
            predicted_deal_size_usd_m=round(predicted_deal_size, 6),
            predicted_deal_type=predicted_deal_type,
            valuation_direction=valuation_direction,  # type: ignore[arg-type]
            ceo_replacement_view=ceo_replacement_view,  # type: ignore[arg-type]
            satisfaction_score=satisfaction_score,
            rationale=rationale or ["LLM returned no explicit rationale."],
            observed_fields=observed_fields,
        )

    def _decision_payload(self, decision: RoleDecision) -> Dict[str, Any]:
        """Return a compact decision payload for prompts."""
        return {
            "financing_intent": decision.financing_intent,
            "completion_view": decision.completion_view,
            "predicted_deal_size_usd_m": decision.predicted_deal_size_usd_m,
            "predicted_deal_type": decision.predicted_deal_type,
            "valuation_direction": decision.valuation_direction,
            "ceo_replacement_view": decision.ceo_replacement_view,
            "satisfaction_score": decision.satisfaction_score,
            "rationale": decision.rationale,
        }


def build_agents(policies: Dict[str, RolePolicy], llm_client: LLMClient) -> Dict[str, BoardAgent]:
    """Instantiate all MVP agents from their role policies and shared LLM client."""
    return {role_name: BoardAgent(policy, llm_client) for role_name, policy in policies.items()}
