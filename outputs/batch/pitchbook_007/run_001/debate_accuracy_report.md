# 辩论前后准确度变化报告

- 分析案例数：212
- 数值指标正确判定阈值：预测值相对真实值误差 <= 50%
- 交易完成判断暂不计入准确率，因为当前样本几乎全部是已完成交易。

## 1. 各阶段预测准确度

| stage | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| initial | 211/212 (99.53%) | 102/212 (48.11%) | 20/28 (71.43%) | 44/143 (30.77%) | 29/69 (42.03%) | 39/55 (70.91%) |
| round_1 | 211/212 (99.53%) | 105/212 (49.53%) | 20/28 (71.43%) | 44/143 (30.77%) | 29/69 (42.03%) | 39/55 (70.91%) |
| round_2 | 211/212 (99.53%) | 105/212 (49.53%) | 20/28 (71.43%) | 44/143 (30.77%) | 29/69 (42.03%) | 39/55 (70.91%) |
| round_3 | 211/212 (99.53%) | 105/212 (49.53%) | 20/28 (71.43%) | 44/143 (30.77%) | 29/69 (42.03%) | 39/55 (70.91%) |
| final | 211/212 (99.53%) | 105/212 (49.53%) | 20/28 (71.43%) | 44/143 (30.77%) | 29/69 (42.03%) | 39/55 (70.91%) |

## 2. 单 Agent Baseline 对比

| system | rows | financing_initiation | deal_type | valuation_direction | deal_size | post_money_valuation | investor_ownership |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| multi_agent_final | 212 | 211/212 (99.53%) | 105/212 (49.53%) | 20/28 (71.43%) | 44/143 (30.77%) | 29/69 (42.03%) | 39/55 (70.91%) |
| baseline_history_only | 212 | 212/212 (100.00%) | 106/212 (50.00%) | 20/28 (71.43%) | 33/143 (23.08%) | 17/69 (24.64%) | 19/55 (34.55%) |
| baseline_history_with_roles | 212 | 212/212 (100.00%) | 111/212 (52.36%) | 20/28 (71.43%) | 45/143 (31.47%) | 20/69 (28.99%) | 22/55 (40.00%) |

## 3. 辩论前 vs 辩论后

### initial_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 211 (99.53%) | 1 (0.47%) | 212 |
| deal_type | 3 (1.42%) | 0 (0.00%) | 102 (48.11%) | 107 (50.47%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 44 (30.77%) | 99 (69.23%) | 143 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 29 (42.03%) | 40 (57.97%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 39 (70.91%) | 16 (29.09%) | 55 |

## 4. 随辩论轮次推进的正确性变化

### initial_to_round_1

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 211 (99.53%) | 1 (0.47%) | 212 |
| deal_type | 3 (1.42%) | 0 (0.00%) | 102 (48.11%) | 107 (50.47%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 44 (30.77%) | 99 (69.23%) | 143 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 29 (42.03%) | 40 (57.97%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 39 (70.91%) | 16 (29.09%) | 55 |

### round_1_to_round_2

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 211 (99.53%) | 1 (0.47%) | 212 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 105 (49.53%) | 107 (50.47%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 44 (30.77%) | 99 (69.23%) | 143 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 29 (42.03%) | 40 (57.97%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 39 (70.91%) | 16 (29.09%) | 55 |

### round_2_to_round_3

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 211 (99.53%) | 1 (0.47%) | 212 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 105 (49.53%) | 107 (50.47%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 44 (30.77%) | 99 (69.23%) | 143 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 29 (42.03%) | 40 (57.97%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 39 (70.91%) | 16 (29.09%) | 55 |

### round_3_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 211 (99.53%) | 1 (0.47%) | 212 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 105 (49.53%) | 107 (50.47%) | 212 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 44 (30.77%) | 99 (69.23%) | 143 |
| post_money_valuation | 0 (0.00%) | 0 (0.00%) | 29 (42.03%) | 40 (57.97%) | 69 |
| investor_ownership | 0 (0.00%) | 0 (0.00%) | 39 (70.91%) | 16 (29.09%) | 55 |

## 5. 数值预测是否更接近真实值

| metric | transition | closer | farther | same | evaluated |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial_to_final | 10 (6.99%) | 8 (5.59%) | 125 (87.41%) | 143 |
| post_money_valuation | initial_to_final | 3 (4.35%) | 4 (5.80%) | 62 (89.86%) | 69 |
| investor_ownership | initial_to_final | 0 (0.00%) | 0 (0.00%) | 55 (100.00%) | 55 |
| deal_size | initial_to_round_1 | 3 (2.10%) | 2 (1.40%) | 138 (96.50%) | 143 |
| post_money_valuation | initial_to_round_1 | 1 (1.45%) | 1 (1.45%) | 67 (97.10%) | 69 |
| investor_ownership | initial_to_round_1 | 0 (0.00%) | 0 (0.00%) | 55 (100.00%) | 55 |
| deal_size | round_1_to_round_2 | 4 (2.80%) | 3 (2.10%) | 136 (95.10%) | 143 |
| post_money_valuation | round_1_to_round_2 | 0 (0.00%) | 2 (2.90%) | 67 (97.10%) | 69 |
| investor_ownership | round_1_to_round_2 | 0 (0.00%) | 0 (0.00%) | 55 (100.00%) | 55 |
| deal_size | round_2_to_round_3 | 4 (2.80%) | 5 (3.50%) | 134 (93.71%) | 143 |
| post_money_valuation | round_2_to_round_3 | 2 (2.90%) | 1 (1.45%) | 66 (95.65%) | 69 |
| investor_ownership | round_2_to_round_3 | 0 (0.00%) | 0 (0.00%) | 55 (100.00%) | 55 |
| deal_size | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 143 (100.00%) | 143 |
| post_money_valuation | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 69 (100.00%) | 69 |
| investor_ownership | round_3_to_final | 0 (0.00%) | 0 (0.00%) | 55 (100.00%) | 55 |

## 6. 数值误差随阶段变化

| metric | stage | evaluated | MAE | MAPE | Median APE |
| --- | --- | ---: | ---: | ---: | ---: |
| deal_size | initial | 143 | 14.900 M USD | 3250.51% | 85.72% |
| deal_size | round_1 | 143 | 14.900 M USD | 3250.09% | 85.72% |
| deal_size | round_2 | 143 | 14.620 M USD | 3251.98% | 85.72% |
| deal_size | round_3 | 143 | 14.686 M USD | 3252.45% | 86.85% |
| deal_size | final | 143 | 14.686 M USD | 3252.45% | 86.85% |
| post_money_valuation | initial | 69 | 64.950 M USD | 289.76% | 67.15% |
| post_money_valuation | round_1 | 69 | 64.957 M USD | 289.97% | 67.15% |
| post_money_valuation | round_2 | 69 | 65.576 M USD | 291.88% | 67.15% |
| post_money_valuation | round_3 | 69 | 65.600 M USD | 292.23% | 67.15% |
| post_money_valuation | final | 69 | 65.600 M USD | 292.23% | 67.15% |
| investor_ownership | initial | 55 | 20.058 pct | 54.86% | 40.25% |
| investor_ownership | round_1 | 55 | 20.058 pct | 54.86% | 40.25% |
| investor_ownership | round_2 | 55 | 20.058 pct | 54.86% | 40.25% |
| investor_ownership | round_3 | 55 | 20.058 pct | 54.86% | 40.25% |
| investor_ownership | final | 55 | 20.058 pct | 54.86% | 40.25% |
