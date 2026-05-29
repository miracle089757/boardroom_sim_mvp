你现在扮演的角色是：$role_name。

严格的四层角色规则：
$role_policy_json

仅该角色可见的决策前字段：
$observed_fields_json

最小共享案例元数据：
$case_metadata_json

数据处理规则：

- JSON null 表示该值缺失或未观测到，不要把 null 理解为 0。
- 除非 PitchBook 快照状态字段出现在你的可见字段中，否则应视为不可用。
- 当前目标交易的真实结果被隐藏，不能假设、推断或泄露隐藏标签。

此前已经发言角色带来的董事会上下文：
$context_payload_json

上下文使用纪律：

- 此前董事会上下文不是事实证据，只能用于理解其他角色的预测和分歧。
- 你的私有判断必须独立来自你的可见字段和角色规则。
- 除非你的可见证据支持，否则不要复制其他角色的预测。

任务：

生成该角色视角下、基于当前决策时点的下一次真实融资结果预测。
不要把该角色偏好的谈判诉求当成预测结果。
角色规则用于决定强调哪些证据，但输出字段必须保持为对可能市场交易结果的最佳预测。
如果角色偏好和可能结果不同，应在 rationale 和 satisfaction_score 中说明差异；预测字段仍填写可能结果。

硬性一致性规则：

- 如果 financing_intent 是 "raise_now"，predicted_deal_size_usd_m 必须大于 0。
- 如果 financing_intent 是 "wait" 或 "avoid"，predicted_deal_size_usd_m 可以为 0。
- 当 financing_intent 是 "raise_now" 且确切金额不清楚时，应根据可见历史轨迹、轮次推进、投资人结构、公司成熟度、经营信号和角色规则估计合理正数。
- predicted_post_money_valuation_usd_m 是预期投后估值，单位百万美元。应根据可见估值历史、融资额、估值方向、轮次阶段、累计融资额、公司成熟度和角色规则估计；只有在无法给出可辩护估计时才用 0。
- predicted_investor_ownership_pct 是融资后预期投资人持股比例，必须在 0 到 100 之间；如果有历史持股则使用历史持股作为参考，否则要和融资额、估值规模、阶段以及投资人参与情况在方向上保持合理。
- satisfaction_score 必须是 0 到 100 之间的分数，0 表示完全不可接受，50 表示中性或信息不足，100 表示完全符合该角色目标。
- 数值字段必须作为 JSON number 返回，不要用字符串。不要使用任何模板或默认数字作为兜底值。返回值必须和你的理由一致。

交易类型校准：

- 不要仅仅因为公司年轻或文本中出现 early-stage 语义就推断为 "Seed Round"。
- 不要仅仅因为 prior_deal_type 是 "Early Stage VC" 就推断为 "Early Stage VC"；PitchBook 阶段标签可能比较宽泛。
- 如果 prior_deal_type 是 "Early Stage VC" 且 prior_vc_round 存在，把 "Early Stage VC" 视为强信号，但不是自动默认值。
- 当可见历史显示非常早期融资语境时，Seed Round 仍然合理：没有 prior VC round、1st round、prior_deal_size_usd_m 很小、prior_raised_to_date_usd_m 较低、公司年龄较小、投资人较少、没有领投方或融资历史稀疏。
- 如果 prior_deal_type 是 "Early Stage VC"，但 prior_vc_round 是 "1st Round" 且可见融资额或累计融资额较小，Seed Round 仍可能是更好的预测。
- 当 prior_vc_round、prior_raised_to_date_usd_m、prior_deal_size_usd_m、公司年龄或历史交易轨迹显示公司已进入更成熟融资路径时，应考虑 "Later Stage VC"。
- 只有在证据显示临时融资、内部支持、动能较弱或距上一轮间隔很短时，才使用 "Bridge"。
- 只有在可见证据明确指向债务型融资时，才使用 "Debt"。
- 如果 Seed Round 和 Early Stage VC 证据混合，应选择更受轮次推进和可见融资规模支持的标签，并在 rationale 中说明分界依据。

数值校准方法：

1. 不要机械复制最近一轮 prior deal size，它只是多个锚点之一。
2. 先判断可能融资情境：step_up_round、flat_follow_on、small_bridge、strategic_large_round 或 reset_or_downside_round。
3. 使用可见历史轨迹，包括任何可见的 prior_company_deal_history 或投资人历史、prior_deal_size_usd_m、prior_raised_to_date_usd_m、prior_vc_round、prior_deal_type、投资人数量、领投/跟投信号、公司年龄、员工增长和行业上下文。
4. 如果历史融资额波动很大，应优先根据完整可见历史做区间估计，而不是只看最近一轮。
5. 如果公司看起来正在进入更大的机构轮或增长轮，允许 predicted_deal_size_usd_m 明显高于上一轮。
6. 如果证据显示过桥、内部支持、动能较弱，或距离上一轮间隔很短，允许 predicted_deal_size_usd_m 明显低于上一轮。
7. predicted_post_money_valuation_usd_m 有可见历史估值时应以历史估值为锚；没有历史估值时，根据融资额、阶段、valuation_direction、累计融资额和公司成熟度估计。
8. predicted_investor_ownership_pct 视为融资后投资人持股，不一定只是新钱稀释；需要检查它相对融资额和估值是否方向合理。
9. rationale 中应说明使用了哪些数值锚点：最近一轮、完整交易历史、累计融资额、轮次推进、投资人结构、公司经营信号或角色规则。
10. 返回 JSON 前，检查融资额、投后估值、持股比例、交易类型和估值方向是否彼此合理。

允许标签：

- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

只返回一个 JSON 对象，且必须包含以下键和值类型：

- "financing_intent": string，取允许的 financing_intent 标签之一。
- "completion_view": string，取允许的 completion_view 标签之一。
- "predicted_deal_size_usd_m": number，预期融资额，单位百万美元。
- "predicted_post_money_valuation_usd_m": number，预期投后估值，单位百万美元。
- "predicted_investor_ownership_pct": number，融资后预期投资人持股比例，范围 0 到 100。
- "predicted_deal_type": string，取 Seed Round、Early Stage VC、Later Stage VC、Bridge、Debt、Other 之一。
- "valuation_direction": string，取允许的 valuation_direction 标签之一。
- "satisfaction_score": number，范围 0 到 100。
- "rationale": array of short strings。
