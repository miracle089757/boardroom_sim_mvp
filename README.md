# Boardroom Simulation MVP

这是一个最小可跑通版本的“多智能体公司董事会博弈”实验代码。代码面向 Linux 执行环境编写，使用 OpenAI-compatible Chat Completions 接口驱动智能体，需要提供 LLM API key。

当前第一版严格按“智能体角色编定”文档改为正样本 VC 交易回测：每个案例对应一家公司在真实 VC 交易发生前的董事会决策时点。Agent 只能看到该时点之前的公司、历史融资、员工、治理和投资人信息；当前轮真实结果只放在 `notes.labels` 中用于评测。

模拟输出聚焦：

1. 融资意向：`raise_now`、`wait`、`avoid`。
2. 预计融资额：`predicted_deal_size_usd_m`。
3. 预计投后估值：`predicted_post_money_valuation_usd_m`。
4. 预计投资人持股：`predicted_investor_ownership_pct`。
5. 预计交易类型：`predicted_deal_type`。
6. 估值方向：`up`、`flat`、`down`。

CEO 更换压力暂时不作为本轮预测目标。当前数据中的 24 个月 CEO 更换标签仍保留在 `notes.labels` 里用于审计，等评估标准修正后再纳入实验。

智能体角色严格采用“智能体角色编定”文档中的四层结构：

- L1 目标函数
- L2 注意力字段
- L3 启发式规则
- L4 交互协议

首批角色为：

- Founder_CEO
- CTO
- Lead_VC_Director
- Followon_VC_Director

## 目录结构

```text
boardroom_sim_mvp/
├── boardroom_sim/
│   ├── __init__.py
│   ├── agents.py
│   ├── io.py
│   ├── llm.py
│   ├── models.py
│   ├── pitchbook.py
│   ├── roles.py
│   └── simulator.py
├── data/
│   └── sample_cases.jsonl
├── outputs/
│   └── .gitkeep
└── run_experiment.py
```

## Linux 下运行

先设置 API key。不要把 key 写入代码或提交到仓库。

```bash
export BOARDROOM_LLM_API_KEY="your_api_key"
export BOARDROOM_LLM_BASE_URL="https://api.z.ai/api/paas/v4"
export BOARDROOM_LLM_MODEL="glm-4.7-flash"
```

默认配置使用 Z.AI 的 `glm-4.7-flash`。如果你使用 OpenAI、DeepSeek、OpenRouter、硅基流动或其他兼容 OpenAI Chat Completions 的服务，把 `BOARDROOM_LLM_BASE_URL` 和 `BOARDROOM_LLM_MODEL` 改成对应值即可。

```bash
cd boardroom_sim_mvp
python3 run_experiment.py \
  --input input/260524_02_03_pitchbook_sample_100_shared.xlsx \
  --output outputs/pitchbook_results.jsonl \
  --trace-output outputs/pitchbook_traces.json \
  --case-limit 3
```

也可以用命令行覆盖模型和 base URL：

```bash
python3 run_experiment.py \
  --input data/sample_cases.jsonl \
  --output outputs/sample_results.jsonl \
  --trace-output outputs/sample_traces.json \
  --model glm-4.7-flash \
  --base-url https://api.z.ai/api/paas/v4 \
  --temperature 0.2
```

运行完成后会生成：

- `outputs/sample_results.jsonl`：每个案例一行的结构化结果。
- `outputs/sample_traces.json`：包含每个案例的角色发言、初始判断、谈判过程和最终决议轨迹。

## 批量实验与准确率评估

如果已经有 `results.jsonl`，可以直接离线评估，不会再次调用 LLM：

```bash
python3 evaluate_results.py \
  --input outputs/pitchbook_results.jsonl \
  --metrics-output outputs/pitchbook_metrics.json \
  --case-metrics-output outputs/pitchbook_case_metrics.csv
```

评估会输出：

- 融资发起命中率：`financing_initiation_decision` 对比 `true_financing_initiated_label`。
- 交易类型准确率：`predicted_deal_type` 对比 `real_deal_type`。
- 估值方向准确率：`valuation_direction` 对比 `real_valuation_direction_label`，真实标签为 `unknown` 的样本会跳过。
- 数值误差：融资额、投后估值、投资人持股分别统计 `MAE`、`RMSE`、`MAPE`、`Median APE`、`±25%` 命中率、`±50%` 命中率；真实数值缺失或非正的样本会跳过该指标。

`financing_completion_view` 仍会输出，但当前样本几乎全部为已完成交易，因此暂不计入正确率统计。

批量运行使用 `run_batch_experiments.py`：

```bash
python3 run_batch_experiments.py \
  --input input/260524_02_03_pitchbook_sample_100_shared.xlsx \
  --output-dir outputs/batch/pitchbook_001 \
  --repeats 1 \
  --bargaining-rounds 3 \
  --history-limit 10
```

为了先快速验证流程，可以加 `--case-limit`：

```bash
python3 run_batch_experiments.py \
  --input input/260524_02_03_pitchbook_sample_100_shared.xlsx \
  --output-dir outputs/batch/smoke_test \
  --repeats 1 \
  --case-limit 3 \
  --bargaining-rounds 1 \
  --history-limit 3
```

批量输出目录结构：

```text
outputs/batch/pitchbook_001/
├── manifest.json
├── run_001/
│   ├── results.jsonl
│   ├── traces.json
│   ├── metrics.json
│   ├── case_metrics.csv
│   ├── debate_accuracy_report.md
│   ├── debate_accuracy_cases.csv
│   ├── baseline_history_only_results.jsonl
│   ├── baseline_history_only_metrics.json
│   ├── baseline_history_only_case_metrics.csv
│   ├── baseline_history_with_roles_results.jsonl
│   ├── baseline_history_with_roles_metrics.json
│   └── baseline_history_with_roles_case_metrics.csv
├── aggregate_metrics.json
├── case_metrics.csv
├── baseline_history_only_aggregate_metrics.json
├── baseline_history_only_case_metrics.csv
├── baseline_history_with_roles_aggregate_metrics.json
└── baseline_history_with_roles_case_metrics.csv
```

默认会额外运行两个单 agent baseline：

- `baseline_history_only`：只把已知历史字段发送给模型，不提供角色编定规则。
- `baseline_history_with_roles`：把已知历史字段和四个角色的编定规则一起发送给模型，但仍是单次单 agent 判断，不进行多智能体辩论。

如果运行中断，重新执行时加 `--resume`，已经完整生成 `results.jsonl` 的 run 会被跳过。若只想保存 compact result 和指标，不保存详细 trace，可以加 `--skip-traces`；若暂时不想跑 baseline，可以加 `--skip-baselines`。

`--history-limit` 控制每个历史记录字段最多保留最近多少条记录，默认是 `10`；设为 `0` 表示不提供历史列表，设为 `-1` 表示保留全部可构造历史记录。

如果需要分析“辩论前后预测发生了什么变化”，使用详细 trace 文件生成可读报告：

```bash
python3 analyze_debate_changes.py \
  --input outputs/batch/pitchbook_001/run_001/traces.json \
  --output outputs/batch/pitchbook_001/run_001/debate_changes_report.md \
  --case-csv-output outputs/batch/pitchbook_001/run_001/debate_changes_cases.csv
```

注意该分析依赖初始判断和每轮更新，因此应输入 `traces.json`；紧凑版 `results.jsonl` 不包含辩论前状态，无法单独还原变化过程。

如果需要进一步统计辩论让预测更接近真实结果还是偏离真实结果：

```bash
python3 analyze_debate_accuracy.py \
  --input outputs/batch/pitchbook_001/run_001/traces.json \
  --output outputs/batch/pitchbook_001/run_001/debate_accuracy_report.md \
  --case-csv-output outputs/batch/pitchbook_001/run_001/debate_accuracy_cases.csv \
  --baseline-results baseline_history_only=outputs/batch/pitchbook_001/run_001/baseline_history_only_results.jsonl \
  --baseline-results baseline_history_with_roles=outputs/batch/pitchbook_001/run_001/baseline_history_with_roles_results.jsonl \
  --deal-size-tolerance 0.50
```

批量运行会自动生成 `debate_accuracy_report.md` 和 `debate_accuracy_cases.csv`。上面的命令也可以对已有 trace 单独重跑报告。该报告会分别给出辩论前、每轮辩论后、最终结果的准确率，并统计 `wrong->correct`、`correct->wrong`、`correct->correct`、`wrong->wrong` 的比例。融资额、投后估值、投资人持股是连续变量，额外统计误差是更接近真实值还是更偏离真实值。

## 输入数据格式

当前支持两种输入：

1. PitchBook Excel：`input/260524_02_03_pitchbook_sample_100_shared.xlsx`。程序会自动筛选 VC-like 交易并转换成 `BoardCase`，不再要求目标交易有 `postvaluation`。
2. 标准化 JSONL：每行一个已经转换好的 `BoardCase`。

真实结果字段，例如当前轮 `deal.dealsize`、`deal.dealtype`、`deal.vcround`、`deal.postvaluation`、`deal.dealstatus`、`deal.vcroundup_down_flat` 以及派生出的 24 个月 CEO 更换标签，只会保存在 `notes.labels` 中，不会进入 Agent 可见字段。当前批量评估暂不统计 CEO 更换指标。

表格中的数值缺失会保留为 JSON `null`，不会再被填成 `0` 发送给 Agent。`business_status`、`company_financing_status`、`ownership_status` 等 PitchBook 快照状态字段会保留在案例中用于审计，但不进入角色可见字段，避免泄露决策时点之后的状态。

标准化 JSONL 的核心字段如下：

```json
{
  "case_id": "11830986_816183250T",
  "company_id": "11830986",
  "target_deal_id": "816183250T",
  "company_label": "11830986",
  "decision_date": "2011-11-14",
  "business_status": "Out of Business",
  "company_financing_status": "Formerly VC-backed",
  "ownership_status": "Acquired/Merged",
  "year_founded": 2007,
  "company_age_at_decision_years": 4.0,
  "primary_industry": "Alternative Energy Equipment",
  "industry_group": "Energy Equipment",
  "industry_sector": "Energy",
  "verticals": ["CleanTech", "Climate Tech"],
  "prior_vc_deal_count": 4,
  "prior_deal_date": "2010-01-07",
  "prior_deal_type": "Early Stage VC",
  "prior_vc_round": "4th Round",
  "prior_deal_size_usd_m": 350.0,
  "prior_post_money_valuation_usd_m": 1100.0,
  "prior_valuation_direction_label": "unknown",
  "employee_growth_rate": null,
  "current_ceo_is_founder": true,
  "notes": {
    "labels": {
      "true_financing_initiated_label": "raise_now",
      "real_deal_size_usd_m": 250.0,
      "real_post_money_valuation_usd_m": 2250.0,
      "real_investor_ownership_pct": 78.22,
      "real_deal_type": "Later Stage VC",
      "real_valuation_direction_label": "up"
    }
  }
}
```

## 当前边界

- 当前是 LLM 智能体，但聚合规则仍是确定性代码，便于批量统计。
- 当前只做正样本 VC-like 交易；因为没有负样本，不能严格评测“是否发起融资”，只能评测正样本下的融资规模、投后估值、投资人持股、轮次和估值方向。
- 当前交易完成标签极度不均衡，因此 `financing_completion_view` 暂不计入正确率。
- CEO 更换压力暂时从预测目标和批量评估中移除，后续需要重新定义标签构造和评估口径后再加回。
- 当前 Follow-on VC 的行为会参考 Lead VC 的立场，但没有完整基金组合约束。
- 当前从 Excel 可构造 212 条 VC-like 正样本；缺少真实数值标签的样本仍参与预测，但跳过对应数值指标的正确率统计。
- 当前输出是研究实验用，不代表真实投资建议。

## 下一步扩展建议

1. 从 PitchBook 表格批量生成 `jsonl` 案例。
2. 增加规则 sanity check，与 LLM 决策并行对比。
3. 增加信息不对称：CEO/CTO/VC 看到不同字段。
4. 增加动态策略：每轮后更新角色坚持度和合作度。
5. 增加纵向序列：Seed -> Series A -> Series B -> Exit/Down round。
