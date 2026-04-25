"""Simulation engine for the boardroom MVP."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from boardroom_sim.agents import build_agents
from boardroom_sim.llm import LLMClient
from boardroom_sim.models import (
    BoardCase,
    CeoReplacementView,
    FinancingVote,
    RoleDecision,
    SimulationResult,
    TermSheetProposal,
    ValuationDirection,
)
from boardroom_sim.roles import build_role_policies, ordered_role_names


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
        """Run one full boardroom simulation case."""
        trace: List[Dict[str, Any]] = []
        context: Dict[str, RoleDecision] = {}

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

        proposal = self._build_initial_proposal(case, context)
        self._record(trace, "initial_proposal", "Lead_VC_Director", "Initial term-sheet proposal generated.", proposal.to_dict())

        for round_index in range(self.bargaining_rounds):
            self._run_bargaining_round(case, context, proposal, trace, round_index)

        financing_decision = self._aggregate_financing(context)
        valuation_direction = self._aggregate_valuation(context)
        ceo_decision = self._aggregate_ceo_replacement(case, context)
        consensus = self._consensus_score(context)
        deal_break_risk = self._deal_break_risk(financing_decision, consensus)
        governance_risk = self._governance_conflict_risk(ceo_decision, context)

        final_payload = {
            "financing_decision": financing_decision,
            "valuation_direction": valuation_direction,
            "ceo_replacement_decision": ceo_decision,
            "consensus_score": consensus,
            "deal_break_risk": deal_break_risk,
            "governance_conflict_risk": governance_risk,
        }
        self._record(trace, "closure", "system", "Final boardroom decisions aggregated.", final_payload)

        return SimulationResult(
            case_id=case.case_id,
            company_name=case.company_name,
            financing_decision=financing_decision,
            valuation_direction=valuation_direction,
            ceo_replacement_decision=ceo_decision,
            role_decisions={role: decision.to_dict() for role, decision in context.items()},
            proposal=proposal.to_dict(),
            consensus_score=consensus,
            deal_break_risk=deal_break_risk,
            governance_conflict_risk=governance_risk,
            trace=trace,
        )

    def _background_summary(self, case: BoardCase) -> str:
        """Create a short shared case background for the trace."""
        return (
            f"{case.company_name} ({case.industry}) is considering a {case.round_type} round. "
            f"Deal size is {case.deal_size_usd_m}M USD, post-money valuation is "
            f"{case.post_money_valuation_usd_m}M USD, runway is {case.runway_months} months."
        )

    def _policy_snapshot(self) -> Dict[str, Any]:
        """Serialize all role policies for auditability."""
        return {name: policy.to_dict() for name, policy in self.policies.items()}

    def _build_initial_proposal(self, case: BoardCase, context: Dict[str, RoleDecision]) -> TermSheetProposal:
        """Build a minimal term-sheet proposal from case facts and lead-VC stance."""
        lead = context["Lead_VC_Director"]
        protection_level = "standard"
        if lead.financing_vote == "reject" or lead.ceo_replacement_view in {"monitor", "replace"}:
            protection_level = "strong"
        elif lead.financing_vote == "approve" and lead.valuation_direction == "up":
            protection_level = "light"

        tech_budget_protected = case.engineering_headcount_growth_rate >= 0.0 and case.tech_debt_risk < 0.75
        ceo_milestones_required = lead.ceo_replacement_view in {"monitor", "replace"}

        return TermSheetProposal(
            deal_size_usd_m=case.deal_size_usd_m,
            valuation_direction=lead.valuation_direction,
            implied_dilution_pct=case.implied_dilution_pct(),
            investor_protection_level=protection_level,
            tech_budget_protected=tech_budget_protected,
            ceo_milestones_required=ceo_milestones_required,
        )

    def _run_bargaining_round(
        self,
        case: BoardCase,
        context: Dict[str, RoleDecision],
        proposal: TermSheetProposal,
        trace: List[Dict[str, Any]],
        round_index: int,
    ) -> None:
        """Record one lightweight bargaining round without changing the deterministic base decisions."""
        for role_name in self.role_order:
            message = self.agents[role_name].bargaining_message(
                case=case,
                decision=context[role_name],
                proposal=proposal,
                round_index=round_index,
                context=context,
            )
            self._record(
                trace,
                f"bargaining_round_{round_index + 1}",
                role_name,
                message,
                {
                    "case_id": case.case_id,
                    "proposal": proposal.to_dict(),
                    "current_decision": context[role_name].to_dict(),
                },
            )

    def _aggregate_financing(self, context: Dict[str, RoleDecision]) -> FinancingVote:
        """Aggregate role votes into the final financing decision."""
        ceo_vote = context["Founder_CEO"].financing_vote
        lead_vote = context["Lead_VC_Director"].financing_vote
        cto_vote = context["CTO"].financing_vote

        if ceo_vote == "reject" or lead_vote == "reject":
            return "reject"
        if "renegotiate" in {ceo_vote, lead_vote, cto_vote} or cto_vote == "reject":
            return "renegotiate"
        return "approve"

    def _aggregate_valuation(self, context: Dict[str, RoleDecision]) -> ValuationDirection:
        """Aggregate valuation-direction views using board influence weights."""
        weights = {
            "Founder_CEO": 2.0,
            "CTO": 0.5,
            "Lead_VC_Director": 3.0,
            "Followon_VC_Director": 1.5,
        }
        score = Counter()
        for role, decision in context.items():
            score[decision.valuation_direction] += weights[role]
        if not score:
            return "unknown"
        return score.most_common(1)[0][0]  # type: ignore[return-value]

    def _aggregate_ceo_replacement(self, case: BoardCase, context: Dict[str, RoleDecision]) -> CeoReplacementView:
        """Aggregate CEO replacement outcome from founder resistance and investor governance pressure."""
        lead_view = context["Lead_VC_Director"].ceo_replacement_view
        follow_view = context["Followon_VC_Director"].ceo_replacement_view
        cto_view = context["CTO"].ceo_replacement_view

        if lead_view == "replace" and (follow_view in {"replace", "monitor"} or case.ceo_performance_risk >= 0.85):
            if cto_view != "keep" or case.ceo_performance_risk >= 0.85:
                return "replace"
        if lead_view in {"replace", "monitor"} or follow_view == "monitor" or cto_view == "monitor":
            return "monitor"
        return "keep"

    def _consensus_score(self, context: Dict[str, RoleDecision]) -> float:
        """Compute a simple consensus score from agreement on the three focal events."""
        financing_count = Counter(decision.financing_vote for decision in context.values()).most_common(1)[0][1]
        valuation_count = Counter(decision.valuation_direction for decision in context.values()).most_common(1)[0][1]
        ceo_count = Counter(decision.ceo_replacement_view for decision in context.values()).most_common(1)[0][1]
        role_count = max(1, len(context))
        return round((financing_count + valuation_count + ceo_count) / (role_count * 3.0), 3)

    def _deal_break_risk(self, financing_decision: FinancingVote, consensus_score: float) -> str:
        """Map financing decision and consensus into a deal-break risk level."""
        if financing_decision == "reject" or consensus_score < 0.45:
            return "high"
        if financing_decision == "renegotiate" or consensus_score < 0.70:
            return "medium"
        return "low"

    def _governance_conflict_risk(self, ceo_decision: CeoReplacementView, context: Dict[str, RoleDecision]) -> str:
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
