"""Configurable board process controls for simulation rounds."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Sequence

from boardroom_sim.config import BoardProcessConfig
from boardroom_sim.culture import interpret_l5_culture
from boardroom_sim.models import RoleDecision


PROCESS_INSTRUCTIONS = {
    "chair_gated": "主席门控式流程：严格按既定顺序发言，角色应回应此前明确提出的证据、问题或分歧。",
    "free_interjection": "开放式流程：本轮发言顺序会轮换，角色可以更主动挑战此前任何角色的证据解释。",
    "top3_dominance": "少数强势董事主导流程：影响权重较高的前三位角色更容易塑造最终结论。",
    "rubber_stamp": "橡皮图章流程：正式讨论较短，角色只有在发现明显预测错误或重大遗漏时才应改变判断。",
}

ARCHETYPE_INSTRUCTIONS = {
    "aunt": "姑妈型董事会：会议默认确认管理层方案。除非可见证据明显反驳当前预测，否则发言应短、保守，并避免引入新的强对抗。",
    "barbarian": "野蛮人型董事会：会议默认从控制、监督和风险暴露出发。发言应主动指出证据缺口、估值风险或投资人保护不足。",
    "clan": "宗族型董事会：会议默认重视关系和共识。发言可以温和，但仍需说明共识是否由可见证据支撑，避免无证据从众。",
    "value_creating": "价值创造型董事会：会议应同时保持支持和挑战。发言需要把建设性异议、可见证据和最终预测校准连接起来。",
}

MEETING_PHASES = {
    "aunt": [
        {
            "phase": "management_framing",
            "purpose": "管理层陈述融资动议，董事会主要确认是否存在明显反证。",
            "expected_contribution": "围绕当前方案做有限确认；只有在可见字段明显冲突时才提出问题。",
        },
        {
            "phase": "factual_clarification",
            "purpose": "澄清融资规模、交易类型、上一轮融资和公司阶段等基础事实。",
            "expected_contribution": "用简短发言确认事实或轻微修正，不主动扩大议题。",
        },
        {
            "phase": "exception_check",
            "purpose": "检查是否存在足以推翻默认方案的异常风险。",
            "expected_contribution": "说明是否发现严重反证；如没有，则维持原判断。",
        },
        {
            "phase": "limited_terms_review",
            "purpose": "有限审查估值、持股和投资人保护条款。",
            "expected_contribution": "只提出必要条款调整，避免进入开放式重谈。",
        },
        {
            "phase": "consent_check",
            "purpose": "确认董事是否愿意接受当前方案或保留意见。",
            "expected_contribution": "明确支持、保留或有限反对的理由。",
        },
        {
            "phase": "motion_confirmation",
            "purpose": "形成接近橡皮图章式的会前结论。",
            "expected_contribution": "说明是否维持立场，以及是否存在足以阻止方案的证据。",
        },
    ],
    "barbarian": [
        {
            "phase": "risk_interrogation",
            "purpose": "强势董事围绕估值、控制权和融资完成风险质询管理层假设。",
            "expected_contribution": "直接指出最脆弱的假设，并要求更强证据或更强投资人保护。",
        },
        {
            "phase": "evidence_demand",
            "purpose": "要求角色用可见字段锚定判断，而不是只表达偏好。",
            "expected_contribution": "列出证据缺口、数据不一致或需要被证明的关键假设。",
        },
        {
            "phase": "control_terms_pressure",
            "purpose": "围绕替代条款、估值下修、保护条款或拒绝融资进行压力测试。",
            "expected_contribution": "提出至少一个投资人保护或交易结构替代方案。",
        },
        {
            "phase": "alternatives_pressure",
            "purpose": "比较继续融资、等待、缩小规模或改变交易结构的替代路径。",
            "expected_contribution": "明确哪条替代路径会降低风险，以及对预测字段的影响。",
        },
        {
            "phase": "hard_commitment",
            "purpose": "在冲突后形成强势立场并判断交易是否仍可能完成。",
            "expected_contribution": "明确哪些条件必须满足，否则应下调完成概率或估值方向。",
        },
        {
            "phase": "dissent_or_approval",
            "purpose": "记录最终批准、反对或保留意见。",
            "expected_contribution": "给出最终立场、保留意见和未解决风险。",
        },
    ],
    "clan": [
        {
            "phase": "relationship_alignment",
            "purpose": "先建立共同目标，确认各角色是否接受融资方向。",
            "expected_contribution": "承认共同目标，再提出温和证据分歧。",
        },
        {
            "phase": "shared_facts",
            "purpose": "把各角色认可的事实基础整理成共同理解。",
            "expected_contribution": "说明哪些事实可以支持共识，哪些事实仍需要澄清。",
        },
        {
            "phase": "consensus_building",
            "purpose": "把不同证据解释整合为董事会可共同接受的融资方案。",
            "expected_contribution": "回应上一轮观点，说明如何在不破坏关系的前提下修正预测。",
        },
        {
            "phase": "concern_softening",
            "purpose": "处理少数疑虑，使保留意见变成可管理的条件。",
            "expected_contribution": "用温和方式提出修正，并说明它如何保护关系和交易可行性。",
        },
        {
            "phase": "shared_position",
            "purpose": "形成可被多数成员接受的共同立场。",
            "expected_contribution": "给出共同立场和少数保留意见，避免无证据从众。",
        },
        {
            "phase": "consent_confirmation",
            "purpose": "确认是否有足够共识进入最终批准或记录保留意见。",
            "expected_contribution": "明确最终支持程度，以及是否还有需要记录的异议。",
        },
    ],
    "value_creating": [
        {
            "phase": "evidence_framing",
            "purpose": "充分暴露关键证据、角色目标和融资路径假设。",
            "expected_contribution": "用角色视角提出一个关键证据锚点，并说明它支持或挑战当前提案。",
        },
        {
            "phase": "assumption_clarification",
            "purpose": "澄清融资规模、估值、完成概率和交易类型背后的关键假设。",
            "expected_contribution": "指出一个必须被验证的假设，并说明若假设不成立应如何调整预测。",
        },
        {
            "phase": "constructive_challenge",
            "purpose": "在支持公司价值创造的同时，对交易类型、规模和估值做建设性挑战。",
            "expected_contribution": "提出可证伪挑战，并给出一个可执行替代解释或交易情境。",
        },
        {
            "phase": "alternative_design",
            "purpose": "比较不同融资路径、条款组合和治理安排。",
            "expected_contribution": "提出或评估替代方案，并说明它对角色满意度和最终预测的影响。",
        },
        {
            "phase": "synthesis",
            "purpose": "整合冲突观点，把分歧转化为可落地条款或保留意见。",
            "expected_contribution": "说明采纳了哪些观点、拒绝了哪些观点，以及预测如何被校准。",
        },
        {
            "phase": "commitment_and_vote",
            "purpose": "形成最终角色承诺和可评估预测。",
            "expected_contribution": "给出最终支持、反对、保留或要求修改的会议立场，并同步内部预测。",
        },
    ],
}


class BoardProcessController:
    """Apply board-process settings to speaking order, memory, and influence."""

    def __init__(self, config: BoardProcessConfig, role_order: Sequence[str]) -> None:
        self.config = config
        self.role_order = list(role_order)

    def to_trace_payload(self) -> Dict[str, Any]:
        """Return a serializable process snapshot for traces and manifests."""
        return asdict(self.config)

    def effective_role_weights(self, base_weights: Dict[str, float]) -> Dict[str, float]:
        """Return board-process-adjusted role weights."""
        configured_multipliers = self.config.role_weight_multipliers
        weights: Dict[str, float] = {}
        for role_name in self.role_order:
            base = float(base_weights.get(role_name, 1.0))
            multiplier = configured_multipliers.get(role_name, 1.0)
            weights[role_name] = round(base * multiplier, 6)
        for role_name, weight in base_weights.items():
            if role_name not in weights:
                weights[role_name] = float(weight)
        return weights

    def speaking_order_for_round(
        self,
        round_index: int,
        effective_weights: Dict[str, float],
    ) -> List[str]:
        """Return the roles that speak in one bargaining round."""
        protocol = self.config.protocol
        if protocol == "free_interjection" and self.role_order:
            shift = round_index % len(self.role_order)
            return self.role_order[shift:] + self.role_order[:shift]
        if protocol == "top3_dominance":
            ranked = sorted(self.role_order, key=lambda role: effective_weights.get(role, 1.0), reverse=True)
            return ranked[: min(3, len(ranked))]
        if protocol == "rubber_stamp":
            if round_index == 0:
                return [role for role in self.role_order if role in {"Founder_CEO", "Lead_VC_Director"}]
            if round_index == 1:
                return [role for role in self.role_order if role in {"Lead_VC_Director", "Followon_VC_Director"}]
            return [role for role in self.role_order if role in {"Founder_CEO", "Lead_VC_Director"}]
        return list(self.role_order)

    def visible_history(self, history: List[Dict[str, Any]], round_number: int) -> List[Dict[str, Any]]:
        """Filter bargaining history according to process memory scope."""
        scope = self.config.memory_scope
        if scope == "none":
            return []
        if scope == "round":
            return [item for item in history if int(item.get("round", -1)) == round_number]
        if scope == "limited":
            window = max(0, self.config.memory_window)
            return history[-window:] if window else []
        return list(history)

    def prompt_context(
        self,
        *,
        role_name: str,
        round_index: int,
        speakers: Sequence[str],
        effective_weights: Dict[str, float],
    ) -> Dict[str, Any]:
        """Return process constraints to expose to an agent prompt."""
        protocol = self.config.protocol
        l5_policy = interpret_l5_culture(self.config.culture)
        meeting_phase = self.meeting_phase_for_round(round_index)
        return {
            "board_archetype": self.config.archetype,
            "board_archetype_label": self.config.archetype_label,
            "board_archetype_description": self.config.archetype_description,
            "discussion_protocol": protocol,
            "dominance_pattern": self.config.dominance_pattern,
            "meeting_phase": meeting_phase,
            "culture_layer": self.config.culture_layer,
            "l5_culture": l5_policy,
            "culture": dict(self.config.culture),
            "challenge_required": self.config.challenge_required,
            "memory_scope": self.config.memory_scope,
            "memory_window": self.config.memory_window,
            "round_number": round_index + 1,
            "speaking_order_this_round": list(speakers),
            "current_role": role_name,
            "current_role_effective_weight": effective_weights.get(role_name, 1.0),
            "discussion_limits": {
                "min_rounds": self.config.min_rounds,
                "max_rounds": self.config.max_rounds,
                "stop_when_consensus_score_gte": self.config.stop_when_consensus_score_gte,
                "stop_when_no_role_changes_for_rounds": self.config.stop_when_no_role_changes_for_rounds,
                "stop_when_no_open_questions": self.config.stop_when_no_open_questions,
            },
            "process_instruction": self._process_instruction(protocol, meeting_phase, l5_policy),
            "challenge_instruction": self._challenge_instruction(l5_policy),
        }

    def meeting_phase_for_round(self, round_index: int) -> Dict[str, Any]:
        """Return the archetype-specific meeting phase for the current round."""
        phases = MEETING_PHASES.get(self.config.archetype, MEETING_PHASES["value_creating"])
        phase = dict(phases[min(round_index, len(phases) - 1)])
        phase["round_number"] = round_index + 1
        phase["phase_index"] = min(round_index, len(phases) - 1) + 1
        phase["phase_count"] = len(phases)
        return phase

    def should_continue_discussion(
        self,
        *,
        round_number: int,
        round_events: Sequence[Dict[str, Any]],
        history: Sequence[Dict[str, Any]],
        consensus_score: float,
    ) -> Dict[str, Any]:
        """Decide whether the board should continue after one completed round."""
        changed_count = sum(1 for event in round_events if event.get("changed_fields"))
        open_questions = self._artifact_values(round_events, "questions_raised")
        alternative_options = self._artifact_values(round_events, "alternative_options")
        no_change_streak = self._no_change_round_streak(history)

        reasons: List[str] = []
        continue_discussion = False
        if round_number >= self.config.max_rounds:
            reasons.append("已达到最大讨论轮数，进入最终聚合。")
        elif round_number < self.config.min_rounds:
            continue_discussion = True
            reasons.append("尚未达到最小讨论轮数，需要继续推进会议。")
        elif changed_count > 0:
            continue_discussion = True
            reasons.append("本轮仍有角色更新了结构化预测，需要观察后续回应。")
        elif self.config.stop_when_no_open_questions and open_questions:
            continue_discussion = True
            reasons.append("本轮提出了尚未在流程层面确认关闭的问题，需要继续讨论。")
        elif consensus_score < self.config.stop_when_consensus_score_gte:
            continue_discussion = True
            reasons.append("当前共识分数低于停止阈值，需要继续整合分歧。")
        elif no_change_streak < self.config.stop_when_no_role_changes_for_rounds:
            continue_discussion = True
            reasons.append("结构化预测稳定时间不足，需要再观察一轮。")
        else:
            reasons.append("达到最小轮数，预测已稳定，未发现新的开放问题，且共识分数达到停止阈值。")

        return {
            "round": round_number,
            "continue_discussion": continue_discussion,
            "reasons": reasons,
            "consensus_score": consensus_score,
            "changed_role_count": changed_count,
            "no_change_round_streak": no_change_streak,
            "open_questions_this_round": open_questions,
            "alternative_options_this_round": alternative_options,
            "limits": {
                "min_rounds": self.config.min_rounds,
                "max_rounds": self.config.max_rounds,
                "stop_when_consensus_score_gte": self.config.stop_when_consensus_score_gte,
                "stop_when_no_role_changes_for_rounds": self.config.stop_when_no_role_changes_for_rounds,
                "stop_when_no_open_questions": self.config.stop_when_no_open_questions,
            },
        }

    def _process_instruction(self, protocol: str, meeting_phase: Dict[str, Any], l5_policy: Dict[str, Any]) -> str:
        protocol_instruction = PROCESS_INSTRUCTIONS.get(protocol, PROCESS_INSTRUCTIONS["chair_gated"])
        archetype_instruction = ARCHETYPE_INSTRUCTIONS.get(self.config.archetype, ARCHETYPE_INSTRUCTIONS["value_creating"])
        l5_levels = ", ".join(
            f"{name}={item['score']:.2f}/{item['level_label']}"
            for name, item in l5_policy["dimensions"].items()
        )
        l5_instruction = f"L5 强度解释：{l5_levels}。行为控制：{l5_policy['meeting_directive']}"
        phase_instruction = (
            f"当前会议阶段={meeting_phase['phase']}；目的：{meeting_phase['purpose']}；"
            f"本轮贡献要求：{meeting_phase['expected_contribution']}"
        )
        return f"{protocol_instruction} {archetype_instruction} {phase_instruction} {l5_instruction}"

    def _challenge_instruction(self, l5_policy: Dict[str, Any]) -> str:
        controls = l5_policy["behavior_controls"]
        challenge_mode = controls["challenge_mode"]
        if self.config.challenge_required or challenge_mode in {"required_challenge", "hard_challenge"}:
            return "本轮要求角色主动检查当前提案或他人推理中的薄弱假设；只有在没有更强证据时才维持原预测。"
        if challenge_mode in {"confirm_unless_contradiction", "soft_question"}:
            return "本轮不强制提出反对意见；如提出异议，应以温和、证据化方式说明，而不是为了制造冲突。"
        return "本轮不强制提出反对意见；角色可以选择确认、补充或温和修正当前预测。"

    def _artifact_values(self, events: Sequence[Dict[str, Any]], field: str) -> List[str]:
        values: List[str] = []
        for event in events:
            artifacts = event.get("meeting_artifacts", {})
            if not isinstance(artifacts, dict):
                continue
            raw = artifacts.get(field)
            if isinstance(raw, list):
                values.extend(str(item).strip() for item in raw if str(item).strip())
            elif isinstance(raw, str) and raw.strip():
                values.append(raw.strip())
        return values

    def _no_change_round_streak(self, history: Sequence[Dict[str, Any]]) -> int:
        rounds = sorted(
            {self._round_number(item) for item in history if self._round_number(item) > 0},
            reverse=True,
        )
        streak = 0
        for round_number in rounds:
            round_items = [item for item in history if self._round_number(item) == round_number]
            if any(item.get("changed_fields") for item in round_items):
                break
            streak += 1
        return streak

    def _round_number(self, event: Dict[str, Any]) -> int:
        try:
            return int(event.get("round", 0))
        except (TypeError, ValueError):
            return 0


def changed_fields(before: RoleDecision, after: RoleDecision) -> List[str]:
    """Return changed prediction fields between two role decisions."""
    fields = [
        "financing_intent",
        "completion_view",
        "predicted_deal_size_usd_m",
        "predicted_post_money_valuation_usd_m",
        "predicted_investor_ownership_pct",
        "predicted_deal_type",
        "valuation_direction",
        "satisfaction_score",
    ]
    return [field for field in fields if getattr(before, field) != getattr(after, field)]
