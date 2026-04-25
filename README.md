# Boardroom Simulation MVP

这是一个最小可跑通版本的“多智能体公司董事会博弈”实验代码。代码面向 Linux 执行环境编写，使用 OpenAI-compatible Chat Completions 接口驱动智能体，需要提供 LLM API key。

第一版只聚焦三个事件：

1. 融资决策：是否批准、重新谈判或拒绝本轮融资。
2. 估值方向：本轮估值相对上一轮是上升、持平还是下降。
3. CEO 更换：保留、观察或更换 CEO。

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
  --input data/sample_cases.jsonl \
  --output outputs/sample_results.jsonl \
  --trace-output outputs/sample_traces.json
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

每行一个 JSON 案例。字段可以逐步扩充，MVP 中核心字段如下：

```json
{
  "case_id": "case_001",
  "company_name": "Example AI",
  "industry": "Artificial Intelligence",
  "round_type": "Series A",
  "deal_size_usd_m": 12.0,
  "previous_deal_size_usd_m": 5.0,
  "pre_money_valuation_usd_m": 42.0,
  "post_money_valuation_usd_m": 54.0,
  "previous_post_money_valuation_usd_m": 30.0,
  "runway_months": 8,
  "burn_multiple": 1.4,
  "founder_equity_pct": 42.0,
  "employee_growth_rate": 0.25,
  "engineering_headcount_growth_rate": 0.3,
  "tech_debt_risk": 0.35,
  "ceo_performance_risk": 0.25,
  "ceo_technical_alignment": 0.8,
  "lead_investor_reputation": 0.8,
  "lead_investor_conviction": 0.75,
  "followon_fund_capacity": 0.7,
  "market_temperature": "normal"
}
```

## 当前边界

- 当前是 LLM 智能体，但聚合规则仍是确定性代码，便于批量统计。
- 当前只做单轮融资董事会博弈，不做公司生命周期序列模拟。
- 当前 Follow-on VC 的行为会参考 Lead VC 的立场，但没有复杂基金组合约束。
- 当前输出是研究实验用，不代表真实投资建议。

## 下一步扩展建议

1. 从 PitchBook 表格批量生成 `jsonl` 案例。
2. 增加规则 sanity check，与 LLM 决策并行对比。
3. 增加信息不对称：CEO/CTO/VC 看到不同字段。
4. 增加动态策略：每轮后更新角色坚持度和合作度。
5. 增加纵向序列：Seed -> Series A -> Series B -> Exit/Down round。
