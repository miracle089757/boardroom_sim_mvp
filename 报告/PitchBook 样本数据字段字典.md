---
title: "PitchBook 样本数据字段字典"
aliases:
  - PitchBook字段字典
  - 02_03_pitchbook_sample_100_shared 字段说明
tags:
  - dataset
  - pitchbook
  - field-dictionary
  - startup-simulation
created: 2026-04-25
source_file: "[[02_03_pitchbook_sample_100_shared.xlsx]]"
---

# PitchBook 样本数据字段字典

这篇笔记解释 `02_03_pitchbook_sample_100_shared.xlsx` 中每张表、每个字段的通俗含义。这个工作簿是一个以创业公司为中心的关系型样本数据集：`company` 是公司主表，其他表围绕公司展开，描述行业、赛道、地点、人员、董事会、投资人、融资交易、竞争对手和相似公司。

## 使用前先记住

- `companyid`：公司 ID，是连接大多数表的核心键。
- `personid`：人员 ID，用来连接人员主表、任职、教育、董事会、顾问等表。
- `investorid`：投资人 ID，用来连接投资人主表、公司-投资人关系、交易-投资人关系。
- `dealid`：交易 ID，用来连接融资/并购事件和参与该事件的投资人。
- 金额、估值、收入等财务字段在 PitchBook 中通常按百万美元或交易本币口径给出；具体单位应以原始导出说明为准。
- 很多字段是稀疏字段，尤其是收入、EBITDA、估值倍数、偏好估值区间等。做实验前应先检查非空率。
- 本数据中的公司、人员、投资人名称多已脱敏，很多 ID 是 hashed ID，不适合当作真实名字解释。

## 表关系速览

| 实体 | 主表/关系表 |
|---|---|
| 公司 | `company` |
| 行业与赛道 | `companyindustryrelation`、`companyverticalrelation` |
| 地点与员工 | `companylocationrelation`、`companyemployeehistoryrelation` |
| 人员与履历 | `person`、`personpositionrelation`、`personeducationrelation` |
| 董事会与顾问 | `personboardseatrelation`、`companyboardteamrelation`、`personadvisoryrelation` |
| 投资人 | `investor`、`companyinvestorrelation` |
| 交易与融资 | `deal`、`dealinvestorrelation` |
| 竞争与相似公司 | `companycompetitorrelation`、`companysimilarrelation` |
| 新闻 | `companynewsrelation` |

## overview

工作簿目录表，记录每个 sheet 的行数、列数和简短说明。

| 字段 | 通俗解释 |
|---|---|
| `sheet` | 工作簿中的 sheet 名称。 |
| `rows` | 该 sheet 的数据行数，不含表头。 |
| `cols` | 该 sheet 的字段列数。 |
| `description` | 对该 sheet 内容的简要说明。 |

## _sample_person_roles

辅助表，不是原始 PitchBook 单表，而是把样本公司相关人员的多类角色合并到一起。它适合快速构造“某个人在某家公司扮演什么角色”。

| 字段 | 通俗解释 |
|---|---|
| `personid` | 人员 ID，可连接 `person`、`personpositionrelation`、`personeducationrelation` 等表。 |
| `companyid` | 公司 ID，表示这个人员角色属于哪家公司。 |
| `fulltitle` | 完整头衔，例如 CEO、Co-Founder、Board Member、Advisor 等。 |
| `startdate` | 该角色开始时间。 |
| `enddate` | 该角色结束时间；为空通常表示未记录结束或仍在任。 |
| `iscurrent` | 是否为当前角色，常见值 1/0。 |
| `isonboard` | 是否在董事会或董事会相关位置上。 |
| `source_table` | 这条角色记录来自哪张原始关系表，例如 boardteam、position、advisory。 |
| `is_founder` | 是否可识别为创始人角色。 |
| `joined_within_2y_of_founding` | 该人员是否在公司成立后 2 年内加入，可近似表示早期核心成员。 |

## company

公司主表。每行是一家公司，包含公司静态画像、总部位置、业务状态、融资状态、文本描述和外部标识。

| 字段 | 通俗解释 |
|---|---|
| `businessstatus` | 公司经营状态，例如正在产生收入、停业、被收购等。 |
| `cikcode` | SEC CIK 编码，美国证券监管披露系统中的公司识别号；只有部分公司有。 |
| `companyfinancingstatus` | 公司融资状态，例如 VC-backed、Formerly VC-backed、PE-backed 等。 |
| `companyid` | 公司唯一 ID，是连接其他公司相关表的核心字段。 |
| `description` | 公司业务描述，通常说明公司做什么、服务谁、解决什么问题。 |
| `emergingspaces` | PitchBook 标注的新兴主题或前沿领域，如电动车充电等；覆盖率较低。 |
| `exchange` | 股票交易所代码或上市交易地点；只有上市或相关公司可能有。 |
| `hqcity` | 公司总部城市。 |
| `hqcountry` | 公司总部所在国家。 |
| `hqglobalregion` | 总部所在全球大区，例如 North America、Europe、Asia 等。 |
| `hqglobalsubregion` | 总部所在更细的大区，例如 West Coast、Northern Europe 等。 |
| `hqstate_province` | 总部所在州、省或地区。 |
| `keywords` | 公司关键词，概括产品、技术、商业模式和行业标签。 |
| `morningstarid` | Morningstar 外部数据 ID，通常用于金融市场数据连接。 |
| `ownershipstatus` | 所有权状态，例如 privately held、publicly held、acquired 等。 |
| `parentcompanyid` | 母公司 ID；如果公司被某个公司控股，可指向母公司。 |
| `profiledatasource` | 公司档案的数据来源或采集来源。 |
| `ticker` | 股票代码或脱敏后的股票标识；多数私有公司为空。 |
| `toplevelparentid` | 最顶层母公司 ID，用于穿透复杂控股结构。 |
| `universe` | PitchBook 中所属数据 universe 或样本范围分类。 |
| `yearfounded` | 公司成立年份。 |

## companyindustryrelation

公司-行业多对多关系表。一家公司可以有多个行业标签，其中一个可被标为主行业。

| 字段 | 通俗解释 |
|---|---|
| `companyid` | 公司 ID。 |
| `industrycode` | 行业细分类名称或代码，例如 Business/Productivity Software。 |
| `industrygroup` | 行业组，比 `industrycode` 更高一层。 |
| `industrysector` | 行业部门，比 `industrygroup` 更高一层。 |
| `isprimary` | 是否为公司的主行业标签。 |

## companyverticalrelation

公司-赛道关系表。赛道比行业更偏主题或投资标签，例如 AI、FinTech、SaaS。

| 字段 | 通俗解释 |
|---|---|
| `companyid` | 公司 ID。 |
| `vertical` | 公司所属垂直赛道或投资主题。 |

## companyemployeehistoryrelation

公司员工数历史表。适合做成长曲线、扩张速度、裁员或收缩信号分析。

| 字段 | 通俗解释 |
|---|---|
| `companyid` | 公司 ID。 |
| `date` | 员工数记录日期。 |
| `employeecount` | 该日期记录到的员工人数。 |

## companylocationrelation

公司办公地点表。每家公司可能有总部、区域办公室或其他地点。

| 字段 | 通俗解释 |
|---|---|
| `city` | 办公地点城市。 |
| `companyid` | 公司 ID。 |
| `country` | 办公地点国家。 |
| `locationstatus` | 地点状态，例如 active、inactive 等。 |
| `locationtype` | 地点类型，例如 Primary HQ、Regional Office。 |
| `state` | 办公地点所在州、省或地区。 |

## companycompetitorrelation

公司竞争对手关系表。每行表示一家公司和一个被识别出的竞争对手。

| 字段 | 通俗解释 |
|---|---|
| `companyid` | 被分析的公司 ID。 |
| `competitorallindustries` | 竞争对手涉及的所有行业标签。 |
| `competitordescription` | 竞争对手的业务描述。 |
| `competitorid` | 竞争对手公司 ID，通常可以连接回 `company.companyid` 或外部公司实体。 |
| `competitorprimaryindustrycode` | 竞争对手主行业细分类。 |
| `competitorprimaryindustrygroup` | 竞争对手主行业组。 |
| `competitorprimaryindustrysector` | 竞争对手主行业部门。 |
| `competitorverticals` | 竞争对手所属赛道标签。 |

## companysimilarrelation

PitchBook 算法生成的相似公司关系表。它不一定表示直接竞争，也可用于构建对照组或 comp set。

| 字段 | 通俗解释 |
|---|---|
| `companyfinancingstatus` | 相似公司的融资状态。 |
| `companyid` | 被分析的公司 ID。 |
| `iscompetitor` | 该相似公司是否也被标记为竞争对手。 |
| `ownershipstatus` | 相似公司的所有权状态。 |
| `similarallindustries` | 相似公司涉及的所有行业标签。 |
| `similarcompanyhqcity` | 相似公司总部城市。 |
| `similarcompanyhqcountry` | 相似公司总部国家。 |
| `similarcompanyhqstate_province` | 相似公司总部州、省或地区。 |
| `similarcompanyid` | 相似公司 ID。 |
| `similardescription` | 相似公司的业务描述。 |
| `similarityrank` | 相似度排名，数字越靠前通常表示越相似。 |
| `similarityscore` | 相似度分数，分数越高表示越相似。 |
| `similarprimaryindustrycode` | 相似公司主行业细分类。 |
| `similarprimaryindustrygroup` | 相似公司主行业组。 |
| `similarprimaryindustrysector` | 相似公司主行业部门。 |
| `similarverticals` | 相似公司赛道标签。 |

## companynewsrelation

公司新闻表。当前样本只有极少记录，适合作为示例，不适合作为主分析变量。

| 字段 | 通俗解释 |
|---|---|
| `byline` | 新闻作者或署名。 |
| `companyid` | 新闻关联的公司 ID。 |
| `publishdate` | 新闻发布日期。 |
| `source` | 新闻来源媒体。 |
| `title` | 新闻标题。 |
| `url` | 新闻链接。 |

## companyboardteamrelation

从公司视角记录董事会和管理团队成员。适合构建公司治理结构和高管团队。

| 字段 | 通俗解释 |
|---|---|
| `companyid` | 公司 ID。 |
| `enddate` | 该成员在该公司角色的结束日期。 |
| `fulltitle` | 成员完整头衔。 |
| `iscurrent` | 是否为当前成员。 |
| `isonboard` | 是否属于董事会成员。 |
| `location` | 该人员位置或工作地点。 |
| `personid` | 人员 ID。 |
| `representingid` | 该董事或成员代表的投资人 ID；常见于投资人派驻董事。 |
| `roleonboard` | 董事会角色，例如 Board Member、Observer 等。 |
| `startdate` | 该角色开始日期。 |

## companyinvestorrelation

公司-投资人关系表。它描述某投资人与某公司之间的持续关系，不只是某一轮交易。

| 字段 | 通俗解释 |
|---|---|
| `companyid` | 被投资公司 ID。 |
| `holding` | 投资人持有状态或持股性质，例如 Minority。 |
| `investorexit` | 投资人退出日期或退出记录。 |
| `investorid` | 投资人 ID。 |
| `investorsince` | 投资人从什么时候开始投资或进入该公司。 |
| `investorstatus` | 投资人在该公司中的状态，例如 Active、Former。 |
| `investortype` | 投资人类型，例如 VC、Angel、Accelerator、Corporate VC。 |

## deal

交易/融资事件主表。每行是一笔交易，可以是 VC 融资、债务、并购、IPO、众筹、二级交易等。这个表很宽，很多财务字段只在特定交易类型下有值。

| 字段 | 通俗解释 |
|---|---|
| `addon` | 是否为 add-on transaction，即某平台公司追加收购的小型补充交易。 |
| `addonplatform` | add-on 交易对应的平台公司或平台资产。 |
| `addonsponsors` | add-on 交易背后的赞助方或投资方。 |
| `announceddate` | 交易公开宣布日期。 |
| `businessstatus` | 交易发生时或记录中的公司经营状态。 |
| `companyid` | 交易关联的公司 ID。 |
| `contingentpayout` | 或有支付/业绩对赌支付，例如并购中的 earn-out。 |
| `dealclass` | 交易大类，例如融资、并购、债务等更高层分类。 |
| `dealdate` | 交易实际发生日期或完成日期。 |
| `dealid` | 交易唯一 ID。 |
| `dealno` | 公司交易序号或 PitchBook 内部交易编号，可用于排序轮次。 |
| `dealsize` | 交易金额，常用于融资额、并购金额或交易规模。 |
| `dealsize_cashflow` | 交易金额相对于现金流的倍数或比值。 |
| `dealsize_ebit` | 交易金额相对于 EBIT 的倍数。 |
| `dealsize_ebitda` | 交易金额相对于 EBITDA 的倍数。 |
| `dealsize_netincome` | 交易金额相对于净利润的倍数。 |
| `dealsize_revenue` | 交易金额相对于收入的倍数。 |
| `dealstatus` | 交易状态，例如 Completed、Cancelled、Announced。 |
| `dealtype` | 交易类型，例如 Seed、Early Stage VC、Later Stage VC、IPO、M&A、Debt。 |
| `debt_ebitda` | 债务/EBITDA 比率，用来衡量杠杆水平。 |
| `debt_equity` | 债务/股权比率。 |
| `debtraisedinround` | 该轮融资中包含的债务融资金额。 |
| `debts` | 债务金额或债务相关说明。 |
| `ebitda` | EBITDA，息税折旧摊销前利润。 |
| `ebitdamarginpercent` | EBITDA 利润率百分比。 |
| `employees` | 交易记录中披露的公司员工数。 |
| `exchange` | 若涉及上市或公开市场交易，表示交易所。 |
| `exitscope` | 退出范围，例如完整退出、部分退出等。 |
| `fillingrangehigh` | IPO 或发行申报价格区间上限；字段名可能是 filing range high 的变体。 |
| `fillingrangelow` | IPO 或发行申报价格区间下限。 |
| `financingstatus` | 交易后的融资状态或融资阶段状态。 |
| `followoninvestors` | 本轮参与的跟投投资人数量。 |
| `grossprofit` | 毛利润。 |
| `impliedev` | 隐含企业价值，通常由交易价格推算。 |
| `impliedev_cashflow` | 隐含企业价值/现金流倍数。 |
| `impliedev_ebit` | 隐含企业价值/EBIT 倍数。 |
| `impliedev_ebitda` | 隐含企业价值/EBITDA 倍数。 |
| `impliedev_netincome` | 隐含企业价值/净利润倍数。 |
| `impliedev_revenue` | 隐含企业价值/收入倍数。 |
| `investorownership` | 交易后投资人持股比例或所有权比例。 |
| `investors` | 本轮投资人数量。 |
| `marketcapendoffirsttradingday` | 上市首日收盘后的市值。 |
| `nativecurrencyofdeal` | 交易原始币种。 |
| `netincome` | 净利润。 |
| `newinvestors` | 本轮新进入投资人数量。 |
| `numberofshares` | 交易涉及的股份数量。 |
| `percentacquired` | 并购交易中被收购的股权比例。 |
| `postvaluation` | 投后估值，即融资后公司估值。 |
| `premoneyvaluation` | 投前估值，即本轮融资前公司估值。 |
| `price1dayafteroffering` | 发行或 IPO 后第 1 天价格。 |
| `price30daysafteroffering` | 发行或 IPO 后第 30 天价格。 |
| `price5daysafteroffering` | 发行或 IPO 后第 5 天价格。 |
| `raisedtodate` | 截至该交易时公司累计融资金额。 |
| `revenue` | 收入。 |
| `revenuegrowthsincelastdebtdeal` | 自上一笔债务交易以来的收入增长率。 |
| `stocksplit` | 股票拆分信息。 |
| `tickersymbol` | 股票代码。 |
| `totaldebt` | 总债务。 |
| `totalinstloansize` | 机构贷款总规模。 |
| `totalinvestedcapital` | 总投入资本。 |
| `totalinvestedequity` | 总投入股权资本。 |
| `totalloansize` | 贷款总规模。 |
| `totalnewdebt` | 本轮新增债务总额。 |
| `valuation_cashflow` | 估值/现金流倍数。 |
| `valuation_ebit` | 估值/EBIT 倍数。 |
| `valuation_ebitda` | 估值/EBITDA 倍数。 |
| `valuation_netincome` | 估值/净利润倍数。 |
| `valuation_revenue` | 估值/收入倍数。 |
| `vcround` | VC 轮次编号或轮次标签，例如 Angel、1st Round、2nd Round。 |
| `vcroundup_down_flat` | 本轮相对上一轮估值方向：up、down、flat；当前样本中覆盖率较低。 |

## dealinvestorrelation

交易-投资人关系表。每行表示某个投资人参与了某笔交易。

| 字段 | 通俗解释 |
|---|---|
| `dealid` | 交易 ID，可连接 `deal`。 |
| `investorfundid` | 参与交易的具体基金 ID；有时比 `investorid` 更细。 |
| `investorid` | 投资人 ID，可连接 `investor`。 |
| `investorinvestmentamount` | 该投资人在该轮投入的金额。 |
| `investorstatus` | 该投资人在该交易中的状态，例如新投资人、跟投投资人等。 |
| `isleadinvestor` | 是否为领投方，常见 1/0。 |
| `leadpartnerid` | 领投合伙人 ID，通常指具体负责该交易的投资人个人。 |
| `numberofsharesacquired` | 该投资人获得或购买的股份数量。 |

## investor

投资人主表。每行是一个投资机构或个人投资人，包含类型、总部、投资偏好和外部标识。

| 字段 | 通俗解释 |
|---|---|
| `cikcode` | SEC CIK 编码，适用于部分公开机构。 |
| `companyfinancingstatus` | 如果该投资人本身也是公司实体，表示其融资状态。 |
| `exchange` | 投资人若为上市公司，表示交易所。 |
| `hqcity` | 投资人总部城市。 |
| `hqcountry` | 投资人总部国家。 |
| `hqglobalregion` | 投资人总部全球大区。 |
| `hqglobalsubregion` | 投资人总部全球子区域。 |
| `hqstate_province` | 投资人总部州、省或地区。 |
| `investorid` | 投资人唯一 ID。 |
| `investornativecurrency` | 投资人使用的本币或主要报告币种。 |
| `investorstatus` | 投资人状态，例如 Active。 |
| `keywords` | 投资人关键词，可能描述投资主题、策略或机构特征。 |
| `morningstarid` | Morningstar 外部数据 ID。 |
| `otherinvestmentpreferences` | 其他投资偏好说明。 |
| `otherinvestortypes` | 除主要类型外的其他投资人类型。 |
| `ownershipstatus` | 投资人自身的所有权状态。 |
| `parentcompanyid` | 投资人的母公司 ID。 |
| `preferredcompanyvaluation` | 投资人偏好的公司估值区间文本。 |
| `preferredcompanyvaluationmax` | 投资人偏好的公司估值上限。 |
| `preferredcompanyvaluationmin` | 投资人偏好的公司估值下限。 |
| `preferreddealsize` | 投资人偏好的交易规模区间文本。 |
| `preferreddealsizemax` | 投资人偏好的交易规模上限。 |
| `preferreddealsizemin` | 投资人偏好的交易规模下限。 |
| `preferredebit` | 投资人偏好的 EBIT 区间文本。 |
| `preferredebitda` | 投资人偏好的 EBITDA 区间文本。 |
| `preferredebitdamax` | 投资人偏好的 EBITDA 上限。 |
| `preferredebitdamin` | 投资人偏好的 EBITDA 下限。 |
| `preferredebitmax` | 投资人偏好的 EBIT 上限。 |
| `preferredebitmin` | 投资人偏好的 EBIT 下限。 |
| `preferredgeography` | 投资人偏好的投资地区。 |
| `preferredinvestmentamount` | 投资人偏好的单笔投资金额区间文本。 |
| `preferredinvestmentamountmax` | 投资人偏好的单笔投资金额上限。 |
| `preferredinvestmentamountmin` | 投资人偏好的单笔投资金额下限。 |
| `preferredinvestmenthorizon` | 投资人偏好的持有期限区间文本。 |
| `preferredinvestmenthorizonmax` | 投资人偏好的持有期限上限。 |
| `preferredinvestmenthorizonmin` | 投资人偏好的持有期限下限。 |
| `preferredinvestmenttypes` | 投资人偏好的投资类型，例如 Early Stage VC、Buyout、M&A。 |
| `preferredrevenue` | 投资人偏好的被投公司收入区间文本。 |
| `preferredrevenuemax` | 投资人偏好的收入上限。 |
| `preferredrevenuemin` | 投资人偏好的收入下限。 |
| `primaryinvestortype` | 投资人的主要类型，例如 Venture Capital、Angel、PE、Corporate VC。 |
| `ticker` | 投资人若为上市公司，表示股票代码或相关标识。 |
| `toplevelparentid` | 投资人的最顶层母公司 ID。 |
| `tradeassociations` | 投资人所属行业协会或组织。 |
| `yearfounded` | 投资机构成立年份。 |

## person

人员主表。只保留人员的基础静态属性。

| 字段 | 通俗解释 |
|---|---|
| `gender` | 性别。 |
| `location` | 人员所在地。 |
| `personid` | 人员唯一 ID。 |

## personpositionrelation

人员任职经历表。记录人员在公司或基金中的职位经历，不限于样本公司。

| 字段 | 通俗解释 |
|---|---|
| `enddate` | 任职结束日期。 |
| `entityid` | 任职实体 ID，可能是公司 ID 或基金 ID。 |
| `entitytype` | 任职实体类型，例如 Company 或 Fund。 |
| `fulltitle` | 完整职位头衔。 |
| `iscurrent` | 是否为当前职位。 |
| `location` | 任职地点或人员地点。 |
| `personid` | 人员 ID。 |
| `positionlevel` | 职级或职位层级，例如 Founder、CEO、VP、Director。 |
| `startdate` | 任职开始日期。 |

## personeducationrelation

人员教育背景表。

| 字段 | 通俗解释 |
|---|---|
| `degree` | 学位，例如 BA、MBA、Master's、PhD。 |
| `graduatingyear` | 毕业年份。 |
| `institute` | 学校或教育机构名称。 |
| `major_concentration` | 专业或研究方向。 |
| `personid` | 人员 ID。 |

## personboardseatrelation

人员-董事席位关系表。每行表示某人在某家公司拥有或曾经拥有董事会席位。

| 字段 | 通俗解释 |
|---|---|
| `companyid` | 董事席位所在公司 ID。 |
| `enddate` | 董事席位结束日期。 |
| `iscurrent` | 是否为当前董事席位。 |
| `location` | 该人员所在地或董事记录地点。 |
| `personid` | 人员 ID。 |
| `representingid` | 该董事代表的投资人 ID，常用于判断投资人派驻董事。 |
| `roleonboard` | 董事会角色，例如 Board Member、Board Observer。 |
| `startdate` | 董事席位开始日期。 |

## personadvisoryrelation

人员顾问关系表。记录人员为某实体担任顾问的情况。

| 字段 | 通俗解释 |
|---|---|
| `advisorytitle` | 顾问头衔或顾问角色名称。 |
| `enddate` | 顾问关系结束日期。 |
| `entityid` | 被顾问服务的实体 ID，可能是公司、基金或投资人实体。 |
| `industrycode` | 顾问关系关联的行业代码或领域。 |
| `iscurrent` | 是否为当前顾问关系。 |
| `location` | 顾问人员所在地。 |
| `personid` | 人员 ID。 |
| `startdate` | 顾问关系开始日期。 |

## 做社会模拟时优先用哪些字段

如果目标是创业公司内部治理或融资决策模拟，建议先用这些字段构造事实卡：

| 模块 | 优先字段 |
|---|---|
| 公司画像 | `company.description`、`company.keywords`、`company.yearfounded`、`company.businessstatus`、`company.companyfinancingstatus` |
| 行业赛道 | `companyindustryrelation.*`、`companyverticalrelation.vertical` |
| 成长状态 | `companyemployeehistoryrelation.date`、`companyemployeehistoryrelation.employeecount` |
| 融资事件 | `deal.dealdate`、`deal.dealtype`、`deal.dealsize`、`deal.vcround`、`deal.raisedtodate` |
| 估值与稀释 | `deal.postvaluation`、`deal.premoneyvaluation`、`deal.investorownership`、`deal.vcroundup_down_flat` |
| 投资人 | `dealinvestorrelation.isleadinvestor`、`companyinvestorrelation.investortype`、`investor.primaryinvestortype` |
| 团队 | `_sample_person_roles.fulltitle`、`personpositionrelation.positionlevel`、`personeducationrelation.*` |
| 董事会 | `companyboardteamrelation.isonboard`、`personboardseatrelation.representingid` |
| 竞争环境 | `companycompetitorrelation.*`、`companysimilarrelation.similarityscore` |

## 常见建模提醒

- 不要把 `companysimilarrelation` 当成真实竞争关系，它是算法相似公司；真实竞争关系更接近 `companycompetitorrelation`。
- 不要把所有空值当成 0。很多空值表示 PitchBook 未披露，而不是金额为 0。
- `dealdate` 比 `announceddate` 覆盖率更高，做时间序列时优先考虑 `dealdate`。
- `postvaluation`、`premoneyvaluation` 很有价值，但缺失较多；估值实验需要子样本。
- `companyemployeehistoryrelation` 是最适合做动态模拟验证的表，因为它是真实时间序列。
- `personpositionrelation` 可用于构造 CEO、CTO、Founder、Director 等角色，但需要用 `fulltitle` 和 `positionlevel` 做规则匹配。
