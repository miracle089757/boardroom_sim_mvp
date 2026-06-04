"""LLM-backed board agents for the MVP simulation."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

from boardroom_sim.config import DEFAULT_ROUND_TASKS
from boardroom_sim.llm import LLMClient
from boardroom_sim.models import (
    BoardCase,
    DealCompletionView,
    FinancingIntent,
    RoleDecision,
    RolePolicy,
    TermSheetProposal,
    ValuationDirection,
)
from boardroom_sim.prompts import PromptRenderer


FINANCING_INTENTS = {"raise_now", "wait", "avoid"}
COMPLETION_VIEWS = {"likely_complete", "unlikely_complete"}
VALUATION_CHOICES = {"up", "flat", "down"}


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


def coerce_string_list(value: Any) -> List[str]:
    """Normalize an optional LLM list field into a list of strings."""
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


class BoardAgent:
    """One LLM-backed board agent governed by a strict four-layer role policy."""

    def __init__(
        self,
        policy: RolePolicy,
        llm_client: LLMClient,
        prompt_renderer: Optional[PromptRenderer] = None,
    ) -> None:
        """Initialize an agent with its role policy and shared LLM client."""
        self.policy = policy
        self.role_name = policy.role_name
        self.llm_client = llm_client
        self.prompt_renderer = prompt_renderer or PromptRenderer()

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
            f"post-money={decision.predicted_post_money_valuation_usd_m:.2f}M, "
            f"ownership={decision.predicted_investor_ownership_pct:.2f}%, "
            f"type={decision.predicted_deal_type}, "
            f"valuation={decision.valuation_direction}. "
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
        process_context: Dict[str, Any] | None = None,
    ) -> Tuple[str, RoleDecision, Dict[str, Any]]:
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
                    process_context=process_context or {},
                ),
            },
        ]
        raw = self.llm_client.complete_json(messages)
        message = str(raw.get("message") or raw.get("speech") or "").strip() or self.opening_statement(decision)
        updated_decision = self._decision_from_json(raw, self.observe(case), fallback=decision)
        return message, updated_decision, self._meeting_artifacts_from_json(raw)

    def rationale_line(self, rationale: List[str]) -> str:
        """Join rationale fragments into one readable trace line."""
        if not rationale:
            return "No major rationale recorded."
        return " ".join(rationale)

    def _system_prompt(self) -> str:
        """Return the stable system prompt shared by all board agents."""
        return self.prompt_renderer.render(
            "system_agent",
            role_name=self.role_name,
            role_policy_json=self._role_policy_text(),
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
        case_metadata = {
            "case_id": case.case_id,
            "company_label": case.company_label,
            "company_id": case.company_id,
            "decision_date": case.decision_date,
            "primary_industry": case.primary_industry,
        }
        return self.prompt_renderer.render(
            "initial_prediction",
            role_name=self.role_name,
            role_policy_json=self._role_policy_text(),
            observed_fields_json=json.dumps(observed_fields, ensure_ascii=False, indent=2),
            case_metadata_json=json.dumps(case_metadata, ensure_ascii=False, indent=2),
            context_payload_json=json.dumps(context_payload, ensure_ascii=False, indent=2),
        )

    def _bargaining_prompt(
        self,
        *,
        case: BoardCase,
        decision: RoleDecision,
        proposal: TermSheetProposal,
        round_index: int,
        context: Dict[str, RoleDecision],
        prior_messages: List[Dict[str, Any]],
        process_context: Dict[str, Any],
    ) -> str:
        """Build the prompt for one bargaining-round utterance and decision update."""
        context_payload = {role: self._decision_payload(item) for role, item in context.items()}
        round_tasks = self.prompt_renderer.round_tasks or list(DEFAULT_ROUND_TASKS)
        round_specific_task = round_tasks[min(round_index, len(round_tasks) - 1)]
        return self.prompt_renderer.render(
            "bargaining_step",
            role_name=self.role_name,
            role_policy_json=self._role_policy_text(),
            observed_fields_json=json.dumps(self.observe(case), ensure_ascii=False, indent=2),
            proposal_json=json.dumps(proposal.to_dict(), ensure_ascii=False, indent=2),
            current_decision_json=json.dumps(self._decision_payload(decision), ensure_ascii=False, indent=2),
            context_payload_json=json.dumps(context_payload, ensure_ascii=False, indent=2),
            prior_messages_json=json.dumps(prior_messages, ensure_ascii=False, indent=2),
            process_context_json=json.dumps(process_context, ensure_ascii=False, indent=2),
            round_index=round_index + 1,
            round_specific_task=round_specific_task,
            response_guidance=self.prompt_renderer.response_guidance(),
        )

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
        predicted_post_money_valuation = max(
            0.0,
            coerce_float(
                raw.get("predicted_post_money_valuation_usd_m"),
                fallback.predicted_post_money_valuation_usd_m if fallback else 0.0,
            ),
        )
        predicted_investor_ownership = min(
            100.0,
            max(
                0.0,
                coerce_float(
                    raw.get("predicted_investor_ownership_pct"),
                    fallback.predicted_investor_ownership_pct if fallback else 0.0,
                ),
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
        satisfaction_score = clamp_score(
            coerce_float(raw.get("satisfaction_score"), fallback.satisfaction_score if fallback else 50.0)
        )
        rationale = coerce_rationale(raw.get("rationale")) if "rationale" in raw else (fallback.rationale if fallback else [])

        return RoleDecision(
            role_name=self.role_name,
            financing_intent=financing_intent,  # type: ignore[arg-type]
            completion_view=completion_view,  # type: ignore[arg-type]
            predicted_deal_size_usd_m=round(predicted_deal_size, 6),
            predicted_post_money_valuation_usd_m=round(predicted_post_money_valuation, 6),
            predicted_investor_ownership_pct=round(predicted_investor_ownership, 6),
            predicted_deal_type=predicted_deal_type,
            valuation_direction=valuation_direction,  # type: ignore[arg-type]
            satisfaction_score=satisfaction_score,
            rationale=rationale or ["LLM returned no explicit rationale."],
            observed_fields=observed_fields,
        )

    def _meeting_artifacts_from_json(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Extract richer boardroom-process fields from a bargaining response."""
        return {
            "boardroom_act": coerce_text(raw.get("boardroom_act"), "unspecified"),
            "direct_response_to": coerce_text(raw.get("direct_response_to"), ""),
            "questions_raised": coerce_string_list(raw.get("questions_raised")),
            "evidence_anchors": coerce_string_list(raw.get("evidence_anchors")),
            "alternative_options": coerce_string_list(raw.get("alternative_options")),
            "role_commitment": coerce_text(raw.get("role_commitment"), ""),
            "prediction_update_reason": coerce_text(raw.get("prediction_update_reason"), ""),
        }

    def _decision_payload(self, decision: RoleDecision) -> Dict[str, Any]:
        """Return a compact decision payload for prompts."""
        return {
            "financing_intent": decision.financing_intent,
            "completion_view": decision.completion_view,
            "predicted_deal_size_usd_m": decision.predicted_deal_size_usd_m,
            "predicted_post_money_valuation_usd_m": decision.predicted_post_money_valuation_usd_m,
            "predicted_investor_ownership_pct": decision.predicted_investor_ownership_pct,
            "predicted_deal_type": decision.predicted_deal_type,
            "valuation_direction": decision.valuation_direction,
            "satisfaction_score": decision.satisfaction_score,
            "rationale": decision.rationale,
        }


def build_agents(
    policies: Dict[str, RolePolicy],
    llm_client: LLMClient,
    prompt_renderer: Optional[PromptRenderer] = None,
) -> Dict[str, BoardAgent]:
    """Instantiate all MVP agents from their role policies and shared LLM client."""
    return {role_name: BoardAgent(policy, llm_client, prompt_renderer) for role_name, policy in policies.items()}
