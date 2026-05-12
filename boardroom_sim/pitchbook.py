"""Build point-in-time boardroom cases from the PitchBook sample workbook."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import pandas as pd

from boardroom_sim.models import BoardCase, ValuationDirection


VC_DEAL_TYPES = {"Early Stage VC", "Later Stage VC", "Seed Round"}
CEO_TITLES = {"chief executive officer", "ceo"}
ENGINEERING_TITLE_TOKENS = (
    "chief technology officer",
    "cto",
    "vp eng",
    "vice president engineering",
    "vice president, engineering",
    "director of eng",
    "director, engineering",
    "software engineer",
    "engineer",
    "engineering",
    "swe",
)


def build_cases_from_pitchbook(
    path: Path,
    limit: Optional[int] = None,
    history_limit: Optional[int] = 10,
) -> List[BoardCase]:
    """Read the PitchBook workbook and convert eligible VC rounds into point-in-time cases."""
    tables = pd.read_excel(path, sheet_name=None)
    deal_df = _clean_table(tables["deal"])
    financing_deals = _select_vc_deals(deal_df)
    history_limit = _normalize_history_limit(history_limit)

    # Use every observable VC-like transaction as a positive event sample. Missing numeric labels
    # are preserved as None and skipped by the relevant evaluation metrics.
    case_deals = financing_deals.copy()
    case_deals = case_deals.sort_values(["companyid", "dealdate", "dealid"], na_position="last")
    if limit is not None:
        case_deals = case_deals.head(limit)

    company_by_id = _index_by_id(_clean_table(tables["company"]), "companyid")
    industry_by_company = _primary_industry_by_company(_clean_table(tables["companyindustryrelation"]))
    verticals_by_company = _list_by_company(_clean_table(tables["companyverticalrelation"]), "vertical")
    investor_by_id = _index_by_id(_clean_table(tables["investor"]), "investorid")
    deal_investors = _clean_table(tables["dealinvestorrelation"])
    employee_history = _clean_table(tables["companyemployeehistoryrelation"])
    person_roles = _clean_table(tables["_sample_person_roles"])
    person_positions = _clean_table(tables["personpositionrelation"])
    board_team = _clean_table(tables["companyboardteamrelation"])
    board_seats = _clean_table(tables["personboardseatrelation"])
    competitor_counts = _count_by_company(_clean_table(tables["companycompetitorrelation"]))
    similar_counts = _count_by_company(_clean_table(tables["companysimilarrelation"]))

    cases: List[BoardCase] = []
    for _, deal in case_deals.iterrows():
        company_id = _as_str(deal.get("companyid"))
        deal_id = _as_str(deal.get("dealid"), "unknown_deal")
        decision_date = deal.get("dealdate")
        case_id = f"{company_id}_{deal_id}" if company_id else deal_id

        prior_deals = _prior_deals(financing_deals, company_id, decision_date)
        previous_deal = prior_deals.iloc[-1] if not prior_deals.empty else None
        prior_previous_deal = prior_deals.iloc[-2] if len(prior_deals) > 1 else None
        previous_deal_id = previous_deal.get("dealid") if previous_deal is not None else None

        company = company_by_id.get(company_id, {})
        industry_context = industry_by_company.get(company_id, {})
        prior_investor_context = _investor_context(
            previous_deal_id,
            deal_investors,
            investor_by_id,
        )
        real_investor_context = _investor_context(deal_id, deal_investors, investor_by_id)
        lead_investor_ids = _investor_ids_for_deal(deal_id, deal_investors, investor_role="lead")
        followon_investor_ids = _investor_ids_for_deal(deal_id, deal_investors, investor_role="followon")
        prior_company_deal_history = _company_deal_history(prior_deals, history_limit)
        prior_lead_investor_deal_history = _investor_deal_history(
            lead_investor_ids,
            financing_deals,
            deal_investors,
            investor_by_id,
            decision_date,
            history_limit,
        )
        prior_followon_investor_deal_history = _investor_deal_history(
            followon_investor_ids,
            financing_deals,
            deal_investors,
            investor_by_id,
            decision_date,
            history_limit,
        )
        employee_context = _employee_context(company_id, decision_date, employee_history)
        governance_context = _governance_context(
            company_id=company_id,
            decision_date=decision_date,
            person_roles=person_roles,
            person_positions=person_positions,
            board_team=board_team,
            board_seats=board_seats,
        )

        prior_post_valuation = _optional_float(previous_deal.get("postvaluation") if previous_deal is not None else None)
        prior_prior_post_valuation = _optional_float(
            prior_previous_deal.get("postvaluation") if prior_previous_deal is not None else None
        )
        prior_markup = _valuation_markup(prior_post_valuation, prior_prior_post_valuation)
        prior_direction = _valuation_direction_from_label_or_markup(
            previous_deal.get("vcroundup_down_flat") if previous_deal is not None else None,
            prior_markup,
        )

        real_post_valuation = _optional_float(deal.get("postvaluation"))
        real_markup = _valuation_markup(real_post_valuation, prior_post_valuation)
        real_direction = _valuation_direction_from_label_or_markup(deal.get("vcroundup_down_flat"), real_markup)
        ceo_replacement = _ceo_replacement_label(company_id, decision_date, person_roles, person_positions)

        labels = {
            "true_financing_initiated_label": "raise_now",
            "real_deal_completed_label": _as_str(deal.get("dealstatus"), "unknown"),
            "real_deal_size_usd_m": _optional_float(deal.get("dealsize")),
            "real_deal_type": _as_str(deal.get("dealtype"), "unknown_deal_type"),
            "real_pre_money_valuation_usd_m": _optional_float(deal.get("premoneyvaluation")),
            "real_post_money_valuation_usd_m": real_post_valuation,
            "real_investor_ownership_pct": _optional_float(deal.get("investorownership")),
            "real_vc_round_direction_raw": _as_str(deal.get("vcroundup_down_flat"), "unknown"),
            "real_valuation_direction_label": real_direction,
            "real_lead_investor_count": real_investor_context["lead_investor_count"],
            "real_lead_investor_types": real_investor_context["lead_investor_types"],
            "real_ceo_replacement_label": ceo_replacement["label"],
            "real_ceo_replacement_detail": ceo_replacement,
        }
        notes = {
            "source": "pitchbook_xlsx",
            "companyid": company_id,
            "target_dealid": deal_id,
            "prior_dealid": _as_str(previous_deal.get("dealid")) if previous_deal is not None else "",
            "labels": labels,
            "field_sources": _field_sources(),
            "caveats": [
                "Positive-event backtest: every case has an observable VC-like transaction as the target event.",
                "Current transaction outcomes are stored only in notes.labels and are not exposed through role attention fields.",
                "Missing target numeric labels are kept as null and skipped by numeric evaluation metrics.",
                "Some company status fields may be PitchBook snapshot fields rather than strict point-in-time facts.",
            ],
        }

        cases.append(
            BoardCase(
                case_id=case_id,
                company_id=company_id,
                target_deal_id=deal_id,
                company_label=company_id or "unknown_company",
                decision_date=_date_str(decision_date),
                business_status=_as_str(company.get("businessstatus"), "unknown"),
                company_financing_status=_as_str(company.get("companyfinancingstatus"), "unknown"),
                ownership_status=_as_str(company.get("ownershipstatus"), "unknown"),
                year_founded=_optional_int(company.get("yearfounded")),
                company_age_at_decision_years=_company_age_years(company.get("yearfounded"), decision_date),
                primary_industry=_as_str(industry_context.get("industrycode"), "unknown_industry"),
                industry_group=_as_str(industry_context.get("industrygroup"), "unknown"),
                industry_sector=_as_str(industry_context.get("industrysector"), "unknown"),
                verticals=verticals_by_company.get(company_id, []),
                keywords=_as_str(company.get("keywords"), ""),
                description=_as_str(company.get("description"), ""),
                prior_vc_deal_count=int(len(prior_deals)),
                prior_deal_date=_date_str(previous_deal.get("dealdate")) if previous_deal is not None else "",
                prior_deal_type=_as_str(previous_deal.get("dealtype") if previous_deal is not None else None, "none"),
                prior_vc_round=_as_str(previous_deal.get("vcround") if previous_deal is not None else None, "none"),
                prior_deal_size_usd_m=_optional_float(previous_deal.get("dealsize") if previous_deal is not None else None),
                prior_pre_money_valuation_usd_m=_optional_float(
                    previous_deal.get("premoneyvaluation") if previous_deal is not None else None
                ),
                prior_post_money_valuation_usd_m=prior_post_valuation,
                prior_raised_to_date_usd_m=_optional_float(
                    previous_deal.get("raisedtodate") if previous_deal is not None else None
                ),
                prior_investor_ownership_pct=_optional_float(
                    previous_deal.get("investorownership") if previous_deal is not None else None
                ),
                months_since_prior_deal=_months_between(
                    previous_deal.get("dealdate") if previous_deal is not None else None,
                    decision_date,
                ),
                prior_valuation_markup_multiple=prior_markup,
                prior_valuation_direction_label=prior_direction,
                prior_investor_count=_optional_int(previous_deal.get("investors") if previous_deal is not None else None),
                prior_new_investor_count=_optional_int(previous_deal.get("newinvestors") if previous_deal is not None else None),
                prior_followon_investor_count=_optional_int(
                    previous_deal.get("followoninvestors") if previous_deal is not None else None
                ),
                prior_lead_investor_count=prior_investor_context["lead_investor_count"],
                prior_lead_investor_types=prior_investor_context["lead_investor_types"],
                prior_lead_investor_amount_share=prior_investor_context["lead_investor_amount_share"],
                prior_lead_preferred_deal_size_min_usd_m=prior_investor_context[
                    "lead_preferred_deal_size_min_usd_m"
                ],
                prior_lead_preferred_deal_size_max_usd_m=prior_investor_context[
                    "lead_preferred_deal_size_max_usd_m"
                ],
                prior_lead_preferred_company_valuation_min_usd_m=prior_investor_context[
                    "lead_preferred_company_valuation_min_usd_m"
                ],
                prior_lead_preferred_company_valuation_max_usd_m=prior_investor_context[
                    "lead_preferred_company_valuation_max_usd_m"
                ],
                prior_company_deal_history=prior_company_deal_history,
                prior_lead_investor_deal_history=prior_lead_investor_deal_history,
                prior_followon_investor_deal_history=prior_followon_investor_deal_history,
                employee_count_at_decision=employee_context["employee_count_at_decision"],
                previous_employee_count=employee_context["previous_employee_count"],
                employee_growth_rate=employee_context["employee_growth_rate"],
                engineering_role_count=governance_context["engineering_role_count"],
                executive_role_count=governance_context["executive_role_count"],
                founder_count=governance_context["founder_count"],
                current_ceo_count=governance_context["current_ceo_count"],
                current_ceo_is_founder=governance_context["current_ceo_is_founder"],
                board_member_count=governance_context["board_member_count"],
                investor_board_member_count=governance_context["investor_board_member_count"],
                competitor_count=competitor_counts.get(company_id, 0),
                similar_company_count=similar_counts.get(company_id, 0),
                notes=notes,
            )
        )
    return cases


def _clean_table(df: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with normalized date-like columns where useful."""
    cleaned = df.copy()
    for column in ("dealdate", "announceddate", "date", "startdate", "enddate", "investorsince", "investorexit"):
        if column in cleaned.columns:
            cleaned[column] = pd.to_datetime(cleaned[column], errors="coerce")
    return cleaned


def _select_vc_deals(deal_df: pd.DataFrame) -> pd.DataFrame:
    """Select observable venture financing events from the deal table."""
    deal_type = deal_df["dealtype"].fillna("").astype(str)
    deal_class = deal_df["dealclass"].fillna("").astype(str)
    mask = deal_type.isin(VC_DEAL_TYPES) | deal_class.eq("Venture Capital")
    return deal_df[mask].copy()


def _normalize_history_limit(history_limit: Optional[int]) -> Optional[int]:
    """Normalize the optional history limit; negative values mean no limit."""
    if history_limit is None or history_limit < 0:
        return None
    return int(history_limit)


def _company_deal_history(prior_deals: pd.DataFrame, history_limit: Optional[int]) -> List[Dict[str, Any]]:
    """Return same-company historical deal records visible before the decision date."""
    if prior_deals.empty or history_limit == 0:
        return []
    previous_post_valuation: Optional[float] = None
    enriched_rows: List[Dict[str, Any]] = []
    for _, row in prior_deals.iterrows():
        payload = _deal_history_payload(row, previous_post_valuation=previous_post_valuation)
        enriched_rows.append(payload)
        post_valuation = _optional_float(row.get("postvaluation"))
        if post_valuation is not None and post_valuation > 0:
            previous_post_valuation = post_valuation
    return _tail(enriched_rows, history_limit)


def _investor_ids_for_deal(deal_id: Any, deal_investors: pd.DataFrame, *, investor_role: str) -> Set[str]:
    """Return investor IDs from one target deal for a role-specific investor representative."""
    deal_id_text = _as_str(deal_id)
    if not deal_id_text or deal_investors.empty:
        return set()
    relation = deal_investors[deal_investors["dealid"].astype(str) == deal_id_text].copy()
    if relation.empty:
        return set()

    is_lead = pd.to_numeric(relation["isleadinvestor"], errors="coerce").fillna(0).astype(int) == 1
    if investor_role == "lead":
        selected = relation[is_lead]
    elif investor_role == "followon":
        status = relation["investorstatus"].fillna("").astype(str).str.lower()
        selected = relation[status.str.contains("follow-on", regex=False)]
        if selected.empty:
            selected = relation[~is_lead]
    else:
        selected = relation.iloc[0:0]
    return {_as_str(investor_id) for investor_id in selected["investorid"] if _as_str(investor_id)}


def _investor_deal_history(
    investor_ids: Set[str],
    financing_deals: pd.DataFrame,
    deal_investors: pd.DataFrame,
    investor_by_id: Dict[str, Dict[str, Any]],
    decision_date: Any,
    history_limit: Optional[int],
) -> List[Dict[str, Any]]:
    """Return historical investor-deal records for the represented investor IDs."""
    if not investor_ids or pd.isna(decision_date) or history_limit == 0:
        return []

    deal_by_id = {
        _as_str(row.get("dealid")): row
        for _, row in financing_deals.iterrows()
        if _as_str(row.get("dealid"))
    }
    relation = deal_investors[deal_investors["investorid"].astype(str).isin(investor_ids)].copy()
    items: List[tuple[pd.Timestamp, str, Dict[str, Any]]] = []
    for _, investor_deal in relation.iterrows():
        deal_id = _as_str(investor_deal.get("dealid"))
        deal = deal_by_id.get(deal_id)
        if deal is None:
            continue
        deal_date = pd.to_datetime(deal.get("dealdate"), errors="coerce")
        if pd.isna(deal_date) or deal_date >= decision_date:
            continue
        investor_id = _as_str(investor_deal.get("investorid"))
        investor_profile = investor_by_id.get(investor_id, {})
        payload = _deal_history_payload(deal, previous_post_valuation=None)
        payload.update(
            {
                "investor_id": investor_id,
                "investor_primary_type": _as_str(investor_profile.get("primaryinvestortype"), ""),
                "investor_status_in_deal": _as_str(investor_deal.get("investorstatus"), ""),
                "is_lead_investor": bool(_optional_int(investor_deal.get("isleadinvestor")) == 1),
                "investor_investment_amount_usd_m": _optional_float(investor_deal.get("investorinvestmentamount")),
                "investor_preferred_deal_size_min_usd_m": _optional_float(
                    investor_profile.get("preferreddealsizemin") or investor_profile.get("preferreddealsize")
                ),
                "investor_preferred_deal_size_max_usd_m": _optional_float(
                    investor_profile.get("preferreddealsizemax") or investor_profile.get("preferreddealsize")
                ),
                "investor_preferred_company_valuation_min_usd_m": _optional_float(
                    investor_profile.get("preferredcompanyvaluationmin")
                    or investor_profile.get("preferredcompanyvaluation")
                ),
                "investor_preferred_company_valuation_max_usd_m": _optional_float(
                    investor_profile.get("preferredcompanyvaluationmax")
                    or investor_profile.get("preferredcompanyvaluation")
                ),
            }
        )
        items.append((deal_date, f"{deal_id}_{investor_id}", payload))

    items.sort(key=lambda item: (item[0], item[1]))
    payloads = [item[2] for item in items]
    return _tail(payloads, history_limit)


def _deal_history_payload(row: Any, *, previous_post_valuation: Optional[float]) -> Dict[str, Any]:
    """Serialize one historical deal row without exposing future target labels."""
    post_valuation = _optional_float(row.get("postvaluation"))
    markup = _valuation_markup(post_valuation, previous_post_valuation)
    return {
        "deal_id": _as_str(row.get("dealid")),
        "company_id": _as_str(row.get("companyid")),
        "deal_date": _date_str(row.get("dealdate")),
        "deal_class": _as_str(row.get("dealclass"), ""),
        "deal_type": _as_str(row.get("dealtype"), ""),
        "deal_status": _as_str(row.get("dealstatus"), ""),
        "vc_round": _as_str(row.get("vcround"), ""),
        "deal_size_usd_m": _optional_float(row.get("dealsize")),
        "pre_money_valuation_usd_m": _optional_float(row.get("premoneyvaluation")),
        "post_money_valuation_usd_m": post_valuation,
        "investor_ownership_pct": _optional_float(row.get("investorownership")),
        "raised_to_date_usd_m": _optional_float(row.get("raisedtodate")),
        "investor_count": _optional_int(row.get("investors")),
        "new_investor_count": _optional_int(row.get("newinvestors")),
        "followon_investor_count": _optional_int(row.get("followoninvestors")),
        "valuation_markup_multiple": markup,
        "valuation_direction_label": _valuation_direction_from_label_or_markup(row.get("vcroundup_down_flat"), markup),
    }


def _tail(items: List[Dict[str, Any]], limit: Optional[int]) -> List[Dict[str, Any]]:
    """Return the most recent history records while preserving chronological order."""
    if limit is None:
        return items
    if limit <= 0:
        return []
    return items[-limit:]


def _primary_industry_by_company(df: pd.DataFrame) -> Dict[str, Dict[str, Any]]:
    """Map company id to the primary industry row, falling back to first row."""
    result: Dict[str, Dict[str, Any]] = {}
    if df.empty:
        return result
    sorted_df = df.sort_values("isprimary", ascending=False)
    for _, row in sorted_df.iterrows():
        company_id = _as_str(row.get("companyid"))
        if company_id and company_id not in result:
            result[company_id] = row.to_dict()
    return result


def _list_by_company(df: pd.DataFrame, column: str) -> Dict[str, List[str]]:
    """Group one text column into lists by company id."""
    result: Dict[str, List[str]] = {}
    if df.empty or column not in df.columns:
        return result
    for company_id, group in df.groupby("companyid", dropna=True):
        values = sorted({_as_str(value) for value in group[column] if _as_str(value)})
        result[_as_str(company_id)] = values
    return result


def _index_by_id(df: pd.DataFrame, key: str) -> Dict[str, Dict[str, Any]]:
    """Index a dataframe by one id column."""
    result: Dict[str, Dict[str, Any]] = {}
    if df.empty or key not in df.columns:
        return result
    for _, row in df.iterrows():
        item_id = _as_str(row.get(key))
        if item_id:
            result[item_id] = row.to_dict()
    return result


def _count_by_company(df: pd.DataFrame) -> Dict[str, int]:
    """Count relation rows by company id."""
    if df.empty or "companyid" not in df.columns:
        return {}
    return {_as_str(company_id): int(count) for company_id, count in df.groupby("companyid").size().items()}


def _prior_deals(deal_df: pd.DataFrame, company_id: str, decision_date: Any) -> pd.DataFrame:
    """Return same-company VC deals strictly before the decision date."""
    if not company_id or pd.isna(decision_date):
        return deal_df.iloc[0:0].copy()
    company_deals = deal_df[deal_df["companyid"].astype(str) == company_id].copy()
    company_deals = company_deals[pd.to_datetime(company_deals["dealdate"], errors="coerce") < decision_date]
    if company_deals.empty:
        return company_deals
    return company_deals.sort_values(["dealdate", "dealid"])


def _investor_context(deal_id: Any, deal_investors: pd.DataFrame, investor_by_id: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize lead-investor participation for one already-known deal."""
    empty = {
        "lead_investor_count": 0,
        "lead_investor_types": [],
        "lead_investor_amount_share": None,
        "lead_preferred_deal_size_min_usd_m": None,
        "lead_preferred_deal_size_max_usd_m": None,
        "lead_preferred_company_valuation_min_usd_m": None,
        "lead_preferred_company_valuation_max_usd_m": None,
    }
    deal_id_text = _as_str(deal_id)
    if not deal_id_text or deal_investors.empty:
        return empty

    relation = deal_investors[deal_investors["dealid"].astype(str) == deal_id_text].copy()
    if relation.empty:
        return empty

    amounts = pd.to_numeric(relation["investorinvestmentamount"], errors="coerce").fillna(0.0)
    total_amount = float(amounts.sum())
    lead_relation = relation[pd.to_numeric(relation["isleadinvestor"], errors="coerce").fillna(0).astype(int) == 1]
    lead_amount = float(pd.to_numeric(lead_relation["investorinvestmentamount"], errors="coerce").fillna(0.0).sum())
    lead_profiles = [
        investor_by_id.get(_as_str(investor_id), {})
        for investor_id in lead_relation["investorid"]
        if _as_str(investor_id)
    ]
    lead_types = sorted(
        {
            _as_str(profile.get("primaryinvestortype"))
            for profile in lead_profiles
            if _as_str(profile.get("primaryinvestortype"))
        }
    )
    return {
        "lead_investor_count": int(len(lead_relation)),
        "lead_investor_types": lead_types,
        "lead_investor_amount_share": lead_amount / total_amount if total_amount > 0 else None,
        "lead_preferred_deal_size_min_usd_m": _min_positive(
            profile.get("preferreddealsizemin") or profile.get("preferreddealsize") for profile in lead_profiles
        ),
        "lead_preferred_deal_size_max_usd_m": _max_positive(
            profile.get("preferreddealsizemax") or profile.get("preferreddealsize") for profile in lead_profiles
        ),
        "lead_preferred_company_valuation_min_usd_m": _min_positive(
            profile.get("preferredcompanyvaluationmin") or profile.get("preferredcompanyvaluation")
            for profile in lead_profiles
        ),
        "lead_preferred_company_valuation_max_usd_m": _max_positive(
            profile.get("preferredcompanyvaluationmax") or profile.get("preferredcompanyvaluation")
            for profile in lead_profiles
        ),
    }


def _employee_context(company_id: str, decision_date: Any, employee_history: pd.DataFrame) -> Dict[str, Optional[float]]:
    """Compute employee count and growth from records available before the decision date."""
    history = employee_history[employee_history["companyid"].astype(str) == company_id].copy()
    if history.empty:
        return {"employee_count_at_decision": None, "previous_employee_count": None, "employee_growth_rate": None}
    history = history.sort_values("date")
    if not pd.isna(decision_date):
        history = history[history["date"] <= decision_date]
    if history.empty:
        return {"employee_count_at_decision": None, "previous_employee_count": None, "employee_growth_rate": None}
    current = _optional_float(history.iloc[-1].get("employeecount"))
    previous = _optional_float(history.iloc[-2].get("employeecount")) if len(history) > 1 else None
    growth = (current - previous) / previous if current is not None and previous is not None and previous > 0 else None
    return {
        "employee_count_at_decision": current,
        "previous_employee_count": previous,
        "employee_growth_rate": growth,
    }


def _governance_context(
    *,
    company_id: str,
    decision_date: Any,
    person_roles: pd.DataFrame,
    person_positions: pd.DataFrame,
    board_team: pd.DataFrame,
    board_seats: pd.DataFrame,
) -> Dict[str, Any]:
    """Summarize founder, CEO, engineering, executive, and board composition at decision time."""
    roles = person_roles[person_roles["companyid"].astype(str) == company_id].copy()
    active_roles = _active_as_of(roles, decision_date)
    founders = active_roles[active_roles.get("is_founder", False).fillna(False).astype(bool)] if not active_roles.empty else active_roles
    if founders.empty and not roles.empty:
        founders = roles[roles.get("is_founder", False).fillna(False).astype(bool)]
    founder_ids = {_as_str(person_id) for person_id in founders.get("personid", []) if _as_str(person_id)}

    positions = person_positions[
        (person_positions.get("entitytype", "").astype(str) == "Company")
        & (person_positions.get("entityid", "").astype(str) == company_id)
    ].copy()
    active_positions = _active_as_of(positions, decision_date)
    ceo_rows = active_positions[_is_ceo_series(active_positions)] if not active_positions.empty else active_positions
    ceo_ids = {_as_str(person_id) for person_id in ceo_rows.get("personid", []) if _as_str(person_id)}

    board_rows = _active_as_of(board_team[board_team["companyid"].astype(str) == company_id].copy(), decision_date)
    board_rows = board_rows[pd.to_numeric(board_rows.get("isonboard"), errors="coerce").fillna(0).astype(bool)]
    board_seat_rows = _active_as_of(board_seats[board_seats["companyid"].astype(str) == company_id].copy(), decision_date)
    board_ids = {
        _as_str(person_id)
        for person_id in list(board_rows.get("personid", [])) + list(board_seat_rows.get("personid", []))
        if _as_str(person_id)
    }
    investor_board_count = len(
        {
            _as_str(person_id)
            for person_id in list(board_rows[board_rows.get("representingid").notna()].get("personid", []))
            + list(board_seat_rows[board_seat_rows.get("representingid").notna()].get("personid", []))
            if _as_str(person_id)
        }
    )

    return {
        "founder_count": len(founder_ids),
        "current_ceo_count": len(ceo_ids),
        "current_ceo_is_founder": bool(ceo_ids & founder_ids),
        "engineering_role_count": int(_is_engineering_series(active_positions).sum()) if not active_positions.empty else 0,
        "executive_role_count": int(_is_executive_series(active_positions).sum()) if not active_positions.empty else 0,
        "board_member_count": len(board_ids),
        "investor_board_member_count": investor_board_count,
    }


def _ceo_replacement_label(
    company_id: str,
    decision_date: Any,
    person_roles: pd.DataFrame,
    person_positions: pd.DataFrame,
    window_months: int = 24,
) -> Dict[str, Any]:
    """Infer whether CEO changes within a fixed post-financing window."""
    if not company_id or pd.isna(decision_date):
        return {"label": "unknown", "window_months": window_months, "reason": "missing company or decision date"}

    date = pd.Timestamp(decision_date)
    window_end = date + pd.DateOffset(months=window_months)
    positions = person_positions[
        (person_positions.get("entitytype", "").astype(str) == "Company")
        & (person_positions.get("entityid", "").astype(str) == company_id)
    ].copy()
    ceo_positions = positions[_is_ceo_series(positions)] if not positions.empty else positions
    if ceo_positions.empty:
        return {"label": "unknown", "window_months": window_months, "reason": "no CEO position rows"}

    initial_rows = _active_as_of(ceo_positions, date)
    initial_ceo_ids = {_as_str(person_id) for person_id in initial_rows.get("personid", []) if _as_str(person_id)}
    if not initial_ceo_ids:
        return {"label": "unknown", "window_months": window_months, "reason": "no CEO active at decision date"}

    future_rows = ceo_positions[
        (ceo_positions["startdate"].notna()) & (ceo_positions["startdate"] > date) & (ceo_positions["startdate"] <= window_end)
    ]
    future_ceo_ids = {_as_str(person_id) for person_id in future_rows.get("personid", []) if _as_str(person_id)}
    ended_initial = initial_rows[
        (initial_rows["enddate"].notna()) & (initial_rows["enddate"] > date) & (initial_rows["enddate"] <= window_end)
    ]
    replaced = bool(future_ceo_ids - initial_ceo_ids) or not ended_initial.empty

    roles = person_roles[person_roles["companyid"].astype(str) == company_id].copy()
    founders = roles[roles.get("is_founder", False).fillna(False).astype(bool)] if not roles.empty else roles
    founder_ids = {_as_str(person_id) for person_id in founders.get("personid", []) if _as_str(person_id)}
    successor_type = "unknown"
    if future_ceo_ids - initial_ceo_ids:
        successor_ids = future_ceo_ids - initial_ceo_ids
        prior_company_people = {
            _as_str(person_id)
            for person_id in roles[roles["startdate"].isna() | (roles["startdate"] <= date)].get("personid", [])
            if _as_str(person_id)
        }
        successor_type = "internal" if successor_ids & prior_company_people else "external"

    return {
        "label": "replace" if replaced else "keep",
        "window_months": window_months,
        "initial_ceo_ids": sorted(initial_ceo_ids),
        "future_ceo_ids": sorted(future_ceo_ids),
        "founder_ceo_at_decision": bool(initial_ceo_ids & founder_ids),
        "successor_type": successor_type,
    }


def _active_as_of(df: pd.DataFrame, date: Any) -> pd.DataFrame:
    """Return rows whose start/end dates imply activity at the given date."""
    if df.empty or pd.isna(date):
        return df.iloc[0:0].copy()
    point = pd.Timestamp(date)
    active = df.copy()
    if "startdate" in active.columns:
        active = active[active["startdate"].isna() | (active["startdate"] <= point)]
    if "enddate" in active.columns:
        active = active[active["enddate"].isna() | (active["enddate"] >= point)]
    return active


def _is_ceo_series(df: pd.DataFrame) -> pd.Series:
    """Return a boolean series identifying CEO position rows."""
    if df.empty:
        return pd.Series(dtype=bool)
    title = df.get("fulltitle", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    level = df.get("positionlevel", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    return title.str.contains("chief executive officer|\\bceo\\b", regex=True) | level.isin(CEO_TITLES)


def _is_engineering_series(df: pd.DataFrame) -> pd.Series:
    """Return a boolean series identifying engineering or technical leadership rows."""
    if df.empty:
        return pd.Series(dtype=bool)
    title = df.get("fulltitle", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    level = df.get("positionlevel", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    combined = title + " " + level
    return combined.apply(lambda text: any(token in text for token in ENGINEERING_TITLE_TOKENS))


def _is_executive_series(df: pd.DataFrame) -> pd.Series:
    """Return a boolean series identifying executive rows."""
    if df.empty:
        return pd.Series(dtype=bool)
    title = df.get("fulltitle", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    level = df.get("positionlevel", pd.Series("", index=df.index)).fillna("").astype(str).str.lower()
    return title.str.contains("chief|president|founder|executive", regex=True) | level.str.contains("chief|executive|founder", regex=True)


def _company_age_years(year_founded: Any, decision_date: Any) -> Optional[float]:
    """Compute company age in years at the decision date."""
    founded = _optional_int(year_founded)
    if founded is None or founded <= 0 or pd.isna(decision_date):
        return None
    return max(0.0, float(pd.Timestamp(decision_date).year - founded))


def _months_between(start: Any, end: Any) -> Optional[float]:
    """Approximate elapsed months between two dates."""
    if pd.isna(start) or pd.isna(end):
        return None
    delta_days = (pd.Timestamp(end) - pd.Timestamp(start)).days
    return round(max(0.0, delta_days / 30.4375), 2)


def _valuation_markup(current: Optional[float], previous: Optional[float]) -> Optional[float]:
    """Return valuation markup when prior post-money valuation is available."""
    return current / previous if current is not None and previous is not None and current > 0 and previous > 0 else None


def _valuation_direction_from_label_or_markup(raw_label: Any, markup: Optional[float]) -> ValuationDirection:
    """Normalize PitchBook direction label, falling back to valuation markup."""
    label = _as_str(raw_label).strip().lower()
    if "up" in label:
        return "up"
    if "down" in label:
        return "down"
    if "flat" in label:
        return "flat"
    return _valuation_direction_from_markup(markup)


def _valuation_direction_from_markup(markup: Optional[float]) -> ValuationDirection:
    """Infer valuation direction from an observed valuation markup."""
    if markup is None or markup <= 0:
        return "unknown"
    if markup >= 1.15:
        return "up"
    if markup <= 0.85:
        return "down"
    return "flat"


def _field_sources() -> Dict[str, str]:
    """Document where generated BoardCase fields and labels came from."""
    return {
        "decision_date": "target deal.dealdate, used only as a decision timestamp",
        "prior_deal_size_usd_m": "previous same-company VC deal.dealsize",
        "prior_post_money_valuation_usd_m": "previous same-company VC deal.postvaluation",
        "prior_valuation_markup_multiple": "previous VC deal.postvaluation divided by the deal before it",
        "prior_company_deal_history": "same-company VC-like deals before decision_date, truncated by history_limit",
        "prior_lead_investor_deal_history": "historical VC-like investments before decision_date by lead investors from the target financing round",
        "prior_followon_investor_deal_history": "historical VC-like investments before decision_date by follow-on or non-lead investors from the target financing round",
        "employee_growth_rate": "companyemployeehistoryrelation.employeecount before decision_date",
        "governance_fields": "_sample_person_roles, personpositionrelation, companyboardteamrelation, personboardseatrelation before decision_date",
        "labels": "current target deal outcomes and derived 24-month CEO replacement label; not exposed to agents",
    }


def _min_positive(values: Any) -> Optional[float]:
    """Return the smallest positive numeric value from an iterable."""
    positives = [number for number in (_optional_float(value) for value in values) if number is not None and number > 0]
    return min(positives) if positives else None


def _max_positive(values: Any) -> Optional[float]:
    """Return the largest positive numeric value from an iterable."""
    positives = [number for number in (_optional_float(value) for value in values) if number is not None and number > 0]
    return max(positives) if positives else None


def _date_str(value: Any) -> str:
    """Serialize a timestamp-like value as YYYY-MM-DD."""
    if value is None or pd.isna(value):
        return ""
    return pd.Timestamp(value).date().isoformat()


def _as_str(value: Any, default: str = "") -> str:
    """Convert a dataframe cell to a clean string."""
    if value is None or (isinstance(value, float) and math.isnan(value)) or pd.isna(value):
        return default
    text = str(value).strip()
    return text if text and text.lower() != "nan" else default


def _as_float(value: Any, default: float = 0.0) -> float:
    """Convert a dataframe cell to float."""
    if value is None or pd.isna(value):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _optional_float(value: Any) -> Optional[float]:
    """Convert a dataframe cell to float while preserving missing values."""
    if value is None or pd.isna(value):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _as_int(value: Any, default: int = 0) -> int:
    """Convert a dataframe cell to int."""
    if value is None or pd.isna(value):
        return default
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return default


def _optional_int(value: Any) -> Optional[int]:
    """Convert a dataframe cell to int while preserving missing values."""
    if value is None or pd.isna(value):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
