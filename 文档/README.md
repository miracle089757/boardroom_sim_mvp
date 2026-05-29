# Boardroom Sim 文档索引

这个文件夹用于让新的协作者或 Agent 快速理解、修改和运行实验。当前代码已经把角色、prompt、可见字段和讨论流程从 Python 硬编码中拆出，主要通过 TOML 和 Markdown 文件维护。

## 文档列表

- [代码结构.md](代码结构.md)：项目目录、核心模块职责、主要扩展点。
- [实验流程.md](实验流程.md)：从输入数据到多智能体辩论、聚合、评估的完整流程。
- [各阶段Prompt.md](各阶段Prompt.md)：每个 LLM 调用阶段使用的 prompt 模板、变量和维护规则。
- [实验运行指南.md](实验运行指南.md)：单次运行、批量运行、评估、常见修改方式。

## 最常改的位置

| 目标 | 修改位置 |
| --- | --- |
| 改角色顺序、轮次、历史窗口、权重 | `configs/boardroom_default.toml` |
| 改某个角色的目标、可见字段、启发式、交互协议 | `policies/roles/*.toml` |
| 改初始预测 prompt | `prompts/initial_prediction.md` |
| 改辩论阶段 prompt | `prompts/bargaining_step.md` |
| 改发言风格 | `prompts/response_generators/*.md` 和配置里的 `response_generator` |
| 改董事会过程、L5 文化、历史可见范围 | 优先改 `configs/boardroom_default.toml` 的 `board.archetype`；需要消融时再改 `[board.culture]` 和 `[discussion]` |
| 改 baseline prompt | `prompts/baseline_system.md`、`prompts/baseline_single_agent.md` |
| 改聚合/流程代码 | `boardroom_sim/simulator.py` |
| 改过程控制逻辑 | `boardroom_sim/process.py` |
| 改单个 Agent 行为与 JSON 校验 | `boardroom_sim/agents.py` |

## 当前实验边界

- 当前支持的讨论范式是 `memory`，即每轮角色看到此前角色预测和辩论消息摘要；在此基础上，`board.archetype` 会默认控制 L5 文化层、发言顺序、主导角色和历史可见范围。
- 当前支持的决策协议是 `weighted_vote`，即按配置中的角色权重聚合分类和数值预测。
- prompt 已改为中文，但 JSON key、枚举标签和数据字段名仍保持英文，便于代码解析和评估。
- 当前真实标签只放在 `notes.labels` 中用于评估，不进入角色可见字段。
