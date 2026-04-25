"""Role policies translated from the agent role-design document."""

from __future__ import annotations

from typing import Dict, List

from boardroom_sim.models import RolePolicy


def build_role_policies() -> Dict[str, RolePolicy]:
    """Create the four strict MVP role policies with the required four layers."""
    policies = [
        RolePolicy(
            role_name="Founder_CEO",
            layer_1_goals=[
                "Maximize long-term company value.",
                "Preserve founder control and avoid excessive dilution.",
                "Maintain execution freedom after financing.",
            ],
            layer_2_attention_fields=[
                "deal_size_usd_m",
                "pre_money_valuation_usd_m",
                "post_money_valuation_usd_m",
                "previous_post_money_valuation_usd_m",
                "round_type",
                "founder_equity_pct",
                "runway_months",
                "employee_growth_rate",
            ],
            layer_2_ignored_fields=[
                "investor_internal_aum",
                "investor_portfolio_allocation",
                "horizontal_company_comps_not_tied_to_current_round",
            ],
            layer_3_heuristics=[
                "Control redline dominates valuation preference.",
                "Valuation markup is treated as a status and market signal.",
                "Dilution can be accepted when financing materially improves runway.",
                "Founder commitments are sticky once public positions are stated.",
            ],
            layer_4_interaction_protocol={
                "speaking_order": 1,
                "board_vote": "founder vote or agenda-setting influence",
                "information_behavior": "selectively discloses upside and execution needs",
                "stickiness": "high",
            },
        ),
        RolePolicy(
            role_name="CTO",
            layer_1_goals=[
                "Protect engineering team health.",
                "Protect technical feasibility and architecture quality.",
                "Protect personal technical reputation.",
            ],
            layer_2_attention_fields=[
                "engineering_headcount_growth_rate",
                "employee_growth_rate",
                "tech_debt_risk",
                "ceo_technical_alignment",
                "industry",
                "runway_months",
            ],
            layer_2_ignored_fields=[
                "liquidation_preference",
                "anti_dilution_terms",
                "investor_portfolio_internal_data",
                "headquarter_city",
            ],
            layer_3_heuristics=[
                "Oppose engineering shrinkage or unfunded technical commitments.",
                "Reject external technical override that threatens architecture.",
                "Protect talent budget before short-term financial cosmetics.",
                "Technical prerequisites should be clarified before fundraising claims.",
            ],
            layer_4_interaction_protocol={
                "speaking_order": 2,
                "board_vote": "normally advisory unless founder-like technical cofounder",
                "information_behavior": "must disclose technical debt and recruiting difficulty",
                "stickiness": "high for technical commitments",
            },
        ),
        RolePolicy(
            role_name="Lead_VC_Director",
            layer_1_goals=[
                "Maximize exit multiple.",
                "Secure favorable financing terms.",
                "Protect portfolio markup and downside.",
            ],
            layer_2_attention_fields=[
                "post_money_valuation_usd_m",
                "previous_post_money_valuation_usd_m",
                "deal_size_usd_m",
                "burn_multiple",
                "runway_months",
                "lead_investor_conviction",
                "lead_investor_reputation",
                "ceo_performance_risk",
            ],
            layer_2_ignored_fields=[
                "deep_product_architecture_detail",
                "individual_engineering_workflow",
                "minor_workforce_analytics",
            ],
            layer_3_heuristics=[
                "Downside protection has priority over unpriced upside.",
                "Valuation must be disciplined against growth and burn risk.",
                "Fund concentration and next-round path must remain clear.",
                "Reserve influence over management change when execution risk is high.",
            ],
            layer_4_interaction_protocol={
                "speaking_order": 3,
                "board_vote": "1-2 board seats and high financing influence",
                "information_behavior": "has market intelligence and term-sheet leverage",
                "stickiness": "medium to high due to LP and fund constraints",
            },
        ),
        RolePolicy(
            role_name="Followon_VC_Director",
            layer_1_goals=[
                "Protect pro-rata rights.",
                "Maintain investment IRR.",
                "Use lead investor signal while managing diversification.",
            ],
            layer_2_attention_fields=[
                "deal_size_usd_m",
                "lead_investor_reputation",
                "lead_investor_conviction",
                "post_money_valuation_usd_m",
                "previous_post_money_valuation_usd_m",
                "followon_fund_capacity",
            ],
            layer_2_ignored_fields=[
                "product_architecture_detail",
                "term_sheet_drafting_detail",
                "minor_operational_metrics",
            ],
            layer_3_heuristics=[
                "Default to follow-on unless explicit red flags appear.",
                "Protect pro-rata and anti-dilution position.",
                "Follow the lead investor signal but do not replace the lead.",
                "Ticket size and sector boundary constrain participation.",
            ],
            layer_4_interaction_protocol={
                "speaking_order": 4,
                "board_vote": "0-1 board seat and limited blocking power",
                "information_behavior": "less direct market information than lead investor",
                "stickiness": "prior follow-on intent becomes a default",
            },
        ),
    ]
    return {policy.role_name: policy for policy in policies}


def ordered_role_names() -> List[str]:
    """Return the fixed speaking order specified by the role-design document."""
    return ["Founder_CEO", "CTO", "Lead_VC_Director", "Followon_VC_Director"]
