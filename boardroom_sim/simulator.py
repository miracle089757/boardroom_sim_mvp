"""Simulation engine for the boardroom MVP."""

from __future__ import annotations

from collections import Counter
from typing import Any, Dict, List

from boardroom_sim.agents import build_agents
from boardroom_sim.config import DEFAULT_ROLE_WEIGHTS, ExperimentConfig, load_experiment_config
from boardroom_sim.llm import LLMClient
from boardroom_sim.models import (
    BoardCase,
    DealCompletionView,
    FinancingIntent,
    RiskLevel,
    RoleDecision,
    SimulationResult,
    TermSheetProposal,
    ValuationDirection,
)
from boardroom_sim.process import BoardProcessController, changed_fields
from boardroom_sim.prompts import PromptRenderer
from boardroom_sim.roles import build_role_policies


ROLE_WEIGHTS = dict(DEFAULT_ROLE_WEIGHTS)


class BoardroomSimulator:
    """Run a deterministic multi-agent boardroom simulation."""

    def __init__(
        self,
        llm_client: LLMClient,
        bargaining_rounds: int | None = None,
        config: ExperimentConfig | None = None,
    ) -> None:
        """Create a simulator with fixed role policies, LLM agents, and discussion limits."""
        self.config = config or load_experiment_config()
        if self.config.discussion_paradigm != "memory":
            raise ValueError(
                f"Unsupported discussion paradigm for this implementation: {self.config.discussion_paradigm}. "
                "Currently supported: memory."
            )
        if self.config.decision_protocol != "weighted_vote":
            raise ValueError(
                f"Unsupported decision protocol for this implementation: {self.config.decision_protocol}. "
                "Currently supported: weighted_vote."
        )
        self.role_order = list(self.config.role_order)
        if bargaining_rounds is not None:
            self.config.board_process.max_rounds = max(1, bargaining_rounds)
            self.config.board_process.min_rounds = min(
                self.config.board_process.min_rounds,
                self.config.board_process.max_rounds,
            )
        self.bargaining_rounds = self.config.board_process.max_rounds
        self.process = BoardProcessController(self.config.board_process, self.role_order)
        self.base_role_weights = dict(self.config.role_weights)
        self.role_weights = self.process.effective_role_weights(self.base_role_weights)
        self.policies = build_role_policies(self.config.role_policy_dir, self.role_order)
        self.llm_client = llm_client
        prompt_renderer = PromptRenderer(
            prompts_dir=self.config.prompts_dir,
            response_generator=self.config.response_generator,
        )
        prompt_renderer.round_tasks = list(self.config.round_tasks)
        self.agents = build_agents(self.policies, llm_client, prompt_renderer=prompt_renderer)

    def simulate(self, case: BoardCase) -> SimulationResult:
        """Run one full point-in-time boardroom simulation case."""
        trace: List[Dict[str, Any]] = []
        context: Dict[str, RoleDecision] = {}
        bargaining_history: List[Dict[str, Any]] = []

        self._record(trace, "preliminary", "system", self._background_summary(case), {})
        self._record(trace, "role_policy", "system", "Loaded strict four-layer role policies.", self._policy_snapshot())
        self._record(
            trace,
            "board_process",
            "system",
            "Loaded configurable board process settings.",
            {
                "process": self.process.to_trace_payload(),
                "base_role_weights": self.base_role_weights,
                "effective_role_weights": self.role_weights,
            },
        )

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
            round_number = round_index + 1
            round_events = [event for event in bargaining_history if int(event.get("round", 0)) == round_number]
            continuation = self.process.should_continue_discussion(
                round_number=round_number,
                round_events=round_events,
                history=bargaining_history,
                consensus_score=self._consensus_score(context),
            )
            self._record(
                trace,
                f"process_decision_after_round_{round_number}",
                "system",
                self._continuation_message(continuation),
                continuation,
            )
            if not continuation["continue_discussion"]:
                break

        financing_intent = self._aggregate_financing_intent(context)
        completion_view = self._aggregate_completion_view(context)
        predicted_deal_size = self._aggregate_deal_size(context)
        predicted_post_money_valuation = self._aggregate_positive_numeric(
            context,
            "predicted_post_money_valuation_usd_m",
        )
        predicted_investor_ownership = self._aggregate_positive_numeric(
            context,
            "predicted_investor_ownership_pct",
        )
        predicted_deal_type = self._aggregate_text_choice(context, "predicted_deal_type", "unknown")
        valuation_direction = self._aggregate_valuation(context)
        consensus = self._consensus_score(context)
        deal_break_risk = self._deal_break_risk(financing_intent, completion_view, consensus)
        final_proposal = self._build_proposal(case, context)

        final_payload = {
            "financing_initiation_decision": financing_intent,
            "financing_completion_view": completion_view,
            "predicted_deal_size_usd_m": predicted_deal_size,
            "predicted_post_money_valuation_usd_m": predicted_post_money_valuation,
            "predicted_investor_ownership_pct": predicted_investor_ownership,
            "predicted_deal_type": predicted_deal_type,
            "valuation_direction": valuation_direction,
            "consensus_score": consensus,
            "deal_break_risk": deal_break_risk,
        }
        self._record(trace, "closure", "system", "Final boardroom predictions aggregated.", final_payload)

        return SimulationResult(
            case_id=case.case_id,
            company_name=case.company_label,
            financing_initiation_decision=financing_intent,
            financing_completion_view=completion_view,
            predicted_deal_size_usd_m=predicted_deal_size,
            predicted_post_money_valuation_usd_m=predicted_post_money_valuation,
            predicted_investor_ownership_pct=predicted_investor_ownership,
            predicted_deal_type=predicted_deal_type,
            valuation_direction=valuation_direction,
            role_decisions={role: decision.to_dict() for role, decision in context.items()},
            proposal=final_proposal.to_dict(),
            consensus_score=consensus,
            deal_break_risk=deal_break_risk,
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
        post_money_valuation = self._aggregate_positive_numeric(context, "predicted_post_money_valuation_usd_m")
        investor_ownership = self._aggregate_positive_numeric(context, "predicted_investor_ownership_pct")
        deal_type = self._aggregate_text_choice(context, "predicted_deal_type", "unknown")
        valuation_direction = self._aggregate_valuation(context)
        lead = context.get("Lead_VC_Director")

        protection_level = "standard"
        if lead and lead.valuation_direction in {"down", "unknown"}:
            protection_level = "strong"
        elif lead and lead.financing_intent == "raise_now" and lead.valuation_direction == "up":
            protection_level = "light"

        cto = context.get("CTO")
        tech_budget_protected = bool(cto and cto.financing_intent != "avoid" and cto.satisfaction_score >= 45.0)

        estimated_dilution = case.estimated_dilution_pct(size)
        return TermSheetProposal(
            recommended_deal_size_usd_m=size,
            recommended_post_money_valuation_usd_m=post_money_valuation,
            recommended_investor_ownership_pct=investor_ownership,
            recommended_deal_type=deal_type,
            valuation_direction=valuation_direction,
            estimated_dilution_pct=round(estimated_dilution, 3) if estimated_dilution is not None else None,
            investor_protection_level=protection_level,  # type: ignore[arg-type]
            tech_budget_protected=tech_budget_protected,
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
        speakers = self.process.speaking_order_for_round(round_index, self.role_weights)
        round_payload = {
            "round": round_index + 1,
            "speaking_order": speakers,
            "base_role_weights": self.base_role_weights,
            "effective_role_weights": self.role_weights,
            "process": self.process.to_trace_payload(),
        }
        self._record(
            trace,
            f"process_round_{round_index + 1}",
            "system",
            "Board process controller selected the round speakers and process constraints.",
            round_payload,
        )
        if not speakers:
            self._record(
                trace,
                f"bargaining_round_{round_index + 1}",
                "system",
                "No role speaks in this round under the configured board process.",
                {"case_id": case.case_id, **round_payload},
            )

        for role_name in speakers:
            process_context = self.process.prompt_context(
                role_name=role_name,
                round_index=round_index,
                speakers=speakers,
                effective_weights=self.role_weights,
            )
            visible_history = self.process.visible_history(bargaining_history, round_index + 1)
            previous_decision = context[role_name]
            message, updated_decision, meeting_artifacts = self.agents[role_name].bargaining_step(
                case=case,
                decision=previous_decision,
                proposal=proposal,
                round_index=round_index,
                context=context,
                prior_messages=visible_history,
                process_context=process_context,
            )
            context[role_name] = updated_decision
            changed = changed_fields(previous_decision, updated_decision)
            event = {
                "round": round_index + 1,
                "role": role_name,
                "message": message,
                "changed_fields": changed,
                "process_context": process_context,
                "meeting_artifacts": meeting_artifacts,
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
                    "process_context": process_context,
                    "meeting_artifacts": meeting_artifacts,
                    "visible_history_count": len(visible_history),
                    "changed_fields": changed,
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

    def _continuation_message(self, continuation: Dict[str, Any]) -> str:
        """Summarize why the board continues or closes discussion."""
        action = "Continue discussion" if continuation.get("continue_discussion") else "Close discussion"
        reasons = " ".join(str(item) for item in continuation.get("reasons", []))
        return f"{action} after round {continuation.get('round')}: {reasons}"

    def _aggregate_financing_intent(self, context: Dict[str, RoleDecision]) -> FinancingIntent:
        """Aggregate role predictions into the final financing initiation decision."""
        return self._weighted_choice(context, "financing_intent", "raise_now")  # type: ignore[return-value]

    def _aggregate_completion_view(self, context: Dict[str, RoleDecision]) -> DealCompletionView:
        """Aggregate role views on whether the proposed financing is likely to complete."""
        return self._weighted_choice(context, "completion_view", "likely_complete")  # type: ignore[return-value]

    def _aggregate_deal_size(self, context: Dict[str, RoleDecision]) -> float:
        """Aggregate predicted deal size using board influence weights."""
        return self._aggregate_positive_numeric(context, "predicted_deal_size_usd_m")

    def _aggregate_positive_numeric(self, context: Dict[str, RoleDecision], attr: str) -> float:
        """Aggregate a positive numeric prediction using board influence weights."""
        weighted_total = 0.0
        weight_total = 0.0
        for role, decision in context.items():
            value = getattr(decision, attr, 0.0)
            if value <= 0 or decision.financing_intent == "avoid":
                continue
            weight = self.role_weights.get(role, 1.0)
            weighted_total += value * weight
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

    def _weighted_choice(self, context: Dict[str, RoleDecision], attr: str, default: str) -> str:
        """Return the weighted modal value for an attribute across role decisions."""
        score = Counter()
        for role, decision in context.items():
            value = getattr(decision, attr, default)
            if not value:
                continue
            score[str(value)] += self.role_weights.get(role, 1.0)
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
