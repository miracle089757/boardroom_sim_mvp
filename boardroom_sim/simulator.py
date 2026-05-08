"""Simulation engine for the boardroom MVP."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from boardroom_sim.agents import build_agents
from boardroom_sim.llm import LLMClient
from boardroom_sim.models import (
    BoardCase,
    CeoReplacementView,
    DealCompletionView,
    FinancingIntent,
    RiskLevel,
    RoleDecision,
    SimulationResult,
    TermSheetProposal,
    ValuationDirection,
)
from boardroom_sim.roles import build_role_policies, ordered_role_names


ROLE_WEIGHTS = {
    "Founder_CEO": 2.0,
    "CTO": 0.5,
    "Lead_VC_Director": 3.0,
    "Followon_VC_Director": 1.5,
}


class BoardroomSimulator:
    """Run a deterministic multi-agent boardroom simulation."""

    def __init__(self, llm_client: LLMClient, bargaining_rounds: int = 2) -> None:
        """Create a simulator with fixed role policies, LLM agents, and a round count."""
        self.bargaining_rounds = bargaining_rounds
        self.policies = build_role_policies()
        self.llm_client = llm_client
        self.agents = build_agents(self.policies, llm_client)
        self.role_order = ordered_role_names()

    def simulate(self, case: BoardCase) -> SimulationResult:
        """Run one full point-in-time boardroom simulation case."""
        trace: List[Dict[str, Any]] = []
        context: Dict[str, RoleDecision] = {}
        bargaining_history: List[Dict[str, Any]] = []

        self._record(trace, "preliminary", "system", self._background_summary(case), {})
        self._record(trace, "role_policy", "system", "Loaded strict four-layer role policies.", self._policy_snapshot())

        for role_name in self.role_order:
            decision = self.agents[role_name].evaluate(case, context)
            context[role_name] = decision
            self._record(
                trace,
                "private_assessment",
                role_name,
                self.agents[role_name].rationale_line(decision.rationale),
                decision.to_dict(),
            )

        for role_name in self.role_order:
            statement = self.agents[role_name].opening_statement(context[role_name])
            self._record(trace, "opening_statement", role_name, statement, {})

        proposal = self._build_proposal(case, context)
        self._record(trace, "initial_proposal", "system", "Initial aggregated financing proposal generated.", proposal.to_dict())

        for round_index in range(self.bargaining_rounds):
            proposal = self._run_bargaining_round(case, context, proposal, trace, bargaining_history, round_index)

        financing_intent = self._aggregate_financing_intent(context)
        completion_view = self._aggregate_completion_view(context)
        predicted_deal_size = self._aggregate_deal_size(context)
        predicted_deal_type = self._aggregate_text_choice(context, "predicted_deal_type", "unknown")
        valuation_direction = self._aggregate_valuation(context)
        ceo_decision = self._aggregate_ceo_replacement(context)
        consensus = self._consensus_score(context)
        deal_break_risk = self._deal_break_risk(financing_intent, completion_view, consensus)
        governance_risk = self._governance_conflict_risk(ceo_decision, context)
        final_proposal = self._build_proposal(case, context)

        final_payload = {
            "financing_initiation_decision": financing_intent,
            "financing_completion_view": completion_view,
            "predicted_deal_size_usd_m": predicted_deal_size,
            "predicted_deal_type": predicted_deal_type,
            "valuation_direction": valuation_direction,
            "ceo_replacement_decision": ceo_decision,
            "consensus_score": consensus,
            "deal_break_risk": deal_break_risk,
            "governance_conflict_risk": governance_risk,
        }
        self._record(trace, "closure", "system", "Final boardroom predictions aggregated.", final_payload)

        return SimulationResult(
            case_id=case.case_id,
            company_name=case.company_label,
            financing_initiation_decision=financing_intent,
            financing_completion_view=completion_view,
            predicted_deal_size_usd_m=predicted_deal_size,
            predicted_deal_type=predicted_deal_type,
            valuation_direction=valuation_direction,
            ceo_replacement_decision=ceo_decision,
            role_decisions={role: decision.to_dict() for role, decision in context.items()},
            proposal=final_proposal.to_dict(),
            consensus_score=consensus,
            deal_break_risk=deal_break_risk,
            governance_conflict_risk=governance_risk,
            labels=case.notes.get("labels", {}) if isinstance(case.notes.get("labels", {}), dict) else {},
            trace=trace,
        )

    def _background_summary(self, case: BoardCase) -> str:
        """Create a short shared case background for the trace."""
        prior = (
            f"prior VC round {case.prior_vc_round} on {case.prior_deal_date} "
            f"with size {self._format_money(case.prior_deal_size_usd_m)} and "
            f"post-money {self._format_money(case.prior_post_money_valuation_usd_m)}"
            if case.prior_vc_deal_count > 0
            else "no prior observable VC round"
        )
        return (
            f"{case.company_label} ({case.primary_industry}) is evaluated at decision date {case.decision_date}. "
            f"The company has {case.prior_vc_deal_count} prior VC rounds; {prior}. "
            f"Historical valuation direction is {case.prior_valuation_direction()}."
        )

    def _policy_snapshot(self) -> Dict[str, Any]:
        """Serialize all role policies for auditability."""
        return {name: policy.to_dict() for name, policy in self.policies.items()}

    def _build_proposal(self, case: BoardCase, context: Dict[str, RoleDecision]) -> TermSheetProposal:
        """Build a minimal proposal from current role predictions."""
        size = self._aggregate_deal_size(context)
        deal_type = self._aggregate_text_choice(context, "predicted_deal_type", "unknown")
        valuation_direction = self._aggregate_valuation(context)
        lead = context.get("Lead_VC_Director")

        protection_level = "standard"
        if lead and (lead.ceo_replacement_view in {"monitor", "replace"} or lead.valuation_direction in {"down", "unknown"}):
            protection_level = "strong"
        elif lead and lead.financing_intent == "raise_now" and lead.valuation_direction == "up":
            protection_level = "light"

        cto = context.get("CTO")
        tech_budget_protected = bool(cto and cto.financing_intent != "avoid" and cto.satisfaction_score >= 45.0)
        ceo_milestones_required = bool(lead and lead.ceo_replacement_view in {"monitor", "replace"})

        estimated_dilution = case.estimated_dilution_pct(size)
        return TermSheetProposal(
            recommended_deal_size_usd_m=size,
            recommended_deal_type=deal_type,
            valuation_direction=valuation_direction,
            estimated_dilution_pct=round(estimated_dilution, 3) if estimated_dilution is not None else None,
            investor_protection_level=protection_level,  # type: ignore[arg-type]
            tech_budget_protected=tech_budget_protected,
            ceo_milestones_required=ceo_milestones_required,
        )

    def _format_money(self, value: Any) -> str:
        """Format a nullable million-USD value for trace text."""
        if value is None:
            return "unknown"
        return f"{value}M USD"

    def _run_bargaining_round(
        self,
        case: BoardCase,
        context: Dict[str, RoleDecision],
        proposal: TermSheetProposal,
        trace: List[Dict[str, Any]],
        bargaining_history: List[Dict[str, Any]],
        round_index: int,
    ) -> TermSheetProposal:
        """Run one bargaining round and let roles update their predictions."""
        for role_name in self.role_order:
            message, updated_decision = self.agents[role_name].bargaining_step(
                case=case,
                decision=context[role_name],
                proposal=proposal,
                round_index=round_index,
                context=context,
                prior_messages=bargaining_history,
            )
            context[role_name] = updated_decision
            event = {
                "round": round_index + 1,
                "role": role_name,
                "message": message,
                "updated_decision": updated_decision.to_dict(),
            }
            bargaining_history.append(event)
            self._record(
                trace,
                f"bargaining_round_{round_index + 1}",
                role_name,
                message,
                {
                    "case_id": case.case_id,
                    "proposal_before_message": proposal.to_dict(),
                    "updated_decision": updated_decision.to_dict(),
                },
            )
        proposal = self._build_proposal(case, context)
        self._record(
            trace,
            f"proposal_after_round_{round_index + 1}",
            "system",
            "Aggregated proposal updated after bargaining round.",
            proposal.to_dict(),
        )
        return proposal

    def _aggregate_financing_intent(self, context: Dict[str, RoleDecision]) -> FinancingIntent:
        """Aggregate role predictions into the final financing initiation decision."""
        return self._weighted_choice(context, "financing_intent", "raise_now")  # type: ignore[return-value]

    def _aggregate_completion_view(self, context: Dict[str, RoleDecision]) -> DealCompletionView:
        """Aggregate role views on whether the proposed financing is likely to complete."""
        return self._weighted_choice(context, "completion_view", "likely_complete")  # type: ignore[return-value]

    def _aggregate_deal_size(self, context: Dict[str, RoleDecision]) -> float:
        """Aggregate predicted deal size using board influence weights."""
        weighted_total = 0.0
        weight_total = 0.0
        for role, decision in context.items():
            if decision.predicted_deal_size_usd_m <= 0 or decision.financing_intent == "avoid":
                continue
            weight = ROLE_WEIGHTS.get(role, 1.0)
            weighted_total += decision.predicted_deal_size_usd_m * weight
            weight_total += weight
        if weight_total <= 0:
            return 0.0
        return round(weighted_total / weight_total, 6)

    def _aggregate_text_choice(self, context: Dict[str, RoleDecision], attr: str, default: str) -> str:
        """Aggregate free-text categorical choices using influence weights."""
        return self._weighted_choice(context, attr, default)

    def _aggregate_valuation(self, context: Dict[str, RoleDecision]) -> ValuationDirection:
        """Aggregate valuation-direction views using board influence weights."""
        return self._weighted_choice(context, "valuation_direction", "flat")  # type: ignore[return-value]

    def _aggregate_ceo_replacement(self, context: Dict[str, RoleDecision]) -> CeoReplacementView:
        """Aggregate CEO replacement outcome from founder resistance and investor governance pressure."""
        lead_view = context["Lead_VC_Director"].ceo_replacement_view
        follow_view = context["Followon_VC_Director"].ceo_replacement_view
        cto_view = context["CTO"].ceo_replacement_view

        if lead_view == "replace" and follow_view in {"replace", "monitor"} and cto_view != "keep":
            return "replace"
        if lead_view in {"replace", "monitor"} or follow_view == "monitor" or cto_view == "monitor":
            return "monitor"
        return "keep"

    def _weighted_choice(self, context: Dict[str, RoleDecision], attr: str, default: str) -> str:
        """Return the weighted modal value for an attribute across role decisions."""
        score = Counter()
        for role, decision in context.items():
            value = getattr(decision, attr, default)
            if not value:
                continue
            score[str(value)] += ROLE_WEIGHTS.get(role, 1.0)
        if not score:
            return default
        return score.most_common(1)[0][0]

    def _consensus_score(self, context: Dict[str, RoleDecision]) -> float:
        """Compute a simple consensus score from agreement on core predicted events."""
        if not context:
            return 0.0
        attrs = [
            "financing_intent",
            "completion_view",
            "predicted_deal_type",
            "valuation_direction",
            "ceo_replacement_view",
        ]
        agreement = 0
        for attr in attrs:
            agreement += Counter(str(getattr(decision, attr)) for decision in context.values()).most_common(1)[0][1]
        return round(agreement / (len(context) * len(attrs)), 3)

    def _deal_break_risk(
        self,
        financing_intent: FinancingIntent,
        completion_view: DealCompletionView,
        consensus_score: float,
    ) -> RiskLevel:
        """Map financing intent, completion view, and consensus into deal-break risk."""
        if financing_intent == "avoid" or completion_view == "unlikely_complete" or consensus_score < 0.45:
            return "high"
        if financing_intent == "wait" or consensus_score < 0.70:
            return "medium"
        return "low"

    def _governance_conflict_risk(self, ceo_decision: CeoReplacementView, context: Dict[str, RoleDecision]) -> RiskLevel:
        """Map CEO replacement pressure and role disagreement into governance conflict risk."""
        if ceo_decision == "replace":
            return "high"
        if ceo_decision == "monitor":
            return "medium"
        investor_pressure = context["Lead_VC_Director"].ceo_replacement_view != "keep"
        return "medium" if investor_pressure else "low"

    def _record(
        self,
        trace: List[Dict[str, Any]],
        stage: str,
        actor: str,
        message: str,
        payload: Dict[str, Any],
    ) -> None:
        """Append one structured trace event to the simulation trace."""
        trace.append(
            {
                "stage": stage,
                "actor": actor,
                "message": message,
                "payload": payload,
            }
        )
