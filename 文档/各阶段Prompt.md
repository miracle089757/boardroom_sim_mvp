# 各阶段 Prompt

当前 prompt 已从代码中移到 `prompts/` 目录。模板使用 Python 标准库 `string.Template`，变量格式是 `$variable_name`。JSON key、字段名和枚举标签仍保持英文，中文只用于说明文字。

## Prompt 总览

| 阶段 | 调用位置 | 模板文件 | 用途 |
| --- | --- | --- | --- |
| 多智能体 system prompt | `BoardAgent._system_prompt()` | `prompts/system_agent.md` | 所有角色 LLM 调用共用的系统约束。 |
| 初始私有预测 | `BoardAgent._decision_prompt()` | `prompts/initial_prediction.md` | 角色在看到自身可见字段后做第一次预测。 |
| 辩论与更新 | `BoardAgent._bargaining_prompt()` | `prompts/bargaining_step.md` | 每轮发言，并返回更新后的完整预测。 |
| 发言风格模块 | `PromptRenderer.response_guidance()` | `prompts/response_generators/*.md` | 控制辩论发言风格，例如简单、批判、推理型。 |
| baseline system prompt | `_baseline_messages()` | `prompts/baseline_system.md` | 单代理 baseline 的系统约束。 |
| baseline user prompt | `_baseline_messages()` | `prompts/baseline_single_agent.md` | 单代理 baseline 的输入字段、任务和 JSON schema。 |

## 1. System Prompt

文件：`prompts/system_agent.md`

主要变量：

- `$role_name`
- `$role_policy_json`

作用：

- 定义当前 LLM 是董事会治理社会模拟中的一个角色。
- 要求严格遵守四层角色规则。
- 强调只能使用可见字段。
- 强调只能返回合法 JSON。

维护建议：

- 这里适合放全局纪律，例如禁止泄露标签、禁止输出 Markdown。
- 不建议在这里放具体数值校准方法；数值校准更适合放在阶段 prompt 中。

## 2. 初始私有预测 Prompt

文件：`prompts/initial_prediction.md`

主要变量：

- `$role_name`
- `$role_policy_json`
- `$observed_fields_json`
- `$case_metadata_json`
- `$context_payload_json`

输入含义：

- `observed_fields_json`：该角色根据 `layer_2_attention_fields` 能看到的字段。
- `case_metadata_json`：最小共享案例信息，例如 `case_id`、公司标签、决策日期、行业。
- `context_payload_json`：此前已发言角色的预测。它只是董事会上下文，不是事实证据。

输出 schema：

```json
{
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "satisfaction_score": 50.0,
  "rationale": ["简短理由"]
}
```

维护建议：

- 如果发现模型经常数值漂移，优先修改这里的“数值校准方法”。
- 如果发现模型把偏好当预测，强化“预测不是谈判诉求”的段落。
- 不要改 JSON key，除非同步修改 `boardroom_sim/agents.py` 和评估代码。

## 3. 辩论与更新 Prompt

文件：`prompts/bargaining_step.md`

主要变量：

- `$role_name`
- `$role_policy_json`
- `$observed_fields_json`
- `$proposal_json`
- `$current_decision_json`
- `$context_payload_json`
- `$prior_messages_json`
- `$process_context_json`
- `$round_index`
- `$round_specific_task`
- `$response_guidance`

输入含义：

- `proposal_json`：当前聚合提案，不是 ground truth。
- `current_decision_json`：该角色当前预测。
- `context_payload_json`：其它角色当前预测。
- `prior_messages_json`：此前辩论发言和更新记录。
- `process_context_json`：当前董事会过程约束，包括 board archetype、board_archetype_description、L5 culture、discussion protocol、challenge_required、memory_scope 和当前角色有效权重。
- `round_specific_task`：来自配置的每轮任务。
- `response_guidance`：来自 `prompts/response_generators/` 的发言风格。

输出比初始预测多一个字段：

```json
{
  "message": "一到三句董事会发言",
  "financing_intent": "raise_now|wait|avoid",
  "completion_view": "likely_complete|unlikely_complete",
  "predicted_deal_size_usd_m": 10.0,
  "predicted_post_money_valuation_usd_m": 50.0,
  "predicted_investor_ownership_pct": 20.0,
  "predicted_deal_type": "Seed Round|Early Stage VC|Later Stage VC|Bridge|Debt|Other",
  "valuation_direction": "up|flat|down",
  "satisfaction_score": 50.0,
  "rationale": ["update_status: no_change", "简短理由"]
}
```

维护建议：

- 想改变每一轮讨论任务，优先改 `configs/boardroom_default.toml` 的 `discussion.round_tasks`。
- 想改变董事会互动机制，优先改 `configs/boardroom_default.toml` 的 `board.archetype`；它会默认带出 L5 文化层、讨论协议、主导模式、挑战要求、记忆范围和角色权重乘数。需要做消融时，再单独覆盖 `[board.culture]` 或 `[discussion]`。
- 想改变语气，优先改或新增 `prompts/response_generators/*.md`。
- 想改变模型是否必须更新预测，修改 “更新状态记录” 段落。

## 4. Response Generator

目录：`prompts/response_generators/`

当前文件：

- `simple.md`：简洁发言。
- `critical.md`：批判性发言，默认启用。
- `reasoning.md`：更强调推理链条和证据权衡。

启用方式：

```toml
[discussion]
response_generator = "critical"
```

新增风格时：

1. 新建 `prompts/response_generators/<name>.md`。
2. 在配置中把 `response_generator` 改为 `<name>`。
3. 不需要改 Python 代码。

## 5. Baseline Prompt

文件：

- `prompts/baseline_system.md`
- `prompts/baseline_single_agent.md`

调用位置：`boardroom_sim/baselines.py`

用途：

- `baseline_history_only`：只传历史时点字段。
- `baseline_history_with_roles`：传历史时点字段和角色政策，但仍是单代理判断。

维护建议：

- baseline 的 JSON schema 应尽量和多智能体最终输出保持一致，方便横向对比。
- baseline 不应模拟多轮辩论，否则会失去和主实验的对照意义。

## Prompt 修改检查清单

- 保留所有代码需要解析的 JSON key。
- 保留英文枚举标签：`raise_now`、`wait`、`avoid`、`likely_complete`、`unlikely_complete`、`up`、`flat`、`down`。
- 数值字段要求 JSON number，不要让模型返回带单位的字符串。
- 不要把真实标签字段加入可见字段或 prompt。
- 修改后至少运行：

```bash
python -B -c "from boardroom_sim.config import load_experiment_config; from boardroom_sim.prompts import PromptRenderer; c=load_experiment_config(); r=PromptRenderer(c.prompts_dir, c.response_generator); print(r.render('initial_prediction', role_name='test', role_policy_json='{}', observed_fields_json='{}', case_metadata_json='{}', context_payload_json='{}')[:200])"
```
