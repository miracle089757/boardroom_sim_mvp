"""LLM-backed board agents for the MVP simulation."""

from __future__ import annotations

import json
from typing import Any, Dict, Iterable, List, Optional, Tuple

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
            "Use only visible pre-decision fields, role policy, and prior board context. Your JSON prediction "
            "fields are role-informed forecasts of the likely realized next financing outcome, not the role's "
            "preferred negotiation demand. Return valid JSON only."
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

Context discipline:
- Prior board context is not factual evidence. Use it only to understand other role forecasts and disagreements.
- Your private assessment must be independently derived from your visible fields and role policy; do not copy another role's prediction unless your own evidence supports it.

Task:
Produce this role-informed point-in-time forecast of the likely realized next financing outcome.
Do not output your preferred negotiation demand as the prediction.
Use the role policy to decide which evidence to emphasize, but the output fields must remain a best forecast of the likely market transaction.
If your role preference differs from the likely outcome, explain that difference in rationale and satisfaction_score; keep the prediction as the likely outcome.
Do not assume or reveal current target-deal labels.

Hard consistency rules:
- If financing_intent is "raise_now", predicted_deal_size_usd_m must be greater than 0.
- If financing_intent is "wait" or "avoid", predicted_deal_size_usd_m may be 0.
- When financing_intent is "raise_now" and exact amount is not clear, estimate a plausible positive amount from visible historical trajectory, round progression, investor structure, company maturity, operating signals, and role policy. Do not use hidden current-deal labels.
- predicted_post_money_valuation_usd_m is the expected post-money valuation in million USD. Estimate it from visible valuation history, deal size, valuation direction, round stage, raised-to-date, company maturity, and role policy; use 0 only when no defensible estimate is possible.
- predicted_investor_ownership_pct is the expected post-financing investor ownership percentage. It must be between 0 and 100; use prior ownership when available, otherwise make it directionally consistent with deal size, valuation scale, stage, and investor participation.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Return numeric fields as JSON numbers, not strings. Do not use any template/default number as a fallback. Return values that are consistent with your own rationale.

Deal type calibration:
- Do not infer "Seed Round" merely because the company is young or uses early-stage language.
- Do not infer "Early Stage VC" merely because prior_deal_type is "Early Stage VC"; PitchBook stage labels can be broad.
- If prior_deal_type is "Early Stage VC" and prior_vc_round exists, treat "Early Stage VC" as a strong signal, but not an automatic default.
- Seed Round remains plausible when the visible history shows very early financing context: no prior VC round, 1st round, very small prior_deal_size_usd_m, low prior_raised_to_date_usd_m, young company age, few investors, no lead investor, or sparse financing history.
- If prior_deal_type is "Early Stage VC" but prior_vc_round is "1st Round" and the visible deal sizes or raised-to-date are small, Seed Round can still be the better forecast.
- Consider "Later Stage VC" when prior_vc_round, prior_raised_to_date_usd_m, prior_deal_size_usd_m, company age, or deal history indicates a mature financing path.
- Use "Bridge" only when evidence suggests interim financing, insider support, weak momentum, or a short interval after the prior round.
- Use "Debt" only when visible evidence specifically points to debt-like financing.
- If the evidence is mixed between Seed Round and Early Stage VC, choose the label best supported by round progression and observed financing scale, and state the tie-breaker in rationale.

Numeric calibration method:
1. Do not blindly copy the most recent prior deal size. Treat it as one anchor among several.
2. First classify the likely financing regime: step_up_round, flat_follow_on, small_bridge, strategic_large_round, or reset_or_downside_round.
3. Use visible historical trajectory, including any visible prior_company_deal_history or investor deal history, prior_deal_size_usd_m, prior_raised_to_date_usd_m, prior_vc_round, prior_deal_type, investor counts, lead/follow-on signals, company age, employee growth, and industry context.
4. If prior deal sizes vary widely, prefer a range-based estimate from the full visible history rather than the latest round alone.
5. If the company appears to be progressing to a larger institutional or growth round, allow predicted_deal_size_usd_m to be materially larger than the prior round.
6. If evidence suggests bridge, insider support, weak momentum, or a short interval after the prior round, allow predicted_deal_size_usd_m to be materially smaller than the prior round.
7. For predicted_post_money_valuation_usd_m, anchor on visible prior valuation when available. If unavailable, estimate from deal size, stage, valuation_direction, raised-to-date, and company maturity.
8. For predicted_investor_ownership_pct, treat it as expected post-financing investor ownership, not necessarily only new-money dilution. Check that it is directionally plausible relative to deal size and valuation.
9. In rationale, state which numeric anchors were used: latest prior round, full deal history, raised-to-date, round progression, investor structure, company operating signals, or role policy.
10. Before returning JSON, check that deal size, post-money valuation, ownership percentage, deal type, and valuation direction are mutually plausible.

Allowed labels:
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

Return one JSON object only with exactly these keys and types:
- "financing_intent": string, one of the allowed financing_intent labels.
- "completion_view": string, one of the allowed completion_view labels.
- "predicted_deal_size_usd_m": number, expected deal size in million USD.
- "predicted_post_money_valuation_usd_m": number, expected post-money valuation in million USD.
- "predicted_investor_ownership_pct": number, expected post-financing investor ownership percentage from 0 to 100.
- "predicted_deal_type": string, one of Seed Round, Early Stage VC, Later Stage VC, Bridge, Debt, Other.
- "valuation_direction": string, one of the allowed valuation_direction labels.
- "satisfaction_score": number from 0 to 100.
- "rationale": array of short strings.
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
        round_tasks = [
            (
                "Round 1: Identify the weakest assumption in the current aggregated proposal or board "
                "context. Challenge it using your visible fields, role policy, or a stronger interpretation "
                "of visible evidence."
            ),
            (
                "Round 2: Re-evaluate your forecast after the challenges. Update only fields where the "
                "evidence weighting, deal-type calibration, or numeric calibration changed."
            ),
            (
                "Round 3: Produce a final forecast. Prioritize prediction accuracy over negotiation posture, "
                "and do not introduce new concessions unless they improve the forecast."
            ),
        ]
        round_specific_task = round_tasks[min(round_index, len(round_tasks) - 1)]
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

Evidence discipline:
- Current aggregated proposal is an intermediate model estimate, not factual evidence and not ground truth.
- Prior bargaining messages are role opinions unless they cite visible pre-decision fields.
- Do not move toward consensus merely to sound cooperative.
- You may update your forecast when the discussion introduces concrete visible evidence you had not emphasized, a stronger interpretation of visible evidence, or a correction to deal-type/numeric calibration.
- If you change predicted_deal_type or any numeric field, rationale must cite the specific visible evidence or inference that caused the change.
- If you do not change any field, rationale must briefly state why the current forecast remains stronger than the alternatives.
- Your JSON prediction fields are forecasts of the likely realized next financing outcome, not your preferred negotiation demand.

Round-specific task:
{round_specific_task}

Update reporting:
- In rationale, include one short item starting with "update_status: no_change" if no forecast field changed.
- If any forecast field changed, include one short item starting with "update_status: changed_fields=" followed by the changed field names.
- Then state the evidence, reweighted evidence, or calibration correction that caused the update decision.

Hard consistency rules:
- If financing_intent is "raise_now", predicted_deal_size_usd_m must be greater than 0.
- If financing_intent is "wait" or "avoid", predicted_deal_size_usd_m may be 0.
- When financing_intent is "raise_now" and exact amount is not clear, estimate a plausible positive amount from visible historical trajectory, round progression, investor structure, company maturity, operating signals, and role policy. Do not use hidden current-deal labels.
- predicted_post_money_valuation_usd_m is the expected post-money valuation in million USD. Estimate it from visible valuation history, deal size, valuation direction, round stage, raised-to-date, company maturity, and role policy; use 0 only when no defensible estimate is possible.
- predicted_investor_ownership_pct is the expected post-financing investor ownership percentage. It must be between 0 and 100; use prior ownership when available, otherwise make it directionally consistent with deal size, valuation scale, stage, and investor participation.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Return numeric fields as JSON numbers, not strings. Do not use any template/default number as a fallback. Return values that are consistent with your updated rationale.

Deal type calibration:
- Do not infer "Seed Round" merely because the company is young or uses early-stage language.
- Do not infer "Early Stage VC" merely because prior_deal_type is "Early Stage VC"; PitchBook stage labels can be broad.
- If prior_deal_type is "Early Stage VC" and prior_vc_round exists, treat "Early Stage VC" as a strong signal, but not an automatic default.
- Seed Round remains plausible when the visible history shows very early financing context: no prior VC round, 1st round, very small prior_deal_size_usd_m, low prior_raised_to_date_usd_m, young company age, few investors, no lead investor, or sparse financing history.
- If prior_deal_type is "Early Stage VC" but prior_vc_round is "1st Round" and the visible deal sizes or raised-to-date are small, Seed Round can still be the better forecast.
- Consider "Later Stage VC" when prior_vc_round, prior_raised_to_date_usd_m, prior_deal_size_usd_m, company age, or deal history indicates a mature financing path.
- Use "Bridge" only when evidence suggests interim financing, insider support, weak momentum, or a short interval after the prior round.
- Use "Debt" only when visible evidence specifically points to debt-like financing.
- If the evidence is mixed between Seed Round and Early Stage VC, choose the label best supported by round progression and observed financing scale, and state the tie-breaker in rationale.
- During bargaining, you may change predicted_deal_type when another role gives a stronger interpretation of visible stage, round progression, or financing-scale evidence; do not change only for consensus.

Numeric calibration method:
1. Do not blindly copy the most recent prior deal size. Treat it as one anchor among several.
2. First classify the likely financing regime: step_up_round, flat_follow_on, small_bridge, strategic_large_round, or reset_or_downside_round.
3. Use visible historical trajectory, including any visible prior_company_deal_history or investor deal history, prior_deal_size_usd_m, prior_raised_to_date_usd_m, prior_vc_round, prior_deal_type, investor counts, lead/follow-on signals, company age, employee growth, and industry context.
4. If prior deal sizes vary widely, prefer a range-based estimate from the full visible history rather than the latest round alone.
5. If the company appears to be progressing to a larger institutional or growth round, allow predicted_deal_size_usd_m to be materially larger than the prior round.
6. If evidence suggests bridge, insider support, weak momentum, or a short interval after the prior round, allow predicted_deal_size_usd_m to be materially smaller than the prior round.
7. For predicted_post_money_valuation_usd_m, anchor on visible prior valuation when available. If unavailable, estimate from deal size, stage, valuation_direction, raised-to-date, and company maturity.
8. For predicted_investor_ownership_pct, treat it as expected post-financing investor ownership, not necessarily only new-money dilution. Check that it is directionally plausible relative to deal size and valuation.
9. In rationale, state which numeric anchors were used: latest prior round, full deal history, raised-to-date, round progression, investor structure, company operating signals, or role policy.
10. Before returning JSON, check that deal size, post-money valuation, ownership percentage, deal type, and valuation direction are mutually plausible.

Write one concise boardroom bargaining message for round {round_index + 1}, then update your forecast if the discussion changes the likely financing outcome.
The message must:
- focus on financing timing, financing amount, deal type, valuation direction, or investor protections;
- reflect your role's L1 goals, L2 attention, L3 heuristics, and L4 protocol;
- avoid generic corporate slogans;
- be one to three sentences.

Return one JSON object only with exactly these keys and types:
- "message": string, one to three concise boardroom sentences.
- "financing_intent": string, one of raise_now, wait, avoid.
- "completion_view": string, one of likely_complete, unlikely_complete.
- "predicted_deal_size_usd_m": number, expected deal size in million USD.
- "predicted_post_money_valuation_usd_m": number, expected post-money valuation in million USD.
- "predicted_investor_ownership_pct": number, expected post-financing investor ownership percentage from 0 to 100.
- "predicted_deal_type": string, one of Seed Round, Early Stage VC, Later Stage VC, Bridge, Debt, Other.
- "valuation_direction": string, one of up, flat, down.
- "satisfaction_score": number from 0 to 100.
- "rationale": array of short strings.
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


def build_agents(policies: Dict[str, RolePolicy], llm_client: LLMClient) -> Dict[str, BoardAgent]:
    """Instantiate all MVP agents from their role policies and shared LLM client."""
    return {role_name: BoardAgent(policy, llm_client) for role_name, policy in policies.items()}
