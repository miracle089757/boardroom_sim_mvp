"""Data models for the boardroom simulation MVP."""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Literal, Optional


FinancingIntent = Literal["raise_now", "wait", "avoid"]
DealCompletionView = Literal["likely_complete", "uncertain", "unlikely_complete"]
ValuationDirection = Literal["up", "flat", "down", "unknown"]
RiskLevel = Literal["low", "medium", "high"]


def is_missing(value: Any) -> bool:
    """Return whether a loose JSON/Python value should be treated as missing."""
    return value is None or value == "" or (isinstance(value, float) and math.isnan(value))


def first_present(*values: Any) -> Any:
    """Return the first value that is not missing."""
    for value in values:
        if not is_missing(value):
            return value
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float while providing a stable default for missing data."""
    if is_missing(value):
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def safe_optional_float(value: Any) -> Optional[float]:
    """Convert a value to float while preserving missing data as None."""
    if is_missing(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int while providing a stable default for missing data."""
    if is_missing(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def safe_optional_int(value: Any) -> Optional[int]:
    """Convert a value to int while preserving missing data as None."""
    if is_missing(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def safe_bool(value: Any, default: bool = False) -> bool:
    """Convert a loose value to bool while handling missing data."""
    if is_missing(value):
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return default


def safe_str(value: Any, default: str = "unknown") -> str:
    """Convert a value to string while preserving a stable default for missing data."""
    if is_missing(value):
        return default
    return str(value)


def safe_str_list(value: Any) -> List[str]:
    """Convert a loose value into a clean list of strings."""
    if is_missing(value):
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, tuple) or isinstance(value, set):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def safe_dict_list(value: Any) -> List[Dict[str, Any]]:
    """Convert a loose value into a list of dictionaries."""
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def safe_direction(value: Any) -> ValuationDirection:
    """Normalize a valuation direction label."""
    text = safe_str(value, "unknown").strip().lower().replace(" round", "")
    if text in {"up", "flat", "down", "unknown"}:
        return text  # type: ignore[return-value]
    return "unknown"


@dataclass
class BoardCase:
    """Represent one point-in-time boardroom case before a real VC transaction."""

    case_id: str  # 模拟案例唯一标识，通常由 company_id 和真实目标 deal_id 拼接生成。
    company_id: str  # PitchBook 公司 ID，用于关联公司、行业、员工、人员等表。
    target_deal_id: str  # 被隐藏的真实目标交易 ID，仅用于追踪和评测，不进入角色可见字段。
    company_label: str  # 公司展示标签；样本没有真实公司名时使用 company_id 代替。
    decision_date: str  # 决策时点；第一版正样本中等于真实融资发生日期，但不说明真实交易已发生。
    business_status: str  # 公司经营状态；注意该字段可能是 PitchBook 当前快照。
    company_financing_status: str  # 公司融资状态；注意该字段可能是 PitchBook 当前快照。
    ownership_status: str  # 公司所有权状态；注意该字段可能是 PitchBook 当前快照。
    year_founded: Optional[int]  # 公司成立年份；缺失时为 None。
    company_age_at_decision_years: Optional[float]  # 决策时点公司的年龄；缺失时为 None。
    primary_industry: str  # 公司主行业，来自 companyindustryrelation 的主行业记录。
    industry_group: str  # 公司所属行业组。
    industry_sector: str  # 公司所属行业部门。
    verticals: List[str]  # 公司垂直赛道标签列表。
    keywords: str  # 公司关键词，描述产品、技术、商业模式或主题标签。
    description: str  # 公司业务描述文本。
    prior_vc_deal_count: int  # 决策时点之前同一公司已发生的 VC 融资次数。
    prior_deal_date: str  # 上一笔 VC 融资日期。
    prior_deal_type: str  # 上一笔 VC 融资类型。
    prior_vc_round: str  # 上一笔 VC 轮次标签。
    prior_deal_size_usd_m: Optional[float]  # 上一笔 VC 融资金额，单位为百万美元；缺失时为 None。
    prior_pre_money_valuation_usd_m: Optional[float]  # 上一笔 VC 融资投前估值，单位为百万美元；缺失时为 None。
    prior_post_money_valuation_usd_m: Optional[float]  # 上一笔 VC 融资投后估值，单位为百万美元；缺失时为 None。
    prior_raised_to_date_usd_m: Optional[float]  # 上一笔融资后可观测的累计融资额，单位为百万美元；缺失时为 None。
    prior_investor_ownership_pct: Optional[float]  # 上一笔融资后的投资人持股比例；缺失时为 None。
    months_since_prior_deal: Optional[float]  # 决策时点距离上一笔 VC 融资的月份数；缺失时为 None。
    prior_valuation_markup_multiple: Optional[float]  # 上一笔估值相对再上一笔估值的倍数；缺失时为 None。
    prior_valuation_direction_label: ValuationDirection  # 上一笔融资的历史估值方向。
    prior_investor_count: Optional[int]  # 上一笔融资投资人总数；缺失时为 None。
    prior_new_investor_count: Optional[int]  # 上一笔融资新投资人数量；缺失时为 None。
    prior_followon_investor_count: Optional[int]  # 上一笔融资跟投投资人数量；缺失时为 None。
    prior_lead_investor_count: int  # 上一笔融资领投方数量。
    prior_lead_investor_types: List[str]  # 上一笔融资领投方类型列表。
    prior_lead_investor_amount_share: Optional[float]  # 上一笔融资领投方披露金额占比；缺失时为 None。
    prior_lead_preferred_deal_size_min_usd_m: Optional[float]  # 上一笔领投方偏好的单笔投资额下限；缺失时为 None。
    prior_lead_preferred_deal_size_max_usd_m: Optional[float]  # 上一笔领投方偏好的单笔投资额上限；缺失时为 None。
    prior_lead_preferred_company_valuation_min_usd_m: Optional[float]  # 上一笔领投方偏好的公司估值下限；缺失时为 None。
    prior_lead_preferred_company_valuation_max_usd_m: Optional[float]  # 上一笔领投方偏好的公司估值上限；缺失时为 None。
    prior_company_deal_history: List[Dict[str, Any]]  # 决策日前同公司历史 VC-like 交易记录，按时间升序截断保留。
    prior_lead_investor_deal_history: List[Dict[str, Any]]  # 本轮领投方在决策日前的历史投资记录。
    prior_followon_investor_deal_history: List[Dict[str, Any]]  # 本轮跟投/非领投方在决策日前的历史投资记录。
    employee_count_at_decision: Optional[float]  # 决策时点之前最近一次可观测员工数；缺失时为 None。
    previous_employee_count: Optional[float]  # 决策时点之前上一条员工数记录；缺失时为 None。
    employee_growth_rate: Optional[float]  # 员工增长率，由最近员工数和上一条员工数计算；缺失时为 None。
    engineering_role_count: int  # 决策时点可识别的工程/技术岗位人数。
    executive_role_count: int  # 决策时点可识别的高管岗位人数。
    founder_count: int  # 决策时点可识别的创始人数量。
    current_ceo_count: int  # 决策时点可识别的在任 CEO 数量。
    current_ceo_is_founder: bool  # 决策时点 CEO 是否可识别为 founder-CEO。
    board_member_count: int  # 决策时点可识别的董事会成员数量。
    investor_board_member_count: int  # 决策时点代表投资人的董事会成员数量。
    competitor_count: int  # PitchBook 记录的竞争对手数量。
    similar_company_count: int  # PitchBook 算法相似公司数量。
    notes: Dict[str, Any] = field(default_factory=dict)  # 附加元数据和真实标签；不进入 Agent 可见字段。

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BoardCase":
        """Build a BoardCase from a loose JSON dictionary."""
        return cls(
            case_id=safe_str(data.get("case_id"), "case_unknown"),
            company_id=safe_str(data.get("company_id"), "unknown_company"),
            target_deal_id=safe_str(data.get("target_deal_id") or data.get("deal_id"), "unknown_deal"),
            company_label=safe_str(data.get("company_label") or data.get("company_name"), "unknown_company"),
            decision_date=safe_str(data.get("decision_date") or data.get("deal_date"), ""),
            business_status=safe_str(data.get("business_status"), "unknown"),
            company_financing_status=safe_str(data.get("company_financing_status"), "unknown"),
            ownership_status=safe_str(data.get("ownership_status"), "unknown"),
            year_founded=safe_optional_int(data.get("year_founded")),
            company_age_at_decision_years=safe_optional_float(
                first_present(data.get("company_age_at_decision_years"), data.get("company_age_at_deal_years"))
            ),
            primary_industry=safe_str(data.get("primary_industry") or data.get("industry"), "unknown_industry"),
            industry_group=safe_str(data.get("industry_group"), "unknown"),
            industry_sector=safe_str(data.get("industry_sector"), "unknown"),
            verticals=safe_str_list(data.get("verticals")),
            keywords=safe_str(data.get("keywords"), ""),
            description=safe_str(data.get("description"), ""),
            prior_vc_deal_count=safe_int(data.get("prior_vc_deal_count")),
            prior_deal_date=safe_str(data.get("prior_deal_date"), ""),
            prior_deal_type=safe_str(data.get("prior_deal_type"), "unknown_prior_deal_type"),
            prior_vc_round=safe_str(data.get("prior_vc_round"), "unknown_prior_vc_round"),
            prior_deal_size_usd_m=safe_optional_float(
                first_present(data.get("prior_deal_size_usd_m"), data.get("previous_deal_size_usd_m"))
            ),
            prior_pre_money_valuation_usd_m=safe_optional_float(data.get("prior_pre_money_valuation_usd_m")),
            prior_post_money_valuation_usd_m=safe_optional_float(
                first_present(data.get("prior_post_money_valuation_usd_m"), data.get("previous_post_money_valuation_usd_m"))
            ),
            prior_raised_to_date_usd_m=safe_optional_float(data.get("prior_raised_to_date_usd_m")),
            prior_investor_ownership_pct=safe_optional_float(data.get("prior_investor_ownership_pct")),
            months_since_prior_deal=safe_optional_float(data.get("months_since_prior_deal")),
            prior_valuation_markup_multiple=safe_optional_float(data.get("prior_valuation_markup_multiple")),
            prior_valuation_direction_label=safe_direction(data.get("prior_valuation_direction_label")),
            prior_investor_count=safe_optional_int(data.get("prior_investor_count")),
            prior_new_investor_count=safe_optional_int(data.get("prior_new_investor_count")),
            prior_followon_investor_count=safe_optional_int(data.get("prior_followon_investor_count")),
            prior_lead_investor_count=safe_int(data.get("prior_lead_investor_count")),
            prior_lead_investor_types=safe_str_list(data.get("prior_lead_investor_types")),
            prior_lead_investor_amount_share=safe_optional_float(data.get("prior_lead_investor_amount_share")),
            prior_lead_preferred_deal_size_min_usd_m=safe_optional_float(data.get("prior_lead_preferred_deal_size_min_usd_m")),
            prior_lead_preferred_deal_size_max_usd_m=safe_optional_float(data.get("prior_lead_preferred_deal_size_max_usd_m")),
            prior_lead_preferred_company_valuation_min_usd_m=safe_optional_float(
                data.get("prior_lead_preferred_company_valuation_min_usd_m")
            ),
            prior_lead_preferred_company_valuation_max_usd_m=safe_optional_float(
                data.get("prior_lead_preferred_company_valuation_max_usd_m")
            ),
            prior_company_deal_history=safe_dict_list(data.get("prior_company_deal_history")),
            prior_lead_investor_deal_history=safe_dict_list(data.get("prior_lead_investor_deal_history")),
            prior_followon_investor_deal_history=safe_dict_list(data.get("prior_followon_investor_deal_history")),
            employee_count_at_decision=safe_optional_float(
                first_present(data.get("employee_count_at_decision"), data.get("employee_count_at_deal"))
            ),
            previous_employee_count=safe_optional_float(data.get("previous_employee_count")),
            employee_growth_rate=safe_optional_float(data.get("employee_growth_rate")),
            engineering_role_count=safe_int(data.get("engineering_role_count")),
            executive_role_count=safe_int(data.get("executive_role_count")),
            founder_count=safe_int(data.get("founder_count")),
            current_ceo_count=safe_int(data.get("current_ceo_count")),
            current_ceo_is_founder=safe_bool(data.get("current_ceo_is_founder")),
            board_member_count=safe_int(data.get("board_member_count")),
            investor_board_member_count=safe_int(data.get("investor_board_member_count")),
            competitor_count=safe_int(data.get("competitor_count")),
            similar_company_count=safe_int(data.get("similar_company_count")),
            notes=data.get("notes", {}) if isinstance(data.get("notes", {}), dict) else {},
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the case to a plain dictionary."""
        return asdict(self)

    def prior_valuation_markup(self) -> Optional[float]:
        """Return the latest historical valuation markup when available."""
        if self.prior_valuation_markup_multiple is not None and self.prior_valuation_markup_multiple > 0:
            return self.prior_valuation_markup_multiple
        return None

    def prior_valuation_direction(self) -> ValuationDirection:
        """Return the latest historical valuation direction."""
        if self.prior_valuation_direction_label != "unknown":
            return self.prior_valuation_direction_label
        markup = self.prior_valuation_markup()
        if markup is None:
            return "unknown"
        if markup >= 1.15:
            return "up"
        if markup <= 0.85:
            return "down"
        return "flat"

    def estimated_dilution_pct(self, deal_size_usd_m: float) -> Optional[float]:
        """Estimate dilution using predicted new money and prior post-money valuation."""
        if deal_size_usd_m <= 0 or self.prior_post_money_valuation_usd_m is None or self.prior_post_money_valuation_usd_m <= 0:
            return None
        return deal_size_usd_m / (self.prior_post_money_valuation_usd_m + deal_size_usd_m) * 100.0


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
    """Store one role's prediction for a point-in-time financing decision."""

    role_name: str
    financing_intent: FinancingIntent
    completion_view: DealCompletionView
    predicted_deal_size_usd_m: float
    predicted_post_money_valuation_usd_m: float
    predicted_investor_ownership_pct: float
    predicted_deal_type: str
    valuation_direction: ValuationDirection
    satisfaction_score: float
    rationale: List[str]
    observed_fields: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        """Serialize a role decision to a plain dictionary."""
        return asdict(self)


@dataclass
class TermSheetProposal:
    """Represent the negotiated financing proposal predicted by the simulator."""

    recommended_deal_size_usd_m: float
    recommended_post_money_valuation_usd_m: float
    recommended_investor_ownership_pct: float
    recommended_deal_type: str
    valuation_direction: ValuationDirection
    estimated_dilution_pct: Optional[float]
    investor_protection_level: Literal["light", "standard", "strong"]
    tech_budget_protected: bool

    def to_dict(self) -> Dict[str, Any]:
        """Serialize a term-sheet proposal to a plain dictionary."""
        return asdict(self)


@dataclass
class SimulationResult:
    """Represent the final output of one boardroom simulation case."""

    case_id: str
    company_name: str
    financing_initiation_decision: FinancingIntent
    financing_completion_view: DealCompletionView
    predicted_deal_size_usd_m: float
    predicted_post_money_valuation_usd_m: float
    predicted_investor_ownership_pct: float
    predicted_deal_type: str
    valuation_direction: ValuationDirection
    role_decisions: Dict[str, Dict[str, Any]]
    proposal: Dict[str, Any]
    consensus_score: float
    deal_break_risk: RiskLevel
    labels: Dict[str, Any]
    trace: List[Dict[str, Any]]

    def to_dict(self, include_trace: bool = True) -> Dict[str, Any]:
        """Serialize the result and optionally omit the detailed trace."""
        data = asdict(self)
        if not include_trace:
            data.pop("trace", None)
        return data
