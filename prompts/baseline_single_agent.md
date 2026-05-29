历史时点字段：
$historical_payload_json

角色政策规则：
$role_rules_json

任务：
预测这个 case 的融资结果。如果提供了角色政策规则，请把这些规则综合成一次单代理判断；不要模拟多角色辩论。

数据处理规则：
- JSON null 表示缺失或不可观测，不要把 null 当作 0。
- 不要使用当前目标交易标签；这些标签没有包含在 payload 中。
- predicted_post_money_valuation_usd_m 是预期投后估值，单位为百万美元。
- predicted_investor_ownership_pct 是融资后投资人预期持股比例，范围为 0 到 100。

允许标签：
- financing_intent: raise_now, wait, avoid
- completion_view: likely_complete, unlikely_complete
- valuation_direction: up, flat, down

只返回一个 JSON 对象，schema 如下：
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
