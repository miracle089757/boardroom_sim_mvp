# 辩论前后准确度变化报告

- 分析案例数：50
- 数值指标正确判定阈值：预测值相对真实值误差 <= 50%
- 交易完成判断暂不计入准确率，因为当前样本几乎全部是已完成交易。

## 1. 各阶段预测准确度

| stage | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| initial | 50/50 (100.00%) | 24/50 (48.00%) | 6/7 (85.71%) | 7/34 (20.59%) | 9/17 (52.94%) | 10/13 (76.92%) |
| round_1 | 50/50 (100.00%) | 24/50 (48.00%) | 6/7 (85.71%) | 7/34 (20.59%) | 9/17 (52.94%) | 10/13 (76.92%) |
| round_2 | 50/50 (100.00%) | 25/50 (50.00%) | 6/7 (85.71%) | 7/34 (20.59%) | 9/17 (52.94%) | 10/13 (76.92%) |
| round_3 | 50/50 (100.00%) | 24/50 (48.00%) | 6/7 (85.71%) | 7/34 (20.59%) | 9/17 (52.94%) | 10/13 (76.92%) |
| final | 50/50 (100.00%) | 24/50 (48.00%) | 6/7 (85.71%) | 7/34 (20.59%) | 9/17 (52.94%) | 10/13 (76.92%) |

## 2. 单 Agent Baseline 对比

| system | rows | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_agent_final | 50 | 50/50 (100.00%) | 24/50 (48.00%) | 6/7 (85.71%) | 7/34 (20.59%) | 9/17 (52.94%) | 10/13 (76.92%) |
| baseline_history_only | 50 | 50/50 (100.00%) | 26/50 (52.00%) | 6/7 (85.71%) | 6/34 (17.65%) | 4/17 (23.53%) | 2/13 (15.38%) |
| baseline_history_with_roles | 50 | 50/50 (100.00%) | 26/50 (52.00%) | 6/7 (85.71%) | 4/34 (11.76%) | 7/17 (41.18%) | 2/13 (15.38%) |

## 3. 辩论前 vs 辩论后

### initial_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 1 (2.00%) | 1 (2.00%) | 23 (46.00%) | 25 (50.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 7 (20.59%) | 27 (79.41%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 9 (52.94%) | 8 (47.06%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 10 (76.92%) | 3 (23.08%) | 13 |

## 4. 随辩论轮次推进的正确性变化

### initial_to_round_1

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 24 (48.00%) | 26 (52.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 7 (20.59%) | 27 (79.41%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 9 (52.94%) | 8 (47.06%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 10 (76.92%) | 3 (23.08%) | 13 |

### round_1_to_round_2

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 1 (2.00%) | 0 (0.00%) | 24 (48.00%) | 25 (50.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 7 (20.59%) | 27 (79.41%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 9 (52.94%) | 8 (47.06%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 10 (76.92%) | 3 (23.08%) | 13 |

### round_2_to_round_3

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 1 (2.00%) | 24 (48.00%) | 25 (50.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 7 (20.59%) | 27 (79.41%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 9 (52.94%) | 8 (47.06%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 10 (76.92%) | 3 (23.08%) | 13 |

### round_3_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 50 (100.00%) | 0 (0.00%) | 50 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 24 (48.00%) | 26 (52.00%) | 50 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 6 (85.71%) | 1 (14.29%) | 7 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 7 (20.59%) | 27 (79.41%) | 34 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 9 (52.94%) | 8 (47.06%) | 17 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 10 (76.92%) | 3 (23.08%) | 13 |

## 5. 数值预测是否更接近真实值

| metric | transition | closer | farther | same | evaluated |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial_to_final | 0 (0.00%) | 1 (2.94%) | 33 (97.06%) | 34 |
| post_money_valuation | initial_to_final | 0 (0.00%) | 1 (5.88%) | 16 (94.12%) | 17 |
| investor_ownership | initial_to_final | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | initial_to_round_1 | 0 (0.00%) | 0 (0.00%) | 34 (100.00%) | 34 |
| post_money_valuation | initial_to_round_1 | 0 (0.00%) | 0 (0.00%) | 17 (100.00%) | 17 |
| investor_ownership | initial_to_round_1 | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 34 (100.00%) | 34 |
| post_money_valuation | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 17 (100.00%) | 17 |
| investor_ownership | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | round_2_to_round_3 | 0 (0.00%) | 1 (2.94%) | 33 (97.06%) | 34 |
| post_money_valuation | round_2_to_round_3 | 0 (0.00%) | 1 (5.88%) | 16 (94.12%) | 17 |
| investor_ownership | round_2_to_round_3 | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |
| deal_size | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 34 (100.00%) | 34 |
| post_money_valuation | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 17 (100.00%) | 17 |
| investor_ownership | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 13 (100.00%) | 13 |

## 6. 数值误差随阶段变化

| metric | stage | evaluated | MAE | MAPE | Median APE |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial | 34 | 35.772 M USD | 949.56% | 92.31% |
| deal_size | round_1 | 34 | 35.772 M USD | 949.56% | 92.31% |
| deal_size | round_2 | 34 | 35.772 M USD | 949.56% | 92.31% |
| deal_size | round_3 | 34 | 35.793 M USD | 949.60% | 92.31% |
| deal_size | final | 34 | 35.793 M USD | 949.60% | 92.31% |
| post_money_valuation | initial | 17 | 130.167 M USD | 55.71% | 50.00% |
| post_money_valuation | round_1 | 17 | 130.167 M USD | 55.71% | 50.00% |
| post_money_valuation | round_2 | 17 | 130.167 M USD | 55.71% | 50.00% |
| post_money_valuation | round_3 | 17 | 130.293 M USD | 55.76% | 50.00% |
| post_money_valuation | final | 17 | 130.293 M USD | 55.76% | 50.00% |
| investor_ownership | initial | 13 | 25.049 pct | 40.76% | 46.38% |
| investor_ownership | round_1 | 13 | 25.049 pct | 40.76% | 46.38% |
| investor_ownership | round_2 | 13 | 25.049 pct | 40.76% | 46.38% |
| investor_ownership | round_3 | 13 | 25.049 pct | 40.76% | 46.38% |
| investor_ownership | final | 13 | 25.049 pct | 40.76% | 46.38% |
