# 辩论前后准确度变化报告

- 分析案例数：3
- 数值指标正确判定阈值：预测值相对真实值误差 <= 50%
- 交易完成判断暂不计入准确率，因为当前样本几乎全部是已完成交易。

## 1. 各阶段预测准确度

| stage | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| initial | 3/3 (100.00%) | 2/3 (66.67%) | 2/2 (100.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |
| round_1 | 3/3 (100.00%) | 2/3 (66.67%) | 1/2 (50.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |
| round_2 | 3/3 (100.00%) | 2/3 (66.67%) | 1/2 (50.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |
| round_3 | 3/3 (100.00%) | 2/3 (66.67%) | 1/2 (50.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |
| final | 3/3 (100.00%) | 2/3 (66.67%) | 1/2 (50.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |

## 2. 单 Agent Baseline 对比

| system | rows | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_agent_final | 3 | 3/3 (100.00%) | 2/3 (66.67%) | 1/2 (50.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |
| baseline_history_only | 3 | 3/3 (100.00%) | 2/3 (66.67%) | 2/2 (100.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |
| baseline_history_with_roles | 3 | 3/3 (100.00%) | 2/3 (66.67%) | 2/2 (100.00%) | 0/3 (0.00%) | 0/3 (0.00%) | 2/3 (66.67%) |

## 3. 辩论前 vs 辩论后

### initial_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 0 (0.00%) | 3 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |
| valuation_direction | 0 (0.00%) | 1 (50.00%) | 1 (50.00%) | 0 (0.00%) | 2 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |

## 4. 随辩论轮次推进的正确性变化

### initial_to_round_1

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 0 (0.00%) | 3 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |
| valuation_direction | 0 (0.00%) | 1 (50.00%) | 1 (50.00%) | 0 (0.00%) | 2 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |

### round_1_to_round_2

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 0 (0.00%) | 3 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 1 (50.00%) | 1 (50.00%) | 2 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |

### round_2_to_round_3

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 0 (0.00%) | 3 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 1 (50.00%) | 1 (50.00%) | 2 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |

### round_3_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 0 (0.00%) | 3 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 1 (50.00%) | 1 (50.00%) | 2 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 2 (66.67%) | 1 (33.33%) | 3 |

## 5. 数值预测是否更接近真实值

| metric | transition | closer | farther | same | evaluated |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial_to_final | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | initial_to_final | 0 (0.00%) | 1 (33.33%) | 2 (66.67%) | 3 |
| investor_ownership | initial_to_final | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| deal_size | initial_to_round_1 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | initial_to_round_1 | 0 (0.00%) | 1 (33.33%) | 2 (66.67%) | 3 |
| investor_ownership | initial_to_round_1 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| deal_size | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| deal_size | round_2_to_round_3 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | round_2_to_round_3 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | round_2_to_round_3 | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| deal_size | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| post_money_valuation | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |
| investor_ownership | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 3 (100.00%) | 3 |

## 6. 数值误差随阶段变化

| metric | stage | evaluated | MAE | MAPE | Median APE |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial | 3 | 43.178 M USD | 341.79% | 84.09% |
| deal_size | round_1 | 3 | 43.178 M USD | 341.79% | 84.09% |
| deal_size | round_2 | 3 | 43.178 M USD | 341.79% | 84.09% |
| deal_size | round_3 | 3 | 43.178 M USD | 341.79% | 84.09% |
| deal_size | final | 3 | 43.178 M USD | 341.79% | 84.09% |
| post_money_valuation | initial | 3 | 335.154 M USD | 271.04% | 88.27% |
| post_money_valuation | round_1 | 3 | 335.487 M USD | 271.34% | 89.18% |
| post_money_valuation | round_2 | 3 | 335.487 M USD | 271.34% | 89.18% |
| post_money_valuation | round_3 | 3 | 335.487 M USD | 271.34% | 89.18% |
| post_money_valuation | final | 3 | 335.487 M USD | 271.34% | 89.18% |
| investor_ownership | initial | 3 | 18.469 pct | 47.92% | 49.29% |
| investor_ownership | round_1 | 3 | 18.469 pct | 47.92% | 49.29% |
| investor_ownership | round_2 | 3 | 18.469 pct | 47.92% | 49.29% |
| investor_ownership | round_3 | 3 | 18.469 pct | 47.92% | 49.29% |
| investor_ownership | final | 3 | 18.469 pct | 47.92% | 49.29% |
