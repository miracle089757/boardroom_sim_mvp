"""Experiment configuration loading for the boardroom simulation."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import tomllib
except ModuleNotFoundError as exc:  # pragma: no cover - Python < 3.11 fallback.
    raise RuntimeError("Python 3.11+ is required for TOML config loading via tomllib.") from exc


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "configs" / "boardroom_default.toml"


DEFAULT_ROLE_ORDER = [
    "Founder_CEO",
    "CTO",
    "Lead_VC_Director",
    "Followon_VC_Director",
]

DEFAULT_ROLE_WEIGHTS = {
    "Founder_CEO": 2.0,
    "CTO": 0.5,
    "Lead_VC_Director": 3.0,
    "Followon_VC_Director": 1.5,
}

DEFAULT_ROUND_TASKS = [
    "第 1 轮：指出当前聚合提案或董事会上下文里最薄弱的一个假设，并用你的可见字段、角色规则或对可见证据的更强解释提出挑战。",
    "第 2 轮：根据上一轮挑战重新评估预测；只更新证据权重、交易类型校准或数值校准确实发生变化的字段。",
    "第 3 轮：给出最终预测；预测准确性优先于谈判姿态，除非能改善预测，否则不要引入新的让步。",
]

DEFAULT_BOARD_CULTURE = {
    "criticality": 0.75,
    "creativity": 0.70,
    "cohesiveness": 0.70,
    "openness_generosity": 0.80,
    "preparation_involvement": 0.85,
}

BOARD_ARCHETYPE_ALIASES = {
    "barbarian_control": "barbarian",
    "clan_consensus": "clan",
}

BOARD_ARCHETYPE_PROFILES: Dict[str, Dict[str, Any]] = {
    "aunt": {
        "label": "姑妈型董事会",
        "description": "形式化、被动确认、管理层主导的董事会。L5 文化层鼓励较少挑战，讨论更像确认既有方案。",
        "culture": {
            "criticality": 0.15,
            "creativity": 0.20,
            "cohesiveness": 0.45,
            "openness_generosity": 0.25,
            "preparation_involvement": 0.25,
        },
        "protocol": "rubber_stamp",
        "dominance_pattern": "management_dominant",
        "challenge_required": False,
        "memory_scope": "limited",
        "memory_window": 3,
        "role_weight_multipliers": {
            "Founder_CEO": 1.25,
            "CTO": 0.85,
            "Lead_VC_Director": 0.80,
            "Followon_VC_Director": 0.80,
        },
    },
    "barbarian": {
        "label": "野蛮人型董事会",
        "description": "控制、监督和低信任导向的董事会。L5 文化层强调高批判、低凝聚，强势投资人更容易主导结论。",
        "culture": {
            "criticality": 0.90,
            "creativity": 0.35,
            "cohesiveness": 0.25,
            "openness_generosity": 0.35,
            "preparation_involvement": 0.80,
        },
        "protocol": "top3_dominance",
        "dominance_pattern": "investor_dominant",
        "challenge_required": True,
        "memory_scope": "full",
        "memory_window": 10,
        "role_weight_multipliers": {
            "Founder_CEO": 0.80,
            "CTO": 0.70,
            "Lead_VC_Director": 1.50,
            "Followon_VC_Director": 1.15,
        },
    },
    "clan": {
        "label": "宗族型董事会",
        "description": "高亲近、高信任、重视和谐的董事会。L5 文化层提高凝聚和开放，但降低强制性挑战。",
        "culture": {
            "criticality": 0.30,
            "creativity": 0.55,
            "cohesiveness": 0.90,
            "openness_generosity": 0.75,
            "preparation_involvement": 0.60,
        },
        "protocol": "chair_gated",
        "dominance_pattern": "consensus_dominant",
        "challenge_required": False,
        "memory_scope": "full",
        "memory_window": 10,
        "role_weight_multipliers": {
            "Founder_CEO": 1.15,
            "CTO": 1.00,
            "Lead_VC_Director": 0.95,
            "Followon_VC_Director": 0.95,
        },
    },
    "value_creating": {
        "label": "价值创造型董事会",
        "description": "兼具监督和支持的董事会。L5 文化层鼓励充分准备、开放异议、建设性批判和共同校准预测。",
        "culture": {
            "criticality": 0.75,
            "creativity": 0.70,
            "cohesiveness": 0.70,
            "openness_generosity": 0.80,
            "preparation_involvement": 0.85,
        },
        "protocol": "free_interjection",
        "dominance_pattern": "balanced",
        "challenge_required": True,
        "memory_scope": "full",
        "memory_window": 10,
        "role_weight_multipliers": {},
    },
}


@dataclass
class BoardProcessConfig:
    """Board-level process knobs that control how agents interact."""

    archetype: str = "value_creating"
    archetype_label: str = "价值创造型董事会"
    archetype_description: str = BOARD_ARCHETYPE_PROFILES["value_creating"]["description"]
    culture_layer: str = "L5"
    culture: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_BOARD_CULTURE))
    protocol: str = "free_interjection"
    dominance_pattern: str = "balanced"
    challenge_required: bool = True
    memory_scope: str = "full"
    memory_window: int = 10
    role_weight_multipliers: Dict[str, float] = field(default_factory=dict)


@dataclass
class ExperimentConfig:
    """Runtime knobs that should vary by experiment instead of code edits."""

    name: str = "boardroom_default"
    config_path: Optional[Path] = None
    role_policy_dir: Path = PROJECT_ROOT / "policies" / "roles"
    prompts_dir: Path = PROJECT_ROOT / "prompts"
    role_order: List[str] = field(default_factory=lambda: list(DEFAULT_ROLE_ORDER))
    role_weights: Dict[str, float] = field(default_factory=lambda: dict(DEFAULT_ROLE_WEIGHTS))
    bargaining_rounds: int = 3
    history_limit: int = 10
    discussion_paradigm: str = "memory"
    response_generator: str = "critical"
    decision_protocol: str = "weighted_vote"
    round_tasks: List[str] = field(default_factory=lambda: list(DEFAULT_ROUND_TASKS))
    board_process: BoardProcessConfig = field(default_factory=BoardProcessConfig)
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_manifest_dict(self) -> Dict[str, Any]:
        """Serialize config fields for experiment manifests."""
        data = asdict(self)
        data["config_path"] = str(self.config_path) if self.config_path else None
        data["role_policy_dir"] = str(self.role_policy_dir)
        data["prompts_dir"] = str(self.prompts_dir)
        data.pop("raw", None)
        return data


def load_experiment_config(path: Optional[Path] = None) -> ExperimentConfig:
    """Load a boardroom experiment config, falling back to built-in defaults."""
    config_path = path or (DEFAULT_CONFIG_PATH if DEFAULT_CONFIG_PATH.exists() else None)
    if config_path is None:
        return ExperimentConfig()

    resolved_path = _resolve_path(config_path)
    with resolved_path.open("rb") as handle:
        raw = tomllib.load(handle)

    experiment = raw.get("experiment", {})
    paths = raw.get("paths", {})
    agents = raw.get("agents", {})
    board = raw.get("board", {})
    discussion = raw.get("discussion", {})
    decision = raw.get("decision", {})

    role_order = _string_list(agents.get("role_order"), DEFAULT_ROLE_ORDER)
    role_weights = {
        str(role): float(weight)
        for role, weight in dict(decision.get("weights", DEFAULT_ROLE_WEIGHTS)).items()
    }
    round_tasks = _string_list(discussion.get("round_tasks"), DEFAULT_ROUND_TASKS)
    board_process = _board_process_from_sections(board, discussion)

    return ExperimentConfig(
        name=str(experiment.get("name", resolved_path.stem)),
        config_path=resolved_path,
        role_policy_dir=_resolve_path(paths.get("role_policy_dir", "policies/roles")),
        prompts_dir=_resolve_path(paths.get("prompts_dir", "prompts")),
        role_order=role_order,
        role_weights=role_weights,
        bargaining_rounds=int(experiment.get("bargaining_rounds", 3)),
        history_limit=int(experiment.get("history_limit", 10)),
        discussion_paradigm=str(discussion.get("paradigm", "memory")),
        response_generator=str(discussion.get("response_generator", "critical")),
        decision_protocol=str(decision.get("protocol", "weighted_vote")),
        round_tasks=round_tasks,
        board_process=board_process,
        raw=raw,
    )


def _resolve_path(value: Any) -> Path:
    path = value if isinstance(value, Path) else Path(str(value))
    return path if path.is_absolute() else PROJECT_ROOT / path


def _string_list(value: Any, default: List[str]) -> List[str]:
    if not isinstance(value, list):
        return list(default)
    cleaned = [str(item) for item in value if str(item)]
    return cleaned or list(default)


def canonicalize_board_archetype(value: Any) -> str:
    """Return the canonical board archetype id used by process profiles."""
    raw = str(value or "value_creating").strip().lower()
    normalized = BOARD_ARCHETYPE_ALIASES.get(raw, raw)
    if normalized not in BOARD_ARCHETYPE_PROFILES:
        return "value_creating"
    return normalized


def _board_process_from_sections(board: Dict[str, Any], discussion: Dict[str, Any]) -> BoardProcessConfig:
    archetype = canonicalize_board_archetype(board.get("archetype", "value_creating"))
    profile = BOARD_ARCHETYPE_PROFILES[archetype]
    culture = _merge_float_dict(profile["culture"], board.get("culture"))
    role_weight_multipliers = _merge_float_dict(
        profile.get("role_weight_multipliers", {}),
        board.get("role_weight_multipliers"),
    )

    return BoardProcessConfig(
        archetype=archetype,
        archetype_label=str(profile["label"]),
        archetype_description=str(profile["description"]),
        culture_layer="L5",
        culture=culture,
        protocol=str(discussion.get("protocol", profile["protocol"])),
        dominance_pattern=str(discussion.get("dominance_pattern", profile["dominance_pattern"])),
        challenge_required=_bool_value(discussion.get("challenge_required"), bool(profile["challenge_required"])),
        memory_scope=str(discussion.get("memory_scope", profile["memory_scope"])),
        memory_window=_int_value(discussion.get("memory_window"), int(profile["memory_window"])),
        role_weight_multipliers=role_weight_multipliers,
    )


def _float_dict(value: Any, default: Dict[str, float]) -> Dict[str, float]:
    if not isinstance(value, dict):
        return dict(default)
    result: Dict[str, float] = {}
    for key, item in value.items():
        try:
            result[str(key)] = float(item)
        except (TypeError, ValueError):
            continue
    return result or dict(default)


def _merge_float_dict(default: Dict[str, float], override: Any) -> Dict[str, float]:
    result = dict(default)
    if not isinstance(override, dict):
        return result
    for key, item in override.items():
        try:
            result[str(key)] = float(item)
        except (TypeError, ValueError):
            continue
    return result


def _bool_value(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y", "on"}:
        return True
    if text in {"false", "0", "no", "n", "off"}:
        return False
    return default


def _int_value(value: Any, default: int) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
