# 最完整单案例选择报告

## 选择结果

| 项目 | 值 |
| --- | --- |
| 输入文件 | input\260524_02_03_pitchbook_sample_100_shared.xlsx |
| 输出 JSONL | input\selected_rich_case.jsonl |
| case_id | 9244942_146320797T |
| company_id | 9244942 |
| target_deal_id | 146320797T |
| 公司标签 | 9244942 |
| 行业 | Business/Productivity Software |
| 决策日期 | 2018-03-02 |
| 总分 | 0.913 |
| 通过关键筛选数 | 5/5 |

## 为什么选择这个 case

- 它优先满足用于观察董事会行为的关键条件：业务信息、历史融资、投资人上下文、Revelio/治理画像和真实标签。
- 输出的 JSONL 只包含这一行 case，可作为后续每次修改实验后的固定 smoke test 输入。
- 真实标签保存在 `notes.labels`，仅用于事后评估，不会进入角色可见字段。

## 关键筛选条件

| 条件 | 是否满足 |
| --- | --- |
| 有业务描述或关键词 | 是 |
| 有历史融资 | 是 |
| 有投资人上下文 | 是 |
| 有 Revelio/治理画像 | 是 |
| 有主要真实标签 | 是 |

## 分类完整度得分

| 类别 | 得分 | 非空字段数 |
| --- | --- | --- |
| 公司基础信息 | 1.000 | 13/13 |
| 历史融资信息 | 0.955 | 13/13 |
| 投资人上下文 | 0.621 | 7/12 |
| Revelio/治理画像 | 1.000 | 10/10 |
| 市场/竞争信息 | 1.000 | 4/4 |
| 真实标签 | 1.000 | 8/8 |

## 关键信息快照

| 字段 | 值 |
| --- | --- |
| case_id | 9244942_146320797T |
| company_id | 9244942 |
| target_deal_id | 146320797T |
| company_label | 9244942 |
| decision_date | 2018-03-02 |
| primary_industry | Business/Productivity Software |
| industry_group | Software |
| industry_sector | Information Technology |
| verticals | ["Artificial Intelligence & Machine Learning","CloudTech & DevOps","Robotics and Drones","SaaS"] |
| keywords | advances automation systems, ai automation platform, enterprise resource planning, erp, intelligent solutions, process automation, robotics automation software, robotics process, robotics process automation, software ro… |
| description | UiPath Inc offers an end-to-end cross-application enterprise automation platform principally with computer vision technology and user interface automations in its initial RPA offering, which remains the foundation of th… |
| prior_vc_deal_count | 2 |
| prior_deal_date | 2017-04-27 |
| prior_vc_round | 2nd Round |
| prior_deal_size_usd_m | 29.6333 |
| prior_pre_money_valuation_usd_m | 80 |
| prior_post_money_valuation_usd_m | 109.633 |
| prior_investor_ownership_pct | 40.4291 |
| employee_count_at_decision | 600 |
| employee_growth_rate | 0.2 |
| engineering_role_count | 4 |
| executive_role_count | 36 |
| founder_count | 3 |
| current_ceo_count | 1 |
| board_member_count | 9 |
| investor_board_member_count | 8 |
| competitor_count | 8 |
| similar_company_count | 30 |

## 真实标签快照

| 标签字段 | 值 |
| --- | --- |
| real_ceo_replacement_detail | {"label": "keep","window_months": 24,"initial_ceo_ids": ["743236954P"],"future_ceo_ids": [],"founder_ceo_at_decision": true,"successor_type": "unknown"} |
| real_ceo_replacement_label | keep |
| real_deal_completed_label | Completed |
| real_deal_size_usd_m | 153 |
| real_deal_type | Later Stage VC |
| real_investor_ownership_pct | 49.2978 |
| real_lead_investor_count | 3 |
| real_lead_investor_types | ["Growth/Expansion","Venture Capital"] |
| real_post_money_valuation_usd_m | 1103 |
| real_pre_money_valuation_usd_m | 950 |
| real_valuation_direction_label | up |
| real_vc_round_direction_raw | Up Round |
| true_financing_initiated_label | raise_now |

## Top 候选案例

| 排名 | case_id | 公司 | 行业 | 总分 | 关键条件 | 基础 | 历史 | 投资人 | Revelio/治理 | 标签 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | 9244942_146320797T | 9244942 | Business/Productivity Software | 0.913 | 5/5 | 1.00 | 0.96 | 0.62 | 1.00 | 1.00 |
| 2 | 662346332_447267668T | 662346332 | Business/Productivity Software | 0.906 | 5/5 | 1.00 | 1.00 | 0.53 | 1.00 | 1.00 |
| 3 | 218034134_219205641T | 218034134 | Business/Productivity Software | 0.904 | 5/5 | 1.00 | 1.00 | 0.62 | 1.00 | 1.00 |
| 4 | 9244942_521451522T | 9244942 | Business/Productivity Software | 0.897 | 5/5 | 1.00 | 1.00 | 0.48 | 1.00 | 1.00 |
| 5 | 650101535_880156056T | 650101535 | Network Management Software | 0.896 | 5/5 | 1.00 | 0.96 | 0.63 | 1.00 | 1.00 |
| 6 | 725460674_665989206T | 725460674 | Network Management Software | 0.880 | 5/5 | 1.00 | 0.96 | 0.66 | 1.00 | 1.00 |
| 7 | 860928473_515093409T | 860928473 | Business/Productivity Software | 0.871 | 5/5 | 0.96 | 1.00 | 0.62 | 0.79 | 1.00 |
| 8 | 662346332_638100522T | 662346332 | Business/Productivity Software | 0.869 | 5/5 | 1.00 | 1.00 | 0.34 | 1.00 | 1.00 |
| 9 | 710410150_903755063T | 710410150 | Multimedia and Design Software | 0.867 | 5/5 | 0.92 | 1.00 | 0.45 | 1.00 | 1.00 |
| 10 | 860928473_433754919T | 860928473 | Business/Productivity Software | 0.862 | 5/5 | 0.96 | 1.00 | 0.57 | 0.79 | 1.00 |

## 角色可见字段覆盖

### Founder_CEO

可见字段覆盖：17/17

| 字段 | 是否非空 | 值 |
| --- | --- | --- |
| prior_deal_size_usd_m | 是 | 29.6333 |
| prior_company_deal_history | 是 | [{"deal_id": "963111474T","company_id": "9244942","deal_date": "2015-07-01","deal_class": "Venture Capital","deal_type": "Later Stage VC","deal_status": "Completed","vc_round": "1st Round","deal_size_usd_m": 1.6,"pre_mo… |
| prior_post_money_valuation_usd_m | 是 | 109.633 |
| prior_valuation_markup_multiple | 是 | 12.7481 |
| prior_valuation_direction_label | 是 | up |
| prior_deal_type | 是 | Later Stage VC |
| prior_vc_round | 是 | 2nd Round |
| prior_raised_to_date_usd_m | 是 | 31.2333 |
| prior_investor_ownership_pct | 是 | 40.4291 |
| prior_lead_investor_count | 是 | 1 |
| prior_lead_investor_types | 是 | ["Venture Capital"] |
| employee_count_at_decision | 是 | 600 |
| employee_growth_rate | 是 | 0.2 |
| founder_count | 是 | 3 |
| current_ceo_is_founder | 是 | 是 |
| board_member_count | 是 | 9 |
| investor_board_member_count | 是 | 8 |

### CTO

可见字段覆盖：15/15

| 字段 | 是否非空 | 值 |
| --- | --- | --- |
| prior_deal_size_usd_m | 是 | 29.6333 |
| prior_company_deal_history | 是 | [{"deal_id": "963111474T","company_id": "9244942","deal_date": "2015-07-01","deal_class": "Venture Capital","deal_type": "Later Stage VC","deal_status": "Completed","vc_round": "1st Round","deal_size_usd_m": 1.6,"pre_mo… |
| prior_raised_to_date_usd_m | 是 | 31.2333 |
| employee_count_at_decision | 是 | 600 |
| previous_employee_count | 是 | 500 |
| employee_growth_rate | 是 | 0.2 |
| engineering_role_count | 是 | 4 |
| executive_role_count | 是 | 36 |
| primary_industry | 是 | Business/Productivity Software |
| industry_group | 是 | Software |
| industry_sector | 是 | Information Technology |
| verticals | 是 | ["Artificial Intelligence & Machine Learning","CloudTech & DevOps","Robotics and Drones","SaaS"] |
| keywords | 是 | advances automation systems, ai automation platform, enterprise resource planning, erp, intelligent solutions, process automation, robotics automation software, robotics process, robotics process automation, software ro… |
| description | 是 | UiPath Inc offers an end-to-end cross-application enterprise automation platform principally with computer vision technology and user interface automations in its initial RPA offering, which remains the foundation of th… |
| company_age_at_decision_years | 是 | 13 |

### Lead_VC_Director

可见字段覆盖：16/21

| 字段 | 是否非空 | 值 |
| --- | --- | --- |
| prior_post_money_valuation_usd_m | 是 | 109.633 |
| prior_lead_investor_deal_history | 是 | [{"deal_id": "437510517T","company_id": "345677179","deal_date": "2010-07-14","deal_class": "Venture Capital","deal_type": "Later Stage VC","deal_status": "Completed","vc_round": "2nd Round","deal_size_usd_m": 7.2,"pre_… |
| prior_pre_money_valuation_usd_m | 是 | 80 |
| prior_valuation_markup_multiple | 是 | 12.7481 |
| prior_valuation_direction_label | 是 | up |
| prior_deal_size_usd_m | 是 | 29.6333 |
| prior_raised_to_date_usd_m | 是 | 31.2333 |
| prior_investor_ownership_pct | 是 | 40.4291 |
| prior_investor_count | 是 | 4 |
| prior_new_investor_count | 是 | 1 |
| prior_followon_investor_count | 是 | 3 |
| prior_lead_investor_count | 是 | 1 |
| prior_lead_investor_amount_share | 否 | 未记录 |
| prior_lead_preferred_deal_size_min_usd_m | 否 | 未记录 |
| prior_lead_preferred_deal_size_max_usd_m | 否 | 未记录 |
| prior_lead_preferred_company_valuation_min_usd_m | 否 | 未记录 |
| prior_lead_preferred_company_valuation_max_usd_m | 否 | 未记录 |
| employee_growth_rate | 是 | 0.2 |
| similar_company_count | 是 | 30 |
| board_member_count | 是 | 9 |
| investor_board_member_count | 是 | 8 |

### Followon_VC_Director

可见字段覆盖：12/15

| 字段 | 是否非空 | 值 |
| --- | --- | --- |
| prior_deal_size_usd_m | 是 | 29.6333 |
| prior_followon_investor_deal_history | 是 | [{"deal_id": "453064052T","company_id": "218034134","deal_date": "2014-03-07","deal_class": "Venture Capital","deal_type": "Later Stage VC","deal_status": "Completed","vc_round": "4th Round","deal_size_usd_m": 21.749998… |
| prior_post_money_valuation_usd_m | 是 | 109.633 |
| prior_valuation_markup_multiple | 是 | 12.7481 |
| prior_valuation_direction_label | 是 | up |
| prior_investor_ownership_pct | 是 | 40.4291 |
| prior_investor_count | 是 | 4 |
| prior_followon_investor_count | 是 | 3 |
| prior_lead_investor_count | 是 | 1 |
| prior_lead_investor_types | 是 | ["Venture Capital"] |
| prior_lead_investor_amount_share | 否 | 未记录 |
| prior_lead_preferred_deal_size_min_usd_m | 否 | 未记录 |
| prior_lead_preferred_deal_size_max_usd_m | 否 | 未记录 |
| employee_growth_rate | 是 | 0.2 |
| similar_company_count | 是 | 30 |

## 固定单案例运行命令

```bash
python run_experiment.py \
  --input input/selected_rich_case.jsonl \
  --output outputs/one_case/results.jsonl \
  --trace-output outputs/one_case/traces.json \
  --readable-output outputs/one_case/boardroom_trace.md \
  --config configs/boardroom_default.toml \
  --case-limit 1
```
