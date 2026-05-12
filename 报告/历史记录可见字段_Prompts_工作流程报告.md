# 历史记录可见字段、Prompt 与实验流程报告

## 1. 本次修改概览

本次修改给案例增加了三类历史记录字段，并支持在命令行中控制每类历史记录最多保留多少条。

命令行参数：

```bash
--history-limit 10
```

含义：

- `10`：每个历史字段最多保留最近 10 条记录，默认值。
- `3`：每个历史字段最多保留最近 3 条记录。
- `0`：不向角色提供历史列表。
- `-1`：不截断，保留全部可构造历史记录。

当前新增的历史字段：

| 字段 | 谁主要可见 | 含义 |
| --- | --- | --- |
| `prior_company_deal_history` | Founder_CEO、CTO | 决策日前同一家公司已经发生的历史 VC-like 交易记录。 |
| `prior_lead_investor_deal_history` | Lead_VC_Director | 本轮目标交易中可识别的领投投资人，在决策日前参与过的历史投资记录。 |
| `prior_followon_investor_deal_history` | Followon_VC_Director | 本轮目标交易中可识别的跟投或非领投投资人，在决策日前参与过的历史投资记录。 |

注意：投资角色的“自己的投资历史”现在用本轮目标交易中的投资人来代表。本轮投资人身份会进入角色可见信息，但本轮真实交易金额、估值、持股比例、完成状态等结果标签仍然隐藏，只用于评估。投资人历史记录本身只保留这些投资人在 `decision_date` 之前参与过的交易，当前目标交易不会被放入历史列表。

## 2. 历史记录字段结构

### 2.1 公司历史交易字段

`prior_company_deal_history` 是一个列表，每个元素是一条历史交易摘要：

| 子字段 | 含义 |
| --- | --- |
| `deal_id` | 历史交易 ID。 |
| `company_id` | 公司 ID。 |
| `deal_date` | 历史交易日期。 |
| `deal_class` | PitchBook 交易类别。 |
| `deal_type` | 交易类型，例如 Seed Round、Early Stage VC、Later Stage VC。 |
| `deal_status` | 历史交易状态。 |
| `vc_round` | VC 轮次标签。 |
| `deal_size_usd_m` | 融资额，单位百万美元。 |
| `pre_money_valuation_usd_m` | 投前估值，单位百万美元。 |
| `post_money_valuation_usd_m` | 投后估值，单位百万美元。 |
| `investor_ownership_pct` | 投资人持股比例。 |
| `raised_to_date_usd_m` | 截至该轮后的累计融资额。 |
| `investor_count` | 该轮投资人数量。 |
| `new_investor_count` | 该轮新投资人数量。 |
| `followon_investor_count` | 该轮跟投投资人数量。 |
| `valuation_markup_multiple` | 相对上一条历史投后估值的倍数。 |
| `valuation_direction_label` | up / flat / down / unknown。 |

### 2.2 投资人历史投资字段

`prior_lead_investor_deal_history` 和 `prior_followon_investor_deal_history` 的基础交易字段与公司历史交易一致，并额外包含投资人相关字段：

| 子字段 | 含义 |
| --- | --- |
| `investor_id` | 投资人 ID。 |
| `investor_primary_type` | 投资人主类型，例如 Venture Capital、Asset Manager。 |
| `investor_status_in_deal` | 投资人在该交易中的身份，例如 New Investor、Follow-On Investor。 |
| `is_lead_investor` | 是否为该交易领投方。 |
| `investor_investment_amount_usd_m` | 该投资人在该交易中的投资额，单位百万美元。 |
| `investor_preferred_deal_size_min_usd_m` | 投资人偏好交易规模下限。 |
| `investor_preferred_deal_size_max_usd_m` | 投资人偏好交易规模上限。 |
| `investor_preferred_company_valuation_min_usd_m` | 投资人偏好公司估值下限。 |
| `investor_preferred_company_valuation_max_usd_m` | 投资人偏好公司估值上限。 |

## 3. 各角色可见字段

所有角色都会在 prompt 中看到极少量共享元数据：

| 字段 | 解释 |
| --- | --- |
| `case_id` | 模拟案例 ID。 |
| `company_label` | 公司展示标签。 |
| `company_id` | PitchBook 公司 ID。 |
| `decision_date` | 决策时点。 |
| `primary_industry` | 公司主行业。 |

除此之外，每个角色只能看到其 L2 attention fields 中列出的字段。

### 3.1 Founder_CEO

Founder_CEO 主要关注公司融资历史、控制权、董事会结构和经营资源。

| 字段 | 解释 |
| --- | --- |
| `prior_company_deal_history` | 同公司历史融资交易列表，帮助 Founder 判断融资节奏、估值路径和稀释压力。 |
| `prior_deal_size_usd_m` | 上一笔融资额。 |
| `prior_post_money_valuation_usd_m` | 上一笔投后估值。 |
| `prior_valuation_markup_multiple` | 上一笔估值相对再上一笔估值的倍数。 |
| `prior_valuation_direction_label` | 上一笔估值方向。 |
| `prior_deal_type` | 上一笔交易类型。 |
| `prior_vc_round` | 上一笔 VC 轮次。 |
| `prior_raised_to_date_usd_m` | 上一轮后累计融资额。 |
| `prior_investor_ownership_pct` | 上一轮后投资人持股比例。 |
| `prior_lead_investor_count` | 上一轮领投方数量。 |
| `prior_lead_investor_types` | 上一轮领投方类型。 |
| `employee_count_at_decision` | 决策时点前最近员工数。 |
| `employee_growth_rate` | 员工增长率。 |
| `founder_count` | 可识别创始人数。 |
| `current_ceo_is_founder` | CEO 是否可识别为 founder-CEO。 |
| `board_member_count` | 董事会成员数量。 |
| `investor_board_member_count` | 投资人董事数量。 |

### 3.2 CTO

CTO 主要关注技术交付能力、团队资源、行业上下文和公司自身历史。

| 字段 | 解释 |
| --- | --- |
| `prior_company_deal_history` | 同公司历史融资交易列表，帮助 CTO 判断资金节奏是否支持技术路线。 |
| `prior_deal_size_usd_m` | 上一笔融资额。 |
| `prior_raised_to_date_usd_m` | 上一轮后累计融资额。 |
| `employee_count_at_decision` | 决策时点前最近员工数。 |
| `previous_employee_count` | 上一条员工数记录。 |
| `employee_growth_rate` | 员工增长率。 |
| `engineering_role_count` | 可识别工程/技术岗位人数。 |
| `executive_role_count` | 可识别高管人数。 |
| `primary_industry` | 公司主行业。 |
| `industry_group` | 行业组。 |
| `industry_sector` | 行业部门。 |
| `verticals` | 垂直赛道标签。 |
| `keywords` | 公司关键词。 |
| `description` | 公司业务描述。 |
| `company_age_at_decision_years` | 决策时点公司年龄。 |

### 3.3 Lead_VC_Director

Lead_VC_Director 主要关注估值纪律、历史投资偏好、董事会影响力和领投方风险。

| 字段 | 解释 |
| --- | --- |
| `prior_lead_investor_deal_history` | 本轮目标交易领投方的历史投资记录，帮助 Lead VC 判断该投资方的历史票据规模、偏好和风险承受模式。 |
| `prior_post_money_valuation_usd_m` | 上一笔投后估值。 |
| `prior_pre_money_valuation_usd_m` | 上一笔投前估值。 |
| `prior_valuation_markup_multiple` | 上一笔估值相对再上一笔估值的倍数。 |
| `prior_valuation_direction_label` | 上一笔估值方向。 |
| `prior_deal_size_usd_m` | 上一笔融资额。 |
| `prior_raised_to_date_usd_m` | 上一轮后累计融资额。 |
| `prior_investor_ownership_pct` | 上一轮后投资人持股比例。 |
| `prior_investor_count` | 上一轮投资人总数。 |
| `prior_new_investor_count` | 上一轮新投资人数量。 |
| `prior_followon_investor_count` | 上一轮跟投投资人数量。 |
| `prior_lead_investor_count` | 上一轮领投方数量。 |
| `prior_lead_investor_amount_share` | 上一轮领投方披露金额占比。 |
| `prior_lead_preferred_deal_size_min_usd_m` | 上一轮领投方偏好交易规模下限。 |
| `prior_lead_preferred_deal_size_max_usd_m` | 上一轮领投方偏好交易规模上限。 |
| `prior_lead_preferred_company_valuation_min_usd_m` | 上一轮领投方偏好公司估值下限。 |
| `prior_lead_preferred_company_valuation_max_usd_m` | 上一轮领投方偏好公司估值上限。 |
| `employee_growth_rate` | 员工增长率。 |
| `similar_company_count` | PitchBook 相似公司数量。 |
| `board_member_count` | 董事会成员数量。 |
| `investor_board_member_count` | 投资人董事数量。 |

### 3.4 Followon_VC_Director

Followon_VC_Director 主要关注 pro-rata、跟投纪律、被领投方稀释的风险和历史跟投模式。

| 字段 | 解释 |
| --- | --- |
| `prior_followon_investor_deal_history` | 本轮目标交易跟投或非领投投资人的历史投资记录，帮助 Follow-on VC 判断历史跟投行为和投资规模。 |
| `prior_deal_size_usd_m` | 上一笔融资额。 |
| `prior_post_money_valuation_usd_m` | 上一笔投后估值。 |
| `prior_valuation_markup_multiple` | 上一笔估值相对再上一笔估值的倍数。 |
| `prior_valuation_direction_label` | 上一笔估值方向。 |
| `prior_investor_ownership_pct` | 上一轮后投资人持股比例。 |
| `prior_investor_count` | 上一轮投资人总数。 |
| `prior_followon_investor_count` | 上一轮跟投投资人数量。 |
| `prior_lead_investor_count` | 上一轮领投方数量。 |
| `prior_lead_investor_types` | 上一轮领投方类型。 |
| `prior_lead_investor_amount_share` | 上一轮领投方披露金额占比。 |
| `prior_lead_preferred_deal_size_min_usd_m` | 上一轮领投方偏好交易规模下限。 |
| `prior_lead_preferred_deal_size_max_usd_m` | 上一轮领投方偏好交易规模上限。 |
| `employee_growth_rate` | 员工增长率。 |
| `similar_company_count` | PitchBook 相似公司数量。 |

## 4. 实验中可能用到的 Prompt

下面列出的是模板。实际运行时，`{...}` 会被替换为具体案例字段、角色规则、历史记录、已有讨论上下文等。

### 4.1 多智能体角色 system prompt

英文模板：

```text
You are an LLM agent in a controlled social simulation of startup boardroom governance.
You must strictly follow the assigned four-layer role policy. This is a point-in-time
positive-sample backtest: the current target transaction outcomes are hidden from you.
Use only visible pre-decision fields, role policy, and prior board context. Return valid JSON only.
```

中文翻译：

```text
你是一个用于初创公司董事会治理社会模拟的 LLM 智能体。
你必须严格遵守被分配的四层角色规则。本实验是一个基于决策时点的正样本回测：
当前目标交易的真实结果对你隐藏。
你只能使用可见的决策前字段、角色规则和已有董事会上下文。只返回合法 JSON。
```

### 4.2 初始角色判断 prompt

英文模板：

```text
You are now acting as role: {role_name}.

Strict four-layer role policy:
{role_policy_json}

Visible pre-decision fields for this role only:
{observed_fields_json}

Minimal shared case metadata:
{case_metadata_json}

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
- predicted_post_money_valuation_usd_m is the expected post-money valuation in million USD. Estimate it from visible prior valuation, valuation direction, company stage, and role policy; use 0 only when no defensible estimate is possible.
- predicted_investor_ownership_pct is the expected investor ownership percentage after the financing. It must be between 0 and 100; use 0 only when no defensible estimate is possible.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Do not copy numeric placeholders from the schema. Return values that are consistent with your own rationale.

Allowed labels:
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

Return one JSON object only with this schema:
{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "satisfaction_score": 50,
  "rationale": ["short reason 1", "short reason 2"]
}
```

中文翻译：

```text
你现在扮演的角色是：{role_name}。

严格的四层角色规则：
{role_policy_json}

仅该角色可见的决策前字段：
{observed_fields_json}

最小共享案例元数据：
{case_metadata_json}

数据处理规则：
- JSON null 表示该值缺失或未观测到，不要把 null 理解为 0。
- 除非 PitchBook 快照状态字段出现在你的可见字段中，否则应视为不可用。

此前已经发言角色带来的董事会上下文：
{context_payload_json}

任务：
预测该角色在当前决策时点的董事会立场。不要假设或泄露当前目标交易的真实标签。

硬性一致性规则：
- 如果 financing_intent 是 "raise_now"，predicted_deal_size_usd_m 必须大于 0。
- 如果 financing_intent 是 "wait" 或 "avoid"，predicted_deal_size_usd_m 可以为 0。
- 当 financing_intent 是 "raise_now" 且确切金额不清楚时，应根据可见的上一轮融资额、累计融资额、VC 轮次、公司年龄和角色规则估计一个合理的正数。不要使用隐藏的当前交易标签。
- predicted_post_money_valuation_usd_m 是预期投后估值，单位百万美元。应根据可见历史估值、估值方向、公司阶段和角色规则估计；只有在无法给出可辩护估计时才用 0。
- predicted_investor_ownership_pct 是融资后预期投资人持股比例，必须在 0 到 100 之间；只有在无法给出可辩护估计时才用 0。
- satisfaction_score 必须是 0 到 100 之间的分数，0 表示完全不可接受，50 表示中性或信息不足，100 表示完全符合该角色目标。
- 不要照抄 schema 中的数字占位符。返回值必须和你的理由一致。

允许的标签：
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

只返回一个 JSON 对象，结构如下：
{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "satisfaction_score": 50,
  "rationale": ["简短理由 1", "简短理由 2"]
}
```

### 4.3 辩论轮次 prompt

英文模板：

```text
You are now acting as role: {role_name}.

Strict four-layer role policy:
{role_policy_json}

Visible pre-decision fields for this role only:
{observed_fields_json}

Current aggregated proposal:
{proposal_json}

Your current prediction:
{current_decision_json}

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
- predicted_post_money_valuation_usd_m is the expected post-money valuation in million USD. Estimate it from visible prior valuation, valuation direction, company stage, current proposal, bargaining history, and role policy; use 0 only when no defensible estimate is possible.
- predicted_investor_ownership_pct is the expected investor ownership percentage after the financing. It must be between 0 and 100; use 0 only when no defensible estimate is possible.
- satisfaction_score must be a 0-100 score, where 0 means completely unacceptable, 50 means neutral or not enough information, and 100 means fully aligned with this role's goals.
- Do not copy numeric placeholders from the schema. Return values that are consistent with your updated rationale.

Write one concise boardroom bargaining message for round {round_index}, then update your prediction if the discussion changes your stance.
The message must:
- focus on financing timing, financing amount, deal type, valuation direction, or investor protections;
- reflect your role's L1 goals, L2 attention, L3 heuristics, and L4 protocol;
- avoid generic corporate slogans;
- be one to three sentences.

Return one JSON object only:
{
  "message": "your boardroom message",
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "satisfaction_score": 50,
  "rationale": ["short reason 1", "short reason 2"]
}
```

中文翻译：

```text
你现在扮演的角色是：{role_name}。

严格的四层角色规则：
{role_policy_json}

仅该角色可见的决策前字段：
{observed_fields_json}

当前聚合提案：
{proposal_json}

你当前的预测：
{current_decision_json}

董事会上下文：
{context_payload_json}

此前的辩论发言：
{prior_messages_json}

数据处理规则：
- JSON null 表示该值缺失或未观测到，不要把 null 理解为 0。
- 除非 PitchBook 快照状态字段出现在你的可见字段中，否则应视为不可用。

硬性一致性规则：
- 如果 financing_intent 是 "raise_now"，predicted_deal_size_usd_m 必须大于 0。
- 如果 financing_intent 是 "wait" 或 "avoid"，predicted_deal_size_usd_m 可以为 0。
- 当 financing_intent 是 "raise_now" 且确切金额不清楚时，应根据可见的上一轮融资额、累计融资额、VC 轮次、公司年龄、当前提案、辩论历史和角色规则估计一个合理的正数。不要使用隐藏的当前交易标签。
- predicted_post_money_valuation_usd_m 是预期投后估值，单位百万美元。应根据可见历史估值、估值方向、公司阶段、当前提案、辩论历史和角色规则估计；只有在无法给出可辩护估计时才用 0。
- predicted_investor_ownership_pct 是融资后预期投资人持股比例，必须在 0 到 100 之间；只有在无法给出可辩护估计时才用 0。
- satisfaction_score 必须是 0 到 100 之间的分数，0 表示完全不可接受，50 表示中性或信息不足，100 表示完全符合该角色目标。
- 不要照抄 schema 中的数字占位符。返回值必须和你更新后的理由一致。

请为第 {round_index} 轮写一句简洁的董事会辩论发言；如果讨论改变了你的立场，请更新你的预测。
发言必须：
- 聚焦融资时机、融资金额、交易类型、估值方向或投资人保护；
- 体现你的 L1 目标、L2 注意力字段、L3 启发式规则和 L4 交互协议；
- 避免泛泛的企业口号；
- 长度为一到三句话。

只返回一个 JSON 对象：
{
  "message": "你的董事会发言",
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "satisfaction_score": 50,
  "rationale": ["简短理由 1", "简短理由 2"]
}
```

### 4.4 单 agent baseline system prompt

英文模板：

```text
You are a single-agent baseline for a controlled startup financing backtest.
Use only the provided historical point-in-time fields. Do not infer or reveal hidden labels.
Return valid JSON only.
```

中文翻译：

```text
你是一个用于受控初创公司融资回测的单 agent baseline。
你只能使用提供的历史决策时点字段。不要推断或泄露隐藏标签。
只返回合法 JSON。
```

### 4.5 单 agent baseline user prompt

英文模板：

```text
Historical point-in-time case fields:
{historical_case_fields_json}

Role policy rules:
{role_rules_or_not_provided}

Task:
Predict the financing outcome for this case. If role policy rules are provided, synthesize them in one single-agent judgment; do not simulate a debate.

Data handling rule:
- JSON null means missing or unobserved. Do not interpret null as zero.
- Do not use current target-deal labels; they are not included in the payload.
- predicted_post_money_valuation_usd_m is the expected post-money valuation in million USD.
- predicted_investor_ownership_pct is the expected investor ownership percentage after the financing, from 0 to 100.

Allowed labels:
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

Return one JSON object only with this schema:
{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "rationale": ["short reason 1", "short reason 2"]
}
```

中文翻译：

```text
历史决策时点案例字段：
{historical_case_fields_json}

角色规则：
{role_rules_or_not_provided}

任务：
预测该案例的融资结果。如果提供了角色规则，请把这些规则综合成一个单 agent 判断；不要模拟辩论。

数据处理规则：
- JSON null 表示缺失或未观测到，不要把 null 理解为 0。
- 不要使用当前目标交易标签；这些标签不会出现在输入 payload 中。
- predicted_post_money_valuation_usd_m 是预期投后估值，单位百万美元。
- predicted_investor_ownership_pct 是融资后预期投资人持股比例，范围为 0 到 100。

允许的标签：
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

只返回一个 JSON 对象，结构如下：
{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "rationale": ["简短理由 1", "简短理由 2"]
}
```

### 4.6 JSON 修复 prompt

如果模型没有返回合法 JSON，LLM 客户端会把上一次回答附回去，并追加如下修复 prompt。

英文模板：

```text
Your previous answer was not valid JSON. Return one JSON object only.
```

中文翻译：

```text
你上一次的回答不是合法 JSON。请只返回一个 JSON 对象。
```

## 5. 实验工作流程

### 5.1 多智能体辩论实验流程

1. 读取 PitchBook Excel 或标准化 JSONL。
2. 如果输入是 PitchBook Excel，先筛选 VC-like 目标交易，当前全量为 212 条正样本。
3. 对每个目标交易确定 `decision_date`，只构造该日期之前可见的历史信息。
4. 构造同公司历史交易列表、本轮目标交易领投方历史投资列表、本轮目标交易跟投或非领投方历史投资列表，并按 `--history-limit` 截断；投资人历史列表会排除当前目标交易本身。
5. 为每个案例生成 `BoardCase`，真实目标交易结果只放入 `notes.labels`，不进入角色可见字段。
6. 依照固定发言顺序创建四个角色：Founder_CEO、CTO、Lead_VC_Director、Followon_VC_Director。
7. 每个角色只读取自己的 L2 attention fields 和最小共享元数据。
8. 每个角色先做一次 private assessment，输出融资意向、完成判断、融资额、投后估值、投资人持股、交易类型、估值方向、满意度和理由。
9. 系统根据角色预测聚合出初始融资提案。
10. 进入若干轮 bargaining。每轮中，各角色看到当前提案、自己的当前预测、其他角色上下文和历史发言，然后给出一段发言并更新预测。
11. 每轮结束后，系统重新聚合提案。
12. 所有轮次结束后，系统聚合最终预测并写入 `results.jsonl` 和 `traces.json`。
13. 评估脚本读取真实标签，统计可评估字段的准确率和数值误差；缺失真实数值标签的样本会跳过对应指标。
14. 生成 `debate_accuracy_report.md`，展示辩论前、每轮后、最终结果以及 baseline 对比。

### 5.2 单 agent baseline 流程

1. 对同一批 `BoardCase` 逐个运行单 agent baseline。
2. `baseline_history_only` 只接收历史字段，不接收角色编定规则。
3. `baseline_history_with_roles` 接收历史字段和四个角色的完整规则，但仍然只做一次单 agent 综合判断。
4. baseline 输出与多智能体最终结果相同的核心预测字段。
5. baseline 使用同一套评估函数，并写入单独的 JSON/CSV 指标文件。
6. baseline 汇总结果也会进入 `debate_accuracy_report.md` 的“单 Agent Baseline 对比”小节。

## 6. 推荐运行命令

快速测试：

```bash
python3 run_batch_experiments.py \
  --input input/02_03_pitchbook_sample_100_shared.xlsx \
  --output-dir outputs/batch/smoke_history \
  --repeats 1 \
  --case-limit 3 \
  --bargaining-rounds 1 \
  --history-limit 3
```

正式运行：

```bash
python3 run_batch_experiments.py \
  --input input/02_03_pitchbook_sample_100_shared.xlsx \
  --output-dir outputs/batch/pitchbook_history_001 \
  --repeats 1 \
  --bargaining-rounds 3 \
  --history-limit 10
```

如果要保留全部历史记录：

```bash
--history-limit -1
```

使用全部历史记录会增加 prompt 长度、成本和噪声，建议先用 3 或 10 做对照实验。
