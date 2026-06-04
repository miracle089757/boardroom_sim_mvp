"""Interpret board-level L5 culture scores into concrete meeting behavior."""

from __future__ import annotations

from typing import Any, Dict


L5_CULTURE_DIMENSIONS = {
    "criticality": "批判性：是否主动挑战假设、证据解释和数值校准。",
    "creativity": "创造性：是否允许提出替代交易路径或不同融资情境。",
    "cohesiveness": "凝聚性：是否倾向维持董事会共同方向和关系稳定。",
    "openness_generosity": "开放慷慨：是否愿意吸收他人证据并给出善意解释。",
    "preparation_involvement": "准备与投入：是否充分使用可见字段、历史轨迹和角色规则。",
}

LEVEL_LABELS = {
    "very_low": "极低",
    "low": "低",
    "medium": "中等",
    "high": "高",
    "very_high": "极高",
}

DIMENSION_BEHAVIOR_RULES = {
    "criticality": {
        "very_low": "通常确认既有提案，除非可见证据出现明显矛盾。",
        "low": "可以提出温和疑问，但不主动制造对抗。",
        "medium": "至少检查一个关键假设是否过度依赖单一证据。",
        "high": "必须提出一个可证伪的薄弱假设、证据冲突或校准问题。",
        "very_high": "必须进行强质询，并要求对关键融资条款给出替代解释或保护方案。",
    },
    "creativity": {
        "very_low": "只讨论当前提案，不主动提出替代交易路径。",
        "low": "只在现有融资路径内做小幅修正。",
        "medium": "可以提出一个有限替代方案，例如融资规模或估值方向调整。",
        "high": "应提出至少一个可行替代交易情境，例如 bridge、flat follow-on 或 strategic round。",
        "very_high": "应主动提出多种交易结构或融资时机方案，并解释各自适用条件。",
    },
    "cohesiveness": {
        "very_low": "角色可以直接表达冲突，不必维护共同立场。",
        "low": "可以明确反对他人，但要指出分歧来源。",
        "medium": "表达分歧后，应说明它如何服务于董事会共同目标。",
        "high": "需要把异议包装为建设性修正，避免只做否定。",
        "very_high": "必须先承认共同目标，再提出修正；避免破坏会议关系。",
    },
    "openness_generosity": {
        "very_low": "只回应自己的证据和角色目标。",
        "low": "可以选择性回应他人观点。",
        "medium": "应回应至少一位此前发言者的关键证据。",
        "high": "必须承认或反驳此前至少一位角色的具体证据解释。",
        "very_high": "必须整合他人观点，说明接受、修正或拒绝的依据。",
    },
    "preparation_involvement": {
        "very_low": "允许依赖角色直觉，但不能编造不可见事实。",
        "low": "至少引用一个可见字段或角色规则。",
        "medium": "至少引用一个具体可见字段和一个角色启发式。",
        "high": "至少引用两个具体可见字段或历史锚点。",
        "very_high": "至少引用三个具体锚点，并说明它们如何共同改变或支持立场。",
    },
}


def level_for_score(score: float) -> str:
    """Map a normalized culture score to a stable qualitative level."""
    bounded = max(0.0, min(1.0, float(score)))
    if bounded < 0.20:
        return "very_low"
    if bounded < 0.40:
        return "low"
    if bounded < 0.60:
        return "medium"
    if bounded < 0.80:
        return "high"
    return "very_high"


def interpret_l5_culture(culture: Dict[str, float]) -> Dict[str, Any]:
    """Translate L5 numeric scores into levels, behavior rules, and controls."""
    dimensions: Dict[str, Dict[str, Any]] = {}
    for name, note in L5_CULTURE_DIMENSIONS.items():
        score = float(culture.get(name, 0.0) or 0.0)
        level = level_for_score(score)
        dimensions[name] = {
            "score": round(max(0.0, min(1.0, score)), 3),
            "level": level,
            "level_label": LEVEL_LABELS[level],
            "meaning": note,
            "behavior_rule": DIMENSION_BEHAVIOR_RULES[name][level],
        }

    controls = _derive_behavior_controls(dimensions)
    return {
        "definition": "L5 是董事会整体文化层，约束角色之间如何挑战、支持、让步和吸收证据；它不是单个角色的事实证据。",
        "dimensions": dimensions,
        "behavior_controls": controls,
        "meeting_directive": _meeting_directive(controls),
    }


def _derive_behavior_controls(dimensions: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    criticality = dimensions["criticality"]["level"]
    creativity = dimensions["creativity"]["level"]
    cohesiveness = dimensions["cohesiveness"]["level"]
    openness = dimensions["openness_generosity"]["level"]
    preparation = dimensions["preparation_involvement"]["level"]

    evidence_anchor_count = {
        "very_low": 0,
        "low": 1,
        "medium": 1,
        "high": 2,
        "very_high": 3,
    }[preparation]
    challenge_mode = {
        "very_low": "confirm_unless_contradiction",
        "low": "soft_question",
        "medium": "check_one_assumption",
        "high": "required_challenge",
        "very_high": "hard_challenge",
    }[criticality]
    alternative_options = {
        "very_low": "do_not_expand_option_space",
        "low": "minor_adjustments_only",
        "medium": "one_optional_alternative",
        "high": "one_required_alternative",
        "very_high": "multiple_required_alternatives",
    }[creativity]
    consensus_pressure = {
        "very_low": "open_conflict_allowed",
        "low": "direct_disagreement_allowed",
        "medium": "link_disagreement_to_common_goal",
        "high": "constructive_disagreement_required",
        "very_high": "common_goal_first_required",
    }[cohesiveness]
    prior_response = {
        "very_low": "self_evidence_only",
        "low": "optional_response",
        "medium": "respond_to_one_prior_claim",
        "high": "acknowledge_or_refute_prior_claim",
        "very_high": "integrate_prior_claims",
    }[openness]

    return {
        "challenge_mode": challenge_mode,
        "alternative_options": alternative_options,
        "consensus_pressure": consensus_pressure,
        "prior_response_requirement": prior_response,
        "minimum_evidence_anchors": evidence_anchor_count,
        "speech_length": "boardroom_substantive",
    }


def _meeting_directive(controls: Dict[str, Any]) -> str:
    parts = [
        f"挑战模式={controls['challenge_mode']}",
        f"替代方案要求={controls['alternative_options']}",
        f"共识压力={controls['consensus_pressure']}",
        f"回应前序发言={controls['prior_response_requirement']}",
        f"最少证据锚点={controls['minimum_evidence_anchors']}",
    ]
    return "；".join(parts) + "。"
