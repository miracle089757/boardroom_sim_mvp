# 辩论变化分析报告

## 总览

- 分析案例数：69
- 角色分类字段在辩论前后发生变化：47 次
- 角色预测融资额在辩论前后发生变化：46 次
- 角色满意度在辩论前后发生变化：34 次
- 最终提案分类字段在辩论前后发生变化：17 次
- 最终提案数值字段在辩论前后发生变化：25 次

解释：这里的“辩论前后”指每个角色的初始 private assessment 与全部 bargaining 结束后的最终 role decision 之间的差异。

## 角色字段变化

### 按字段统计

| field | changes |
| --- | ---: |
| predicted_deal_type | 36 |
| financing_intent | 7 |
| completion_view | 4 |

### 按角色统计

| role | changes |
| --- | ---: |
| Founder_CEO | 14 |
| CTO | 13 |
| Lead_VC_Director | 11 |
| Followon_VC_Director | 9 |

### 分类字段变化方向

| field | before | after | count |
| --- | --- | --- | ---: |
| predicted_deal_type | Early Stage VC | Seed Round | 36 |
| financing_intent | raise_now | wait | 7 |
| completion_view | likely_complete | unlikely_complete | 4 |

## 数值字段变化

### 角色预测融资额

| field | changes | increased | decreased | mean delta | median abs delta | max abs delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| predicted_deal_size_usd_m | 46 | 32 | 14 | 2.304 | 5.000 | 25.000 |

### 角色满意度

| field | changes | increased | decreased | mean delta | median abs delta | max abs delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| satisfaction_score | 34 | 27 | 7 | 10.735 | 20.000 | 30.000 |

## 最终提案变化

### 提案分类字段变化

| field | changes |
| --- | ---: |
| recommended_deal_type | 13 |
| tech_budget_protected | 4 |

### 提案数值字段变化

| field | changes | increased | decreased | mean delta | median abs delta | max abs delta |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| estimated_dilution_pct | 4 | 1 | 3 | 2.420 | 0.817 | 11.831 |
| recommended_deal_size_usd_m | 21 | 14 | 7 | 2.392 | 0.408 | 9.000 |

## 分轮变化

| round | field | changes |
| --- | --- | ---: |
| bargaining_round_1 | completion_view | 3 |
| bargaining_round_1 | financing_intent | 5 |
| bargaining_round_1 | predicted_deal_size_usd_m | 21 |
| bargaining_round_1 | predicted_deal_type | 18 |
| bargaining_round_1 | satisfaction_score | 19 |
| bargaining_round_2 | completion_view | 1 |
| bargaining_round_2 | financing_intent | 1 |
| bargaining_round_2 | predicted_deal_size_usd_m | 25 |
| bargaining_round_2 | predicted_deal_type | 13 |
| bargaining_round_2 | satisfaction_score | 22 |
| bargaining_round_3 | financing_intent | 1 |
| bargaining_round_3 | predicted_deal_size_usd_m | 2 |
| bargaining_round_3 | predicted_deal_type | 5 |
| bargaining_round_3 | satisfaction_score | 3 |

## 变化最多的案例

| case_id | role categorical | role size | role satisfaction | proposal categorical | proposal size delta | final type / true | final size / true |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 395080535_182107892T | 3 | 3 | 2 | 1 | 9.000 | Seed Round / Seed Round | 10.000 / 13.521 |
| 498664659_416326831T | 4 | 2 | 2 | 1 | 0.179 | Seed Round / Seed Round | 2.000 / 0.580 |
| 547069886_421335654T | 4 | 2 | 2 | 1 | 0.000 | Later Stage VC / Later Stage VC | 25.000 / 46.897 |
| 532341497_266608912T | 4 | 3 | 0 | 1 | 8.357 | Seed Round / Seed Round | 10.000 / 2.332 |
| 532476121_216082716T | 3 | 3 | 1 | 1 | 3.571 | Seed Round / Later Stage VC | 8.571 / 6.457 |
| 532476121_916845364T | 0 | 4 | 2 | 0 | 9.000 | Seed Round / Early Stage VC | 10.000 / 2.000 |
| 440112243_958212705T | 0 | 4 | 2 | 0 | 8.643 | Early Stage VC / Early Stage VC | 9.643 / 1.359 |
| 56698470_648838575T | 3 | 1 | 1 | 1 | 1.071 | Seed Round / Early Stage VC | 9.357 / n/a |
| 108943275_242536412T | 2 | 2 | 2 | 0 | 0.000 | Seed Round / Early Stage VC | 1.000 / 2.728 |
| 437602468_696873542T | 4 | 0 | 1 | 1 | 0.000 | Seed Round / Later Stage VC | 10.000 / 1.474 |
| 811956194_984457418T | 2 | 1 | 2 | 1 | 0.000 | Early Stage VC / Early Stage VC | 10.000 / 1.485 |
| 811956194_422362760T | 0 | 2 | 3 | 0 | -0.357 | Early Stage VC / Early Stage VC | 1.464 / 5.074 |
