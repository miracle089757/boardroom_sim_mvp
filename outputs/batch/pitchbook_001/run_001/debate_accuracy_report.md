# 辩论前后准确度变化报告

- 分析案例数：69
- 融资额正确判定阈值：预测值相对真实值误差 <= 50%

## 1. 各阶段预测准确度

| stage | financing_initiation | financing_completion | deal_type | valuation_direction | deal_size |
| --- | ---: | ---: | ---: | ---: | ---: |
| initial | 69/69 (100.00%) | 66/69 (95.65%) | 41/69 (59.42%) | 20/28 (71.43%) | 30/67 (44.78%) |
| round_1 | 69/69 (100.00%) | 66/69 (95.65%) | 43/69 (62.32%) | 20/28 (71.43%) | 26/67 (38.81%) |
| round_2 | 69/69 (100.00%) | 66/69 (95.65%) | 45/69 (65.22%) | 20/28 (71.43%) | 26/67 (38.81%) |
| round_3 | 69/69 (100.00%) | 66/69 (95.65%) | 44/69 (63.77%) | 20/28 (71.43%) | 26/67 (38.81%) |
| final | 69/69 (100.00%) | 66/69 (95.65%) | 44/69 (63.77%) | 20/28 (71.43%) | 26/67 (38.81%) |

## 2. 辩论前 vs 辩论后

### initial_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 69 (100.00%) | 0 (0.00%) | 69 |
| financing_completion | 0 (0.00%) | 0 (0.00%) | 66 (95.65%) | 3 (4.35%) | 69 |
| deal_type | 7 (10.14%) | 4 (5.80%) | 37 (53.62%) | 21 (30.43%) | 69 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 1 (1.49%) | 5 (7.46%) | 25 (37.31%) | 36 (53.73%) | 67 |

## 3. 随辩论轮次推进的正确性变化

### initial_to_round_1

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 69 (100.00%) | 0 (0.00%) | 69 |
| financing_completion | 0 (0.00%) | 0 (0.00%) | 66 (95.65%) | 3 (4.35%) | 69 |
| deal_type | 4 (5.80%) | 2 (2.90%) | 39 (56.52%) | 24 (34.78%) | 69 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 4 (5.97%) | 26 (38.81%) | 37 (55.22%) | 67 |

### round_1_to_round_2

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 69 (100.00%) | 0 (0.00%) | 69 |
| financing_completion | 0 (0.00%) | 0 (0.00%) | 66 (95.65%) | 3 (4.35%) | 69 |
| deal_type | 3 (4.35%) | 1 (1.45%) | 42 (60.87%) | 23 (33.33%) | 69 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 1 (1.49%) | 1 (1.49%) | 25 (37.31%) | 40 (59.70%) | 67 |

### round_2_to_round_3

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 69 (100.00%) | 0 (0.00%) | 69 |
| financing_completion | 0 (0.00%) | 0 (0.00%) | 66 (95.65%) | 3 (4.35%) | 69 |
| deal_type | 0 (0.00%) | 1 (1.45%) | 44 (63.77%) | 24 (34.78%) | 69 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 26 (38.81%) | 41 (61.19%) | 67 |

### round_3_to_final

| metric | wrong->correct | correct->wrong | correct->correct | wrong->wrong | evaluated |
| --- | ---: | ---: | ---: | ---: | ---: |
| financing_initiation | 0 (0.00%) | 0 (0.00%) | 69 (100.00%) | 0 (0.00%) | 69 |
| financing_completion | 0 (0.00%) | 0 (0.00%) | 66 (95.65%) | 3 (4.35%) | 69 |
| deal_type | 0 (0.00%) | 0 (0.00%) | 44 (63.77%) | 25 (36.23%) | 69 |
| valuation_direction | 0 (0.00%) | 0 (0.00%) | 20 (71.43%) | 8 (28.57%) | 28 |
| deal_size | 0 (0.00%) | 0 (0.00%) | 26 (38.81%) | 41 (61.19%) | 67 |

## 4. 融资额是否更接近真实值

| transition | closer | farther | same | evaluated |
| --- | ---: | ---: | ---: | ---: |
| initial_to_final | 7 (10.45%) | 12 (17.91%) | 48 (71.64%) | 67 |
| initial_to_round_1 | 7 (10.45%) | 9 (13.43%) | 51 (76.12%) | 67 |
| round_1_to_round_2 | 4 (5.97%) | 8 (11.94%) | 55 (82.09%) | 67 |
| round_2_to_round_3 | 0 (0.00%) | 1 (1.49%) | 66 (98.51%) | 67 |
| round_3_to_final | 0 (0.00%) | 0 (0.00%) | 67 (100.00%) | 67 |

## 5. 融资额误差随阶段变化

| stage | evaluated | MAE (M USD) | MAPE | Median APE |
| --- | ---: | ---: | ---: | ---: |
| initial | 67 | 13.974 | 277.42% | 63.35% |
| round_1 | 67 | 14.079 | 292.50% | 69.70% |
| round_2 | 67 | 14.184 | 303.67% | 71.14% |
| round_3 | 67 | 14.187 | 303.72% | 71.14% |
| final | 67 | 14.187 | 303.72% | 71.14% |
