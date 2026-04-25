"""LLM-backed board agents for the MVP simulation."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List

from boardroom_sim.llm import LLMClient
from boardroom_sim.models import (
    BoardCase,
    CeoReplacementView,
    FinancingVote,
    RoleDecision,
    RolePolicy,
    TermSheetProposal,
    ValuationDirection,
)


FINANCING_CHOICES = {"approve", "renegotiate", "reject"}
VALUATION_CHOICES = {"up", "flat", "down", "unknown"}
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
        """Ask the LLM to decide the three focal events from this role's perspective."""
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
        """Create a compact opening statement based on the role decision."""
        return (
            f"{self.role_name} starts with financing={decision.financing_vote}, "
            f"valuation={decision.valuation_direction}, "
            f"ceo={decision.ceo_replacement_view}. "
            f"Reason: {self.rationale_line(decision.rationale)}"
        )

    def bargaining_message(
        self,
        case: BoardCase,
        decision: RoleDecision,
        proposal: TermSheetProposal,
        round_index: int,
        context: Dict[str, RoleDecision],
    ) -> str:
        """Ask the LLM to produce one concise bargaining message for this role."""
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
                ),
            },
        ]
        raw = self.llm_client.complete_json(messages)
        message = str(raw.get("message", "")).strip()
        if message:
            return message
        return self.opening_statement(decision)

    def rationale_line(self, rationale: List[str]) -> str:
        """Join rationale fragments into one readable trace line."""
        if not rationale:
            return "No major rationale recorded."
        return " ".join(rationale)

    def _system_prompt(self) -> str:
        """Return the stable system prompt shared by all board agents."""
        return (
            "You are an LLM agent in a controlled social simulation of startup boardroom governance. "
            "You must strictly follow the assigned role policy. The experiment only studies three events: "
            "financing decision, valuation direction, and CEO replacement. Use only the visible fields, "
            "the role policy, and prior board context. Return valid JSON only."
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
        """Build the decision prompt for the three focal events."""
        context_payload = {
            role: {
                "financing_vote": decision.financing_vote,
                "valuation_direction": decision.valuation_direction,
                "ceo_replacement_view": decision.ceo_replacement_view,
                "rationale": decision.rationale,
            }
            for role, decision in context.items()
        }
        return f"""
You are now acting as role: {self.role_name}.

Strict four-layer role policy:
{self._role_policy_text()}

Visible case fields for this role only:
{json.dumps(observed_fields, ensure_ascii=False, indent=2)}

Minimal shared case metadata:
{json.dumps({
    "case_id": case.case_id,
    "company_name": case.company_name,
    "round_type": case.round_type,
    "market_temperature": case.market_temperature,
    "business_status": case.business_status,
}, ensure_ascii=False, indent=2)}

Prior board context from roles that have already spoken:
{json.dumps(context_payload, ensure_ascii=False, indent=2)}

Task:
Decide the three focal events from your role's perspective.

Allowed labels:
- financing_vote: approve, renegotiate, reject
- valuation_direction: up, flat, down, unknown
- ceo_replacement_view: keep, monitor, replace

Return one JSON object only with this schema:
{{
  "financing_vote": "approve|renegotiate|reject",
  "valuation_direction": "up|flat|down|unknown",
  "ceo_replacement_view": "keep|monitor|replace",
  "satisfaction_score": 0,
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
    ) -> str:
        """Build the prompt for one bargaining-round utterance."""
        context_payload = {
            role: {
                "financing_vote": item.financing_vote,
                "valuation_direction": item.valuation_direction,
                "ceo_replacement_view": item.ceo_replacement_view,
            }
            for role, item in context.items()
        }
        return f"""
You are now acting as role: {self.role_name}.

Strict four-layer role policy:
{self._role_policy_text()}

Visible case fields for this role only:
{json.dumps(self.observe(case), ensure_ascii=False, indent=2)}

Current proposal:
{json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2)}

Your current decision:
{json.dumps(decision.to_dict(), ensure_ascii=False, indent=2)}

Board context:
{json.dumps(context_payload, ensure_ascii=False, indent=2)}

Write one concise boardroom bargaining message for round {round_index + 1}. The message must:
- focus only on financing decision, valuation direction, or CEO replacement;
- reflect your role's L1 goals, L2 attention, L3 heuristics, and L4 protocol;
- avoid generic corporate slogans;
- be one to three sentences.

Return one JSON object only:
{{
  "message": "your boardroom message"
}}
"""

    def _decision_from_json(self, raw: Dict[str, Any], observed_fields: Dict[str, Any]) -> RoleDecision:
        """Convert a parsed LLM JSON object into a validated RoleDecision."""
        financing_vote = coerce_choice(raw.get("financing_vote"), FINANCING_CHOICES, "renegotiate")
        valuation_direction = coerce_choice(raw.get("valuation_direction"), VALUATION_CHOICES, "unknown")
        ceo_replacement_view = coerce_choice(raw.get("ceo_replacement_view"), CEO_CHOICES, "monitor")
        satisfaction_score = clamp_score(coerce_float(raw.get("satisfaction_score"), 50.0))
        rationale = coerce_rationale(raw.get("rationale"))

        return RoleDecision(
            role_name=self.role_name,
            financing_vote=financing_vote,  # type: ignore[arg-type]
            valuation_direction=valuation_direction,  # type: ignore[arg-type]
            ceo_replacement_view=ceo_replacement_view,  # type: ignore[arg-type]
            satisfaction_score=satisfaction_score,
            rationale=rationale,
            observed_fields=observed_fields,
        )


def build_agents(policies: Dict[str, RolePolicy], llm_client: LLMClient) -> Dict[str, BoardAgent]:
    """Instantiate all MVP agents from their role policies and shared LLM client."""
    return {role_name: BoardAgent(policy, llm_client) for role_name, policy in policies.items()}
