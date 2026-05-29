python3 - <<'PY'
import json
import pandas as pd
from pathlib import Path
from boardroom_sim.pitchbook import build_cases_from_pitchbook

xlsx = Path("input/260524_02_03_pitchbook_sample_100_shared.xlsx")
case_id = "11830986_789374083T"

cases = build_cases_from_pitchbook(xlsx)
case = next(c for c in cases if c.case_id == case_id)

company_id = case.company_id
target_deal_id = case.target_deal_id
prior_deal_id = case.notes.get("prior_dealid", "")

tables = pd.read_excel(xlsx, sheet_name=None)

deal = tables["deal"].copy()
company = tables["company"].copy()

target_deal_row = deal[deal["dealid"].astype(str) == target_deal_id]
prior_deal_row = deal[deal["dealid"].astype(str) == prior_deal_id] if prior_deal_id else pd.DataFrame()
company_row = company[company["companyid"].astype(str) == company_id]

output = {
    "case_id": case_id,
    "boardcase_generated_fields": case.to_dict(),
    "raw_target_deal_row": target_deal_row.to_dict(orient="records"),
    "raw_prior_deal_row": prior_deal_row.to_dict(orient="records"),
    "raw_company_row": company_row.to_dict(orient="records"),
}

Path("outputs/one_case_raw_fields.json").write_text(
    json.dumps(output, ensure_ascii=False, indent=2, default=str),
    encoding="utf-8",
)

print("已导出到 outputs/one_case_raw_fields.json")
print("companyid =", company_id)
print("target_dealid =", target_deal_id)
print("prior_dealid =", prior_deal_id)
PY
