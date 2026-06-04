# samples 文本材料用途说明

## 材料来源与性质

`samples/` 下的 10 个 `*_background.txt` 文件是并购代理文件中类似 “Background of the Merger” 的过程叙事文本。它们不是当前 VC 融资回测的结构化输入字段，而是董事会真实过程材料样本。

根据 `0规则制定.pdf` 的说明，PitchBook 与 EDGAR Background 的互补关系是：

- PitchBook 更强在“环境”：融资历史、估值轨迹、投资人构成、人员与公司状态。
- EDGAR Background 更强在“过程”：董事会会议、特别委员会、顾问介入、竞购方接触、NDA、报价修订、fairness opinion、谈判轨迹。

因此，这些文本当前不应急于并入主实验，但很适合作为后续“真实董事会过程”的材料库。

## 抽样统计

以下统计基于关键词粗筛，只用于判断材料价值，不代表精确事件抽取结果。

| 文件 | 字符数 | board/meeting | Special Committee | NDA/保密协议 | price/offer/bid | fairness opinion | negotiation/discussion |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `0001104659-26-059602_background.txt` | 36643 | 30 | 0 | 7 | 37 | 1 | 12 |
| `0001104659-26-061335_background.txt` | 60027 | 64 | 0 | 5 | 37 | 2 | 21 |
| `0001104659-26-064024_background.txt` | 60020 | 99 | 198 | 7 | 107 | 3 | 34 |
| `0001104659-26-065876_background.txt` | 71520 | 91 | 13 | 3 | 94 | 6 | 37 |
| `0001140361-26-021662_background.txt` | 83292 | 220 | 0 | 10 | 162 | 1 | 65 |
| `0001140361-26-022528_background.txt` | 33554 | 45 | 0 | 1 | 107 | 0 | 11 |
| `0001193125-26-229702_background.txt` | 46837 | 124 | 0 | 14 | 122 | 2 | 27 |
| `0001193125-26-234433_background.txt` | 44893 | 198 | 4 | 3 | 76 | 0 | 47 |
| `0001193125-26-234468_background.txt` | 44893 | 198 | 4 | 3 | 76 | 0 | 47 |
| `0001829126-26-005295_background.txt` | 23354 | 50 | 0 | 4 | 25 | 1 | 12 |

## 对后续实验的可能用途

### 1. 真实董事会过程模板库

这些文本能提供真实会议过程的结构，例如：

- 管理层或董事会如何开始寻找交易对象。
- 董事会如何授权管理层、顾问或特别委员会。
- 潜在买方如何被接触、签 NDA、进入下一轮。
- 报价如何多轮修订。
- 董事会如何讨论 fairness opinion、交易风险和最终建议。

后续可以把这些过程抽象成会议阶段模板，用于生成更真实的董事会讨论流程，而不是让角色简单轮流发言。

### 2. L4 交互协议的实证参照

`0规则制定.pdf` 强调 L4 不只是投票权，也包括正式/非正式 arena、chair-gated 与 free-interjection、top-3 dominance、背景讨论和橡皮图章式正式会议。

这些 background 文本可以帮助标注或提取：

- 谁发起会议。
- 谁主导讨论。
- 是否存在特别委员会。
- 顾问是否在会议中提供意见。
- 董事会是否真正讨论，还是只确认已有谈判结果。
- 是否存在 bidder 竞争和多轮议价。

这些信号可用于未来校准 `discussion_protocol` 和 `meeting_phase`。

### 3. L5 群体文化层的行为例子

规则文件中的 L5 包括：

- `criticality`
- `creativity`
- `cohesiveness`
- `openness_generosity`
- `preparation_involvement`

这些文本可以作为每个维度的正反例材料：

- 高 `criticality`：董事会或特别委员会多次质询估值、风险、条款。
- 高 `creativity`：出现多个 bidder、替代交易结构或多轮战略选择。
- 高 `cohesiveness`：董事会围绕共同目标形成一致建议。
- 高 `openness_generosity`：顾问、管理层、董事会之间反复吸收信息并修正立场。
- 高 `preparation_involvement`：频繁会议、长期过程、外部顾问深度参与。

后续可以把这些例子写进 prompt few-shot 或用于构造 L5 行为解释器的标注数据。

### 4. 过程特征抽取任务

如果后续希望把 EDGAR 材料结构化，可以先抽取以下字段：

- `board_meeting_count`
- `special_committee_used`
- `advisor_count_or_presence`
- `nda_count`
- `bidder_count`
- `price_revision_count`
- `fairness_opinion_present`
- `process_duration_days`
- `final_recommendation_style`
- `board_pushback_events`

这些字段不一定直接进入当前 VC 融资预测实验，但可以作为未来 M&A 过程预测实验的特征。

### 5. 训练或评估“会议发言真实性”

这些文本不是对话记录，但包含会议事件的真实叙事。后续可以用它们检查模拟输出是否具备真实董事会过程特征：

- 是否有阶段推进，而不是每轮重复预测。
- 是否出现顾问、委员会、管理层、投资人之间的互动。
- 是否体现报价、条款、风险、替代方案的动态变化。
- 是否能区分正式董事会会议与会前/会外谈判。

## 当前不引入主实验的原因

暂不引入代码主流程，原因是：

- 当前主实验是 VC-backed private company 的融资回测；samples 多数是 public company M&A proxy 叙事，样本对象和事件类型不同。
- 文本较长，如果直接塞进 prompt，会显著增加 token 成本和噪声。
- 这些材料需要先做事件抽取或模板化，否则会把“真实过程文本”和“当前案例事实”混在一起，增加信息泄露和任务混淆风险。

当前最合理的位置是：作为文档化材料库、过程模板来源、L4/L5 行为例子和未来 EDGAR/M&A 扩展实验的数据基础。
