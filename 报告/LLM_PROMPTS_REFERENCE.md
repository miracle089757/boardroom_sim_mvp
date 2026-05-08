# LLM Prompt 汇总（中英文对照）

本文档整理当前项目中所有可能发送给 LLM 的 prompt 模板。代码位置主要在：

- `boardroom_sim/agents.py`：角色系统 prompt、初始判断 prompt、辩论更新 prompt。
- `boardroom_sim/llm.py`：LLM 返回非 JSON 时的重试修正 prompt。

说明：

- 下文中的 `{...}` 表示运行时动态插入的内容。
- `system` 和 `user` 是发送给 OpenAI-compatible Chat Completions API 的消息角色。
- 角色政策、案例字段、上下文和历史发言均以 JSON 字符串插入 prompt。

## 1. 初始角色判断调用

触发位置：`BoardAgent.evaluate()`

用途：每个角色在正式辩论前，根据自己可见字段和已经发言角色的上下文，给出初始判断。

实际发送的 messages：

```python
[
  {"role": "system", "content": SYSTEM_PROMPT},
  {"role": "user", "content": DECISION_PROMPT}
]
```

### 1.1 System Prompt

**English 原文**

```text
You are an LLM agent in a controlled social simulation of startup boardroom governance. You must strictly follow the assigned four-layer role policy. This is a point-in-time positive-sample backtest: the current target transaction outcomes are hidden from you. Use only visible pre-decision fields, role policy, and prior board context. Return valid JSON only.
```

**中文对照**

```text
你是一个用于初创公司董事会治理受控社会模拟的 LLM 智能体。你必须严格遵守被分配的四层角色规则。这是一个时点回测正样本实验：当前目标交易的真实结果对你隐藏。你只能使用可见的决策前字段、角色规则和此前董事会上下文。只返回有效 JSON。
```

### 1.2 User Prompt: 初始判断

**English 原文模板**

```text
You are now acting as role: {role_name}.

Strict four-layer role policy:
{role_policy_json}

Visible pre-decision fields for this role only:
{observed_fields_json}

Minimal shared case metadata:
{
  "case_id": "{case_id}",
  "company_label": "{company_label}",
  "company_id": "{company_id}",
  "decision_date": "{decision_date}",
  "primary_industry": "{primary_industry}"
}

Data handling rule:
- JSON null means the value is missing or unobserved. Do not interpret null as zero.
- Treat PitchBook snapshot company status fields as unavailable unless they appear in your visible fields.

Prior board context from roles that have already spoken:
{context_payload_json}

Task:
Predict this role's point-in-time board stance. Do not assume or reveal current target-deal labels.

Hard consistency rules:
- If financing_intent is "raise_now", predicted_deal_size_usd_m must be greater than 0.
- If financing_intent is "wait" or "avoid", predicted_deal_size_usd_m may be 0.
- When financing_intent is "raise_now" and exact amount is not clear, estimate a plausible positive amount from visible prior_deal_size_usd_m, prior_raised_to_date_usd_m, prior_vc_round, company age, and role policy. Do not use hidden current-deal labels.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Do not copy numeric placeholders from the schema. Return values that are consistent with your own rationale.

Allowed labels:
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down
- ceo_replacement_view: keep, monitor, replace

Return one JSON object only with this schema:
{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "ceo_replacement_view": "keep|monitor|replace",
  "satisfaction_score": 50,
  "rationale": ["short reason 1", "short reason 2"]
}
```

**中文对照模板**

```text
你现在扮演的角色是：{role_name}。

严格的四层角色规则：
{role_policy_json}

该角色唯一可见的决策前字段：
{observed_fields_json}

最小共享案例元数据：
{
  "case_id": "{case_id}",
  "company_label": "{company_label}",
  "company_id": "{company_id}",
  "decision_date": "{decision_date}",
  "primary_industry": "{primary_industry}"
}

数据处理规则：
- JSON null 表示该值缺失或未观测。不要把 null 理解为 0。
- 除非 PitchBook 快照状态字段出现在你的可见字段里，否则应视为不可用。

此前已经发言角色提供的董事会上下文：
{context_payload_json}

任务：
预测该角色在当前时点的董事会立场。不要假设或泄露当前目标交易的真实标签。

硬性一致性规则：
- 如果 financing_intent 是 "raise_now"，predicted_deal_size_usd_m 必须大于 0。
- 如果 financing_intent 是 "wait" 或 "avoid"，predicted_deal_size_usd_m 可以为 0。
- 当 financing_intent 是 "raise_now" 且具体金额不清楚时，需要根据可见的 prior_deal_size_usd_m、prior_raised_to_date_usd_m、prior_vc_round、公司年龄和角色规则估计一个合理的正数。不要使用隐藏的当前交易真实标签。
- satisfaction_score 必须是 0-100 分，其中 0 表示完全不可接受，50 表示中性或信息不足，100 表示完全符合该角色目标。
- 不要照抄 schema 中的数字占位符。返回值必须与你自己的理由一致。

允许的标签：
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down
- ceo_replacement_view: keep, monitor, replace

只返回一个 JSON 对象，结构如下：
{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "ceo_replacement_view": "keep|monitor|replace",
  "satisfaction_score": 50,
  "rationale": ["简短理由 1", "简短理由 2"]
}
```

## 2. 辩论轮次调用

触发位置：`BoardAgent.bargaining_step()`

用途：每个辩论轮中，每个角色根据当前提案、自己的当前判断、其他角色上下文和此前发言，生成一句董事会谈判发言，并更新自己的判断。

实际发送的 messages：

```python
[
  {"role": "system", "content": SYSTEM_PROMPT},
  {"role": "user", "content": BARGAINING_PROMPT}
]
```

其中 `SYSTEM_PROMPT` 与第 1.1 节完全相同。

### 2.1 User Prompt: 辩论发言与立场更新

**English 原文模板**

```text
You are now acting as role: {role_name}.

Strict four-layer role policy:
{role_policy_json}

Visible pre-decision fields for this role only:
{observed_fields_json}

Current aggregated proposal:
{proposal_json}

Your current prediction:
{current_prediction_json}

Board context:
{context_payload_json}

Prior bargaining messages:
{prior_messages_json}

Data handling rule:
- JSON null means the value is missing or unobserved. Do not interpret null as zero.
- Treat PitchBook snapshot company status fields as unavailable unless they appear in your visible fields.

Hard consistency rules:
- If financing_intent is "raise_now", predicted_deal_size_usd_m must be greater than 0.
- If financing_intent is "wait" or "avoid", predicted_deal_size_usd_m may be 0.
- When financing_intent is "raise_now" and exact amount is not clear, estimate a plausible positive amount from visible prior_deal_size_usd_m, prior_raised_to_date_usd_m, prior_vc_round, company age, current proposal, bargaining history, and role policy. Do not use hidden current-deal labels.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Do not copy numeric placeholders from the schema. Return values that are consistent with your updated rationale.

Write one concise boardroom bargaining message for round {round_index + 1}, then update your prediction if the discussion changes your stance.
The message must:
- focus on financing timing, financing amount, deal type, valuation direction, or CEO replacement;
- reflect your role's L1 goals, L2 attention, L3 heuristics, and L4 protocol;
- avoid generic corporate slogans;
- be one to three sentences.

Return one JSON object only:
{
  "message": "your boardroom message",
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "ceo_replacement_view": "keep|monitor|replace",
  "satisfaction_score": 50,
  "rationale": ["short reason 1", "short reason 2"]
}
```

**中文对照模板**

```text
你现在扮演的角色是：{role_name}。

严格的四层角色规则：
{role_policy_json}

该角色唯一可见的决策前字段：
{observed_fields_json}

当前综合提案：
{proposal_json}

你当前的预测：
{current_prediction_json}

董事会上下文：
{context_payload_json}

此前辩论发言：
{prior_messages_json}

数据处理规则：
- JSON null 表示该值缺失或未观测。不要把 null 理解为 0。
- 除非 PitchBook 快照状态字段出现在你的可见字段里，否则应视为不可用。

硬性一致性规则：
- 如果 financing_intent 是 "raise_now"，predicted_deal_size_usd_m 必须大于 0。
- 如果 financing_intent 是 "wait" 或 "avoid"，predicted_deal_size_usd_m 可以为 0。
- 当 financing_intent 是 "raise_now" 且具体金额不清楚时，需要根据可见的 prior_deal_size_usd_m、prior_raised_to_date_usd_m、prior_vc_round、公司年龄、当前提案、辩论历史和角色规则估计一个合理的正数。不要使用隐藏的当前交易真实标签。
- satisfaction_score 必须是 0-100 分，其中 0 表示完全不可接受，50 表示中性或信息不足，100 表示完全符合该角色目标。
- 不要照抄 schema 中的数字占位符。返回值必须与你更新后的理由一致。

请为第 {round_index + 1} 轮写一句简洁的董事会谈判发言，然后在讨论改变你立场时更新你的预测。
该发言必须：
- 聚焦于融资时点、融资金额、交易类型、估值方向或 CEO 更换；
- 体现你的 L1 目标、L2 注意字段、L3 启发式规则和 L4 互动协议；
- 避免空泛的公司口号；
- 长度为一到三句话。

只返回一个 JSON 对象：
{
  "message": "你的董事会发言",
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "ceo_replacement_view": "keep|monitor|replace",
  "satisfaction_score": 50,
  "rationale": ["简短理由 1", "简短理由 2"]
}
```

## 3. JSON 解析失败后的重试 Prompt

触发位置：`LLMClient.complete_json()`

用途：如果 LLM 上一次回复不能被解析成一个 JSON 对象，系统会把模型上一次的原文回复作为一条 `assistant` 消息加入上下文，然后追加下面的 `user` 修正提示。

实际追加的 messages：

```python
[
  {"role": "assistant", "content": "{last_invalid_model_response}"},
  {"role": "user", "content": RETRY_JSON_PROMPT}
]
```

### 3.1 User Prompt: JSON 修正提示

**English 原文**

```text
Your previous answer was not valid JSON. Return one JSON object only.
```

**中文对照**

```text
你上一次的回答不是有效 JSON。请只返回一个 JSON 对象。
```

## 4. 运行时动态插入内容说明

- `{role_name}`：当前角色名称，例如 `Founder_CEO`、`CTO`、`Lead_VC_Director`、`Followon_VC_Director`。
- `{role_policy_json}`：该角色完整四层规则，来自 `roles.py`。
- `{observed_fields_json}`：该角色可见字段，来自 `RolePolicy.layer_2_attention_fields` 与 `BoardCase`。
- `{context_payload_json}`：已经给出判断的角色上下文，包含融资意向、完成判断、预测金额、轮次、估值方向、CEO 更换观点、满意度和理由。
- `{proposal_json}`：当前聚合提案，包含建议融资额、交易类型、估值方向、估计稀释率、投资人保护强度、技术预算保护和 CEO milestone 要求。
- `{current_prediction_json}`：当前角色上一轮或初始的预测。
- `{prior_messages_json}`：此前辩论轮中已经产生的角色发言和更新后的判断。
- `{last_invalid_model_response}`：模型上一轮无法解析为 JSON 的原始回复。

## 5. 不会直接发送给 LLM 的文本

- `opening_statement()` 生成的开场陈述主要写入 trace，用于报告和过程记录；它不是单独的 LLM prompt。
- `render_trace_report.py` 生成的是人类可读报告，不会发送给 LLM。
- `README.md`、教程报告和本文件仅用于人工查阅，不会参与模型调用。
