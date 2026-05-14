# 辩论前后准确度变化报告

- 分析案例数：50
- 数值指标正确判定阈值：预测值相对真实值误差 <= 50%
- 交易完成判断暂不计入准确率，因为当前样本几乎全部是已完成交易。

## 1. 各阶段预测准确度

| stage | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| initial | 50/50 (100.00%) | 28/50 (56.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 7/17 (41.18%) | 11/13 (84.62%) |
| round_1 | 50/50 (100.00%) | 28/50 (56.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 7/17 (41.18%) | 11/13 (84.62%) |
| round_2 | 50/50 (100.00%) | 27/50 (54.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 7/17 (41.18%) | 11/13 (84.62%) |
| round_3 | 50/50 (100.00%) | 27/50 (54.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 7/17 (41.18%) | 11/13 (84.62%) |
| final | 50/50 (100.00%) | 27/50 (54.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 7/17 (41.18%) | 11/13 (84.62%) |

## 2. 单 Agent Baseline 对比

| system | rows | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_agent_final | 50 | 50/50 (100.00%) | 27/50 (54.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 7/17 (41.18%) | 11/13 (84.62%) |
| baseline_history_only | 50 | 50/50 (100.00%) | 24/50 (48.00%) | 6/7 (85.71%) | 5/34 (14.71%) | 4/17 (23.53%) | 1/13 (7.69%) |
| baseline_history_with_roles | 50 | 50/50 (100.00%) | 27/50 (54.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 7/17 (41.18%) | 3/13 (23.08%) |

## 3. 辩论前 vs 辩论后

### initial_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 1 (2.00%) | 27 (54.00%) | 22 (44.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 6 (17.65%) | 28 (82.35%) | 34 |
| post_money_valuation | 1 (5.88%) | 1 (5.88%) | 6 (35.29%) | 9 (52.94%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 11 (84.62%) | 2 (15.38%) | 13 |

## 4. 随辩论轮次推进的正确性变化

### initial_to_round_1

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 28 (56.00%) | 22 (44.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 6 (17.65%) | 28 (82.35%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 7 (41.18%) | 10 (58.82%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 11 (84.62%) | 2 (15.38%) | 13 |

### round_1_to_round_2

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 1 (2.00%) | 27 (54.00%) | 22 (44.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 6 (17.65%) | 28 (82.35%) | 34 |
| post_money_valuation | 1 (5.88%) | 1 (5.88%) | 6 (35.29%) | 9 (52.94%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 11 (84.62%) | 2 (15.38%) | 13 |

### round_2_to_round_3

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 27 (54.00%) | 23 (46.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 6 (17.65%) | 28 (82.35%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 7 (41.18%) | 10 (58.82%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 11 (84.62%) | 2 (15.38%) | 13 |

### round_3_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 27 (54.00%) | 23 (46.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 6 (17.65%) | 28 (82.35%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 7 (41.18%) | 10 (58.82%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 11 (84.62%) | 2 (15.38%) | 13 |

## 5. 数值预测是否更接近真实值

| metric | transition | closer | farther | same | evaluated |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial_to_final | 4 (11.76%) | 4 (11.76%) | 26 (76.47%) | 34 |
| post_money_valuation | initial_to_final | 2 (11.76%) | 2 (11.76%) | 13 (76.47%) | 17 |
| investor_ownership | initial_to_final | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | initial_to_round_1 | 2 (5.88%) | 1 (2.94%) | 31 (91.18%) | 34 |
| post_money_valuation | initial_to_round_1 | 1 (5.88%) | 0 (0.00%) | 16 (94.12%) | 17 |
| investor_ownership | initial_to_round_1 | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | round_1_to_round_2 | 1 (2.94%) | 4 (11.76%) | 29 (85.29%) | 34 |
| post_money_valuation | round_1_to_round_2 | 1 (5.88%) | 2 (11.76%) | 14 (82.35%) | 17 |
| investor_ownership | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | round_2_to_round_3 | 2 (5.88%) | 2 (5.88%) | 30 (88.24%) | 34 |
| post_money_valuation | round_2_to_round_3 | 0 (0.00%) | 0 (0.00%) | 17 (100.00%) | 17 |
| investor_ownership | round_2_to_round_3 | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 34 (100.00%) | 34 |
| post_money_valuation | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 17 (100.00%) | 17 |
| investor_ownership | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |

## 6. 数值误差随阶段变化

| metric | stage | evaluated | MAE | MAPE | Median APE |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial | 34 | 41.271 M USD | 974.99% | 89.10% |
| deal_size | round_1 | 34 | 41.828 M USD | 974.16% | 89.10% |
| deal_size | round_2 | 34 | 42.315 M USD | 976.45% | 89.10% |
| deal_size | round_3 | 34 | 42.308 M USD | 974.92% | 89.10% |
| deal_size | final | 34 | 42.308 M USD | 974.92% | 89.10% |
| post_money_valuation | initial | 17 | 119.689 M USD | 57.65% | 59.52% |
| post_money_valuation | round_1 | 17 | 119.563 M USD | 57.53% | 59.52% |
| post_money_valuation | round_2 | 17 | 119.306 M USD | 55.30% | 53.49% |
| post_money_valuation | round_3 | 17 | 119.306 M USD | 55.30% | 53.49% |
| post_money_valuation | final | 17 | 119.306 M USD | 55.30% | 53.49% |
| investor_ownership | initial | 13 | 26.208 pct | 42.07% | 42.36% |
| investor_ownership | round_1 | 13 | 26.208 pct | 42.07% | 42.36% |
| investor_ownership | round_2 | 13 | 26.208 pct | 42.07% | 42.36% |
| investor_ownership | round_3 | 13 | 26.208 pct | 42.07% | 42.36% |
| investor_ownership | final | 13 | 26.208 pct | 42.07% | 42.36% |
