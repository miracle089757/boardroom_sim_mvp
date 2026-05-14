# 辩论前后准确度变化报告

- 分析案例数：212
- 数值指标正确判定阈值：预测值相对真实值误差 <= 50%
- 交易完成判断暂不计入准确率，因为当前样本几乎全部是已完成交易。

## 1. 各阶段预测准确度

| stage | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| initial | 210/212 (99.06%) | 97/212 (45.75%) | 20/28 (71.43%) | 28/143 (19.58%) | 11/69 (15.94%) | 19/55 (34.55%) |
| round_1 | 210/212 (99.06%) | 85/212 (40.09%) | 20/28 (71.43%) | 27/143 (18.88%) | 10/69 (14.49%) | 19/55 (34.55%) |
| round_2 | 211/212 (99.53%) | 83/212 (39.15%) | 20/28 (71.43%) | 26/143 (18.18%) | 11/69 (15.94%) | 19/55 (34.55%) |
| round_3 | 211/212 (99.53%) | 82/212 (38.68%) | 20/28 (71.43%) | 26/143 (18.18%) | 11/69 (15.94%) | 19/55 (34.55%) |
| final | 211/212 (99.53%) | 82/212 (38.68%) | 20/28 (71.43%) | 26/143 (18.18%) | 11/69 (15.94%) | 19/55 (34.55%) |

## 2. 单 Agent Baseline 对比

| system | rows | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_agent_final | 212 | 211/212 (99.53%) | 82/212 (38.68%) | 20/28 (71.43%) | 26/143 (18.18%) | 11/69 (15.94%) | 19/55 (34.55%) |
| baseline_history_only | 212 | 212/212 (100.00%) | 102/212 (48.11%) | 20/28 (71.43%) | 28/143 (19.58%) | 14/69 (20.29%) | 18/55 (32.73%) |
| baseline_history_with_roles | 212 | 212/212 (100.00%) | 109/212 (51.42%) | 20/28 (71.43%) | 40/143 (27.97%) | 20/69 (28.99%) | 21/55 (38.18%) |

## 3. 辩论前 vs 辩论后

### initial_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 1 (0.47%) | 0 (0.00%) | 210 (99.06%) | 1 (0.47%) | 212 |
| deal_type | 15 (7.08%) | 30 (14.15%) | 67 (31.60%) | 100 (47.17%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 2 (1.40%) | 26 (18.18%) | 115 (80.42%) | 143 |
| post_money_valuation | 1 (1.45%) | 1 (1.45%) | 10 (14.49%) | 57 (82.61%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 19 (34.55%) | 36 (65.45%) | 55 |

## 4. 随辩论轮次推进的正确性变化

### initial_to_round_1

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 210 (99.06%) | 2 (0.94%) | 212 |
| deal_type | 14 (6.60%) | 26 (12.26%) | 71 (33.49%) | 101 (47.64%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 1 (0.70%) | 27 (18.88%) | 115 (80.42%) | 143 |
| post_money_valuation | 0 (0.00%) | 1 (1.45%) | 10 (14.49%) | 58 (84.06%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 19 (34.55%) | 36 (65.45%) | 55 |

### round_1_to_round_2

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 1 (0.47%) | 0 (0.00%) | 210 (99.06%) | 1 (0.47%) | 212 |
| deal_type | 1 (0.47%) | 3 (1.42%) | 82 (38.68%) | 126 (59.43%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 1 (0.70%) | 26 (18.18%) | 116 (81.12%) | 143 |
| post_money_valuation | 1 (1.45%) | 0 (0.00%) | 10 (14.49%) | 58 (84.06%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 19 (34.55%) | 36 (65.45%) | 55 |

### round_2_to_round_3

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 211 (99.53%) | 1 (0.47%) | 212 |
| deal_type | 0 (0.00%) | 1 (0.47%) | 82 (38.68%) | 129 (60.85%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 26 (18.18%) | 117 (81.82%) | 143 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 11 (15.94%) | 58 (84.06%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 19 (34.55%) | 36 (65.45%) | 55 |

### round_3_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 211 (99.53%) | 1 (0.47%) | 212 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 82 (38.68%) | 130 (61.32%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 26 (18.18%) | 117 (81.82%) | 143 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 11 (15.94%) | 58 (84.06%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 19 (34.55%) | 36 (65.45%) | 55 |

## 5. 数值预测是否更接近真实值

| metric | transition | closer | farther | same | evaluated |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial_to_final | 8 (5.59%) | 30 (20.98%) | 105 (73.43%) | 143 |
| post_money_valuation | initial_to_final | 6 (8.70%) | 9 (13.04%) | 54 (78.26%) | 69 |
| investor_ownership | initial_to_final | 4 (7.27%) | 12 (21.82%) | 39 (70.91%) | 55 |
| deal_size | initial_to_round_1 | 5 (3.50%) | 22 (15.38%) | 116 (81.12%) | 143 |
| post_money_valuation | initial_to_round_1 | 3 (4.35%) | 5 (7.25%) | 61 (88.41%) | 69 |
| investor_ownership | initial_to_round_1 | 3 (5.45%) | 10 (18.18%) | 42 (76.36%) | 55 |
| deal_size | round_1_to_round_2 | 5 (3.50%) | 12 (8.39%) | 126 (88.11%) | 143 |
| post_money_valuation | round_1_to_round_2 | 2 (2.90%) | 5 (7.25%) | 62 (89.86%) | 69 |
| investor_ownership | round_1_to_round_2 | 3 (5.45%) | 4 (7.27%) | 48 (87.27%) | 55 |
| deal_size | round_2_to_round_3 | 3 (2.10%) | 6 (4.20%) | 134 (93.71%) | 143 |
| post_money_valuation | round_2_to_round_3 | 2 (2.90%) | 3 (4.35%) | 64 (92.75%) | 69 |
| investor_ownership | round_2_to_round_3 | 3 (5.45%) | 5 (9.09%) | 47 (85.45%) | 55 |
| deal_size | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 143 (100.00%) | 143 |
| post_money_valuation | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 69 (100.00%) | 69 |
| investor_ownership | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 55 (100.00%) | 55 |

## 6. 数值误差随阶段变化

| metric | stage | evaluated | MAE | MAPE | Median APE |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial | 143 | 13.622 M USD | 13038.04% | 185.71% |
| deal_size | round_1 | 143 | 13.575 M USD | 13092.61% | 207.69% |
| deal_size | round_2 | 143 | 13.703 M USD | 13170.50% | 207.69% |
| deal_size | round_3 | 143 | 13.755 M USD | 13189.89% | 211.06% |
| deal_size | final | 143 | 13.755 M USD | 13189.89% | 211.06% |
| post_money_valuation | initial | 69 | 103.037 M USD | 521.58% | 191.86% |
| post_money_valuation | round_1 | 69 | 101.847 M USD | 511.40% | 188.32% |
| post_money_valuation | round_2 | 69 | 102.259 M USD | 516.90% | 188.32% |
| post_money_valuation | round_3 | 69 | 102.546 M USD | 519.62% | 191.86% |
| post_money_valuation | final | 69 | 102.546 M USD | 519.62% | 191.86% |
| investor_ownership | initial | 55 | 26.107 pct | 59.94% | 60.90% |
| investor_ownership | round_1 | 55 | 26.197 pct | 60.02% | 60.90% |
| investor_ownership | round_2 | 55 | 26.167 pct | 59.99% | 60.90% |
| investor_ownership | round_3 | 55 | 26.276 pct | 60.21% | 61.73% |
| investor_ownership | final | 55 | 26.276 pct | 60.21% | 61.73% |
