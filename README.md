# Boardroom Simulation MVP

这是一个最小可跑通版本的“多智能体公司董事会博弈”实验代码。代码面向 Linux 执行环境编写，使用 OpenAI-compatible Chat Completions 接口驱动智能体，需要提供 LLM API key。

当前第一版严格按“智能体角色编定”文档改为正样本 VC 交易回测：每个案例对应一家公司在真实 VC 交易发生前的董事会决策时点。Agent 只能看到该时点之前的公司、历史融资、员工、治理和投资人信息；当前轮真实结果只放在 `notes.labels` 中用于评测。

模拟输出聚焦：

1. 融资意向：`raise_now`、`wait`、`avoid`。
2. 预计融资额：`predicted_deal_size_usd_m`。
3. 预计交易类型：`predicted_deal_type`。
4. 估值方向：`up`、`flat`、`down`。
5. CEO 更换压力：`keep`、`monitor`、`replace`。

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
  --input input/02_03_pitchbook_sample_100_shared.xlsx \
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

## 输入数据格式

当前支持两种输入：

1. PitchBook Excel：`input/02_03_pitchbook_sample_100_shared.xlsx`。程序会自动筛选有 `postvaluation` 的 VC 交易并转换成 `BoardCase`。
2. 标准化 JSONL：每行一个已经转换好的 `BoardCase`。

真实结果字段，例如当前轮 `deal.dealsize`、`deal.dealtype`、`deal.vcround`、`deal.postvaluation`、`deal.dealstatus`、`deal.vcroundup_down_flat` 以及派生出的 24 个月 CEO 更换标签，只会保存在 `notes.labels` 中用于后续评测，不会进入 Agent 可见字段。

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
      "real_deal_type": "Later Stage VC",
      "real_valuation_direction_label": "up",
      "real_ceo_replacement_label": "replace"
    }
  }
}
```

## 当前边界

- 当前是 LLM 智能体，但聚合规则仍是确定性代码，便于批量统计。
- 当前只做正样本 VC 交易；因为没有负样本，不能严格评测“是否发起融资”，只能评测正样本下的融资规模、轮次、估值方向和 CEO 更换。
- 当前 Follow-on VC 的行为会参考 Lead VC 的立场，但没有完整基金组合约束。
- 当前从 Excel 只筛选有 `postvaluation` 的 VC 交易。
- 当前输出是研究实验用，不代表真实投资建议。

## 下一步扩展建议

1. 从 PitchBook 表格批量生成 `jsonl` 案例。
2. 增加规则 sanity check，与 LLM 决策并行对比。
3. 增加信息不对称：CEO/CTO/VC 看到不同字段。
4. 增加动态策略：每轮后更新角色坚持度和合作度。
5. 增加纵向序列：Seed -> Series A -> Series B -> Exit/Down round。
