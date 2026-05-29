"""Configurable board process controls for simulation rounds."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, List, Sequence

from boardroom_sim.config import BoardProcessConfig
from boardroom_sim.models import RoleDecision


PROCESS_INSTRUCTIONS = {
    "chair_gated": "主席式流程：严格按既定顺序发言，角色应回应此前明确提出的证据或分歧。",
    "free_interjection": "开放式流程：本轮发言顺序会轮换，角色可以更主动挑战此前任何角色的证据解释。",
    "top3_dominance": "少数强势董事主导流程：影响权重较高的前三位角色更容易塑造最终结论。",
    "rubber_stamp": "橡皮图章流程：正式讨论很短，角色只有在发现明显预测错误时才应改变判断。",
}

ARCHETYPE_INSTRUCTIONS = {
    "aunt": "姑妈型董事会：会议默认确认管理层方案。除非可见证据明显反驳当前预测，否则发言应短、保守，并避免引入新的强对抗。",
    "barbarian": "野蛮人型董事会：会议默认从控制、监督和风险暴露出发。发言应主动指出证据缺口、估值风险或投资人保护不足。",
    "clan": "宗族型董事会：会议默认重视关系和共识。发言可以温和，但仍需说明共识是否由可见证据支撑，避免无证据从众。",
    "value_creating": "价值创造型董事会：会议应同时保持支持和挑战。发言需要把建设性异议、可见证据和最终预测校准连接起来。",
}

L5_CULTURE_DIMENSIONS = {
    "criticality": "批判性：是否主动挑战假设、证据解释和数值校准。",
    "creativity": "创造性：是否允许提出替代交易路径或不同融资情境。",
    "cohesiveness": "凝聚性：是否倾向维持董事会共同方向和关系稳定。",
    "openness_generosity": "开放慷慨：是否愿意吸收他人证据并给出善意解释。",
    "preparation_involvement": "准备与投入：是否充分使用可见字段、历史轨迹和角色规则。",
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
            if round_index > 0:
                return []
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
        return {
            "board_archetype": self.config.archetype,
            "board_archetype_label": self.config.archetype_label,
            "board_archetype_description": self.config.archetype_description,
            "discussion_protocol": protocol,
            "dominance_pattern": self.config.dominance_pattern,
            "culture_layer": self.config.culture_layer,
            "l5_culture": {
                "definition": "L5 是董事会整体文化层，约束角色之间如何挑战、支持、让步和吸收证据；它不是单个角色的事实证据。",
                "dimensions": dict(self.config.culture),
                "dimension_notes": dict(L5_CULTURE_DIMENSIONS),
            },
            "culture": dict(self.config.culture),
            "challenge_required": self.config.challenge_required,
            "memory_scope": self.config.memory_scope,
            "memory_window": self.config.memory_window,
            "round_number": round_index + 1,
            "speaking_order_this_round": list(speakers),
            "current_role": role_name,
            "current_role_effective_weight": effective_weights.get(role_name, 1.0),
            "process_instruction": self._process_instruction(protocol),
            "challenge_instruction": self._challenge_instruction(),
        }

    def _process_instruction(self, protocol: str) -> str:
        protocol_instruction = PROCESS_INSTRUCTIONS.get(protocol, PROCESS_INSTRUCTIONS["chair_gated"])
        archetype_instruction = ARCHETYPE_INSTRUCTIONS.get(self.config.archetype, ARCHETYPE_INSTRUCTIONS["value_creating"])
        culture = self.config.culture
        l5_instruction = (
            f"L5 文化层参数：批判性={culture.get('criticality', 0):.2f}，"
            f"创造性={culture.get('creativity', 0):.2f}，"
            f"凝聚性={culture.get('cohesiveness', 0):.2f}，"
            f"开放慷慨={culture.get('openness_generosity', 0):.2f}，"
            f"准备投入={culture.get('preparation_involvement', 0):.2f}。"
        )
        return f"{protocol_instruction} {archetype_instruction} {l5_instruction}"

    def _challenge_instruction(self) -> str:
        criticality = self.config.culture.get("criticality", 0.0)
        if self.config.challenge_required or criticality >= 0.65:
            return "本轮要求角色主动检查当前提案或他人推理中的薄弱假设；只有在没有更强证据时才维持原预测。"
        if criticality <= 0.35:
            return "本轮不强制提出反对意见；如提出异议，应以温和、证据化方式说明，而不是为了制造冲突。"
        return "本轮不强制提出反对意见；角色可以选择确认、补充或温和修正当前预测。"


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
