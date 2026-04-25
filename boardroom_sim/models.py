"""Data models for the boardroom simulation MVP."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


FinancingVote = Literal["approve", "renegotiate", "reject"]
ValuationDirection = Literal["up", "flat", "down", "unknown"]
CeoReplacementView = Literal["keep", "monitor", "replace"]


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float while providing a stable default for missing data."""
    if value is None or value == "":
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_str(value: Any, default: str = "unknown") -> str:
    """Convert a value to string while preserving a stable default for missing data."""
    if value is None or value == "":
        return default
    return str(value)


@dataclass
class BoardCase:
    """Represent one financing-round boardroom simulation case."""

    case_id: str
    company_name: str
    industry: str
    round_type: str
    deal_size_usd_m: float
    previous_deal_size_usd_m: float
    pre_money_valuation_usd_m: float
    post_money_valuation_usd_m: float
    previous_post_money_valuation_usd_m: float
    runway_months: float
    burn_multiple: float
    founder_equity_pct: float
    employee_growth_rate: float
    engineering_headcount_growth_rate: float
    tech_debt_risk: float
    ceo_performance_risk: float
    ceo_technical_alignment: float
    lead_investor_reputation: float
    lead_investor_conviction: float
    followon_fund_capacity: float
    market_temperature: str = "normal"
    business_status: str = "operating"
    notes: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoardCase":
        """Build a BoardCase from a loose JSON dictionary."""
        return cls(
            case_id=safe_str(data.get("case_id"), "case_unknown"),
            company_name=safe_str(data.get("company_name"), "unknown_company"),
            industry=safe_str(data.get("industry"), "unknown_industry"),
            round_type=safe_str(data.get("round_type"), "unknown_round"),
            deal_size_usd_m=safe_float(data.get("deal_size_usd_m")),
            previous_deal_size_usd_m=safe_float(data.get("previous_deal_size_usd_m")),
            pre_money_valuation_usd_m=safe_float(data.get("pre_money_valuation_usd_m")),
            post_money_valuation_usd_m=safe_float(data.get("post_money_valuation_usd_m")),
            previous_post_money_valuation_usd_m=safe_float(data.get("previous_post_money_valuation_usd_m")),
            runway_months=safe_float(data.get("runway_months"), 12.0),
            burn_multiple=safe_float(data.get("burn_multiple"), 1.0),
            founder_equity_pct=safe_float(data.get("founder_equity_pct"), 35.0),
            employee_growth_rate=safe_float(data.get("employee_growth_rate")),
            engineering_headcount_growth_rate=safe_float(data.get("engineering_headcount_growth_rate")),
            tech_debt_risk=safe_float(data.get("tech_debt_risk")),
            ceo_performance_risk=safe_float(data.get("ceo_performance_risk")),
            ceo_technical_alignment=safe_float(data.get("ceo_technical_alignment"), 0.5),
            lead_investor_reputation=safe_float(data.get("lead_investor_reputation"), 0.5),
            lead_investor_conviction=safe_float(data.get("lead_investor_conviction"), 0.5),
            followon_fund_capacity=safe_float(data.get("followon_fund_capacity"), 0.5),
            market_temperature=safe_str(data.get("market_temperature"), "normal"),
            business_status=safe_str(data.get("business_status"), "operating"),
            notes=data.get("notes", {}) if isinstance(data.get("notes", {}), dict) else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the case to a plain dictionary."""
        return asdict(self)

    def implied_dilution_pct(self) -> float:
        """Estimate new-money dilution as deal size divided by post-money valuation."""
        if self.post_money_valuation_usd_m <= 0:
            return 0.0
        return self.deal_size_usd_m / self.post_money_valuation_usd_m * 100.0

    def valuation_markup(self) -> Optional[float]:
        """Return current post-money valuation divided by previous post-money valuation."""
        if self.previous_post_money_valuation_usd_m <= 0:
            return None
        return self.post_money_valuation_usd_m / self.previous_post_money_valuation_usd_m

    def observed_valuation_direction(self) -> ValuationDirection:
        """Infer observed valuation direction from current and previous post-money valuation."""
        markup = self.valuation_markup()
        if markup is None:
            return "unknown"
        if markup >= 1.15:
            return "up"
        if markup <= 0.85:
            return "down"
        return "flat"


@dataclass
class RolePolicy:
    """Store one role's four-layer behavior specification."""

    role_name: str
    layer_1_goals: List[str]
    layer_2_attention_fields: List[str]
    layer_2_ignored_fields: List[str]
    layer_3_heuristics: List[str]
    layer_4_interaction_protocol: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize a role policy to a plain dictionary."""
        return asdict(self)


@dataclass
class RoleDecision:
    """Store one role's decision on the three focal events."""

    role_name: str
    financing_vote: FinancingVote
    valuation_direction: ValuationDirection
    ceo_replacement_view: CeoReplacementView
    satisfaction_score: float
    rationale: List[str]
    observed_fields: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize a role decision to a plain dictionary."""
        return asdict(self)


@dataclass
class TermSheetProposal:
    """Represent the negotiated financing proposal used by the simulator."""

    deal_size_usd_m: float
    valuation_direction: ValuationDirection
    implied_dilution_pct: float
    investor_protection_level: Literal["light", "standard", "strong"]
    tech_budget_protected: bool
    ceo_milestones_required: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize a term-sheet proposal to a plain dictionary."""
        return asdict(self)


@dataclass
class SimulationResult:
    """Represent the final output of one boardroom simulation case."""

    case_id: str
    company_name: str
    financing_decision: FinancingVote
    valuation_direction: ValuationDirection
    ceo_replacement_decision: CeoReplacementView
    role_decisions: Dict[str, Dict[str, Any]]
    proposal: Dict[str, Any]
    consensus_score: float
    deal_break_risk: Literal["low", "medium", "high"]
    governance_conflict_risk: Literal["low", "medium", "high"]
    trace: List[Dict[str, Any]]

    def to_dict(self, include_trace: bool = True) -> Dict[str, Any]:
        """Serialize the result and optionally omit the detailed trace."""
        data = asdict(self)
        if not include_trace:
            data.pop("trace", None)
        return data
