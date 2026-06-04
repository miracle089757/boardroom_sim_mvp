from __future__ import annotations

import ast
import html
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path.cwd()
OUT = ROOT / "文档" / "完整代码教程.html"
OUT_MD = ROOT / "文档" / "完整代码教程.md"
SOURCE_PATTERNS = [
    "*.py",
    "boardroom_sim/*.py",
    "configs/*.toml",
    "policies/roles/*.toml",
    "prompts/*.md",
    "prompts/response_generators/*.md",
    "requirements.txt",
    "one_case.sh",
]
EXCLUDED_SOURCE_NAMES = {"tutorial_generator.py"}


@dataclass
class FunctionInfo:
    file: Path
    module: str
    name: str
    qualname: str
    anchor: str
    lineno: int
    end_lineno: int
    signature: str
    args: list[str]
    returns: str
    doc: str
    source: str
    calls: list[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    file: Path
    module: str
    name: str
    qualname: str
    anchor: str
    lineno: int
    end_lineno: int
    bases: list[str]
    doc: str
    fields: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def safe_anchor(*parts: object) -> str:
    raw = "-".join(str(part) for part in parts)
    anchor = re.sub(r"[^a-zA-Z0-9_-]+", "-", raw).strip("-").lower()
    return anchor or "section"


def collect_source_files() -> list[Path]:
    files: list[Path] = []
    for pattern in SOURCE_PATTERNS:
        files.extend(ROOT.glob(pattern))
    return sorted(
        {p for p in files if p.is_file() and p.name not in EXCLUDED_SOURCE_NAMES},
        key=lambda p: str(p).lower(),
    )


def call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = call_name(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    if isinstance(node, ast.Subscript):
        return call_name(node.value)
    if isinstance(node, ast.Call):
        return call_name(node.func)
    return ""


def annotation_name(node: ast.AST | None) -> str:
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def expression_name(node: ast.AST | None) -> str:
    if node is None:
        return "None"
    try:
        text = ast.unparse(node)
    except Exception:
        return type(node).__name__
    return text if len(text) <= 120 else text[:117] + "..."


def collect_calls(node: ast.AST) -> list[str]:
    calls: list[str] = []
    seen: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = call_name(child.func)
            if name and name not in seen:
                seen.add(name)
                calls.append(name)
    return calls


def collect_args(node: ast.FunctionDef | ast.AsyncFunctionDef) -> list[str]:
    args = [arg.arg for arg in node.args.posonlyargs + node.args.args]
    if node.args.vararg:
        args.append("*" + node.args.vararg.arg)
    args.extend(arg.arg for arg in node.args.kwonlyargs)
    if node.args.kwarg:
        args.append("**" + node.args.kwarg.arg)
    return args


def source_segment(lines: list[str], start: int, end: int) -> str:
    return "\n".join(lines[start - 1 : end]).rstrip()


def signature_from_source(source: str) -> str:
    lines = source.splitlines()
    signature_lines: list[str] = []
    paren_balance = 0
    started = False
    for line in lines:
        stripped = line.strip()
        if not started and not stripped.startswith(("def ", "async def ")):
            continue
        started = True
        signature_lines.append(stripped)
        paren_balance += stripped.count("(") - stripped.count(")")
        if paren_balance <= 0 and stripped.endswith(":"):
            break
    return " ".join(signature_lines)


def module_name_for(path: Path) -> str:
    stem = rel(path).replace("/", ".")
    if stem.endswith(".py"):
        stem = stem[:-3]
    return stem


def parse_python_files(source_files: list[Path]) -> tuple[list[FunctionInfo], list[ClassInfo], dict[Path, str]]:
    functions: list[FunctionInfo] = []
    classes: list[ClassInfo] = []
    file_texts: dict[Path, str] = {}

    for path in source_files:
        if path.suffix != ".py":
            continue
        text = path.read_text(encoding="utf-8")
        file_texts[path] = text
        lines = text.splitlines()
        tree = ast.parse(text, filename=str(path))
        module = module_name_for(path)

        class_stack: list[str] = []

        class Visitor(ast.NodeVisitor):
            def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
                qualname = ".".join(class_stack + [node.name])
                fields = class_fields(node)
                methods = [item.name for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))]
                class_info = ClassInfo(
                    file=path,
                    module=module,
                    name=node.name,
                    qualname=qualname,
                    anchor=safe_anchor("class", rel(path), qualname, node.lineno),
                    lineno=node.lineno,
                    end_lineno=getattr(node, "end_lineno", node.lineno),
                    bases=[annotation_name(base) for base in node.bases],
                    doc=ast.get_docstring(node) or "",
                    fields=fields,
                    methods=methods,
                )
                classes.append(class_info)
                class_stack.append(node.name)
                self.generic_visit(node)
                class_stack.pop()

            def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
                self._visit_function(node)

            def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
                self._visit_function(node)

            def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
                qualname = ".".join(class_stack + [node.name])
                end = getattr(node, "end_lineno", node.lineno)
                source = source_segment(lines, node.lineno, end)
                functions.append(
                    FunctionInfo(
                        file=path,
                        module=module,
                        name=node.name,
                        qualname=qualname,
                        anchor=safe_anchor("fn", rel(path), qualname, node.lineno),
                        lineno=node.lineno,
                        end_lineno=end,
                        signature=signature_from_source(source),
                        args=collect_args(node),
                        returns=annotation_name(node.returns),
                        doc=ast.get_docstring(node) or "",
                        source=source,
                        calls=collect_calls(node),
                    )
                )
                self.generic_visit(node)

        Visitor().visit(tree)
    return functions, classes, file_texts


def class_fields(node: ast.ClassDef) -> list[str]:
    fields: list[str] = []
    seen: set[str] = set()

    def add(name: str) -> None:
        if name and name not in seen:
            seen.add(name)
            fields.append(name)

    for item in node.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
            add(item.target.id)
        elif isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name):
                    add(target.id)
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "__init__":
            for child in ast.walk(item):
                targets: list[ast.AST] = []
                if isinstance(child, ast.Assign):
                    targets = list(child.targets)
                elif isinstance(child, ast.AnnAssign):
                    targets = [child.target]
                for target in targets:
                    if (
                        isinstance(target, ast.Attribute)
                        and isinstance(target.value, ast.Name)
                        and target.value.id == "self"
                    ):
                        add(target.attr)
    return fields


CORE_FUNCTION_PURPOSES = {
    "boardroom_sim.agents:BoardAgent.evaluate": "让单个角色根据当前案例和其他角色初始判断生成自己的结构化预测。它把系统 prompt、角色规则、案例可见字段和上下文拼成消息，调用 LLM 返回 JSON，然后规范化为 RoleDecision。",
    "boardroom_sim.agents:BoardAgent.bargaining_step": "让某个角色在指定讨论轮次发言，并根据会议内容更新自己的预测。返回三部分：发言文本、更新后的 RoleDecision、以及结构化会议行为记录。",
    "boardroom_sim.agents:BoardAgent._decision_from_json": "把 LLM 返回的原始 JSON 压成实验可用的 RoleDecision。这里负责字段兜底、枚举值校验、数值范围裁剪和理由列表清洗。",
    "boardroom_sim.agents:BoardAgent._meeting_artifacts_from_json": "从 LLM 的讨论回复中提取会议行为字段，例如提出的问题、回应对象、证据锚点、替代方案和承诺事项，用于 trace 与后续分析。",
    "boardroom_sim.simulator:BoardroomSimulator.simulate": "单个案例的主流程。它按角色生成初始判断，记录开场观点，执行若干轮董事会讨论，聚合最终 term sheet，并输出 SimulationResult。",
    "boardroom_sim.simulator:BoardroomSimulator._run_bargaining_round": "执行一轮讨论：按流程控制器给出的发言顺序调用角色 agent，记录发言、预测变化、会议阶段和 L5 文化约束。",
    "boardroom_sim.simulator:BoardroomSimulator._build_proposal": "把各角色的最终 RoleDecision 聚合成一个 TermSheetProposal，也就是实验最终预测的交易结果。",
    "boardroom_sim.process:BoardProcessController.prompt_context": "生成每轮发给角色的过程上下文，包含讨论协议、当前会议阶段、可见历史、L5 文化解释和可操作行为要求。",
    "boardroom_sim.process:BoardProcessController.speaking_order_for_round": "决定某一轮谁先发言、谁发言、谁不发言。这里体现 board archetype 对讨论流程的影响。",
    "boardroom_sim.process:BoardProcessController.effective_role_weights": "根据 archetype 调整角色投票/聚合权重，用于最终预测的加权汇总。",
    "boardroom_sim.culture:interpret_l5_culture": "把配置中的 L5 文化层数值解释成离散等级、行为控制和会议指令，让 LLM 看到的不只是裸数值，而是可执行的讨论规则。",
    "boardroom_sim.culture:_derive_behavior_controls": "把五个文化维度的等级转换成过程控制变量，例如是否必须回应前人、是否要求替代方案、证据锚点数量和共识压力。",
    "boardroom_sim.config:load_experiment_config": "读取 TOML 配置，并构造 ExperimentConfig。它把 LLM、输入输出、prompt、角色和 board_process 相关配置统一装配起来。",
    "boardroom_sim.config:_board_process_from_sections": "把配置文件中的 [board] 与 [discussion] 段落合成 BoardProcessConfig，是修改 archetype、L5 文化、可见历史和讨论流程的核心入口。",
    "boardroom_sim.pitchbook:build_cases_from_pitchbook": "从 PitchBook/Revelio Excel 工作簿中组装 BoardCase 列表。它关联公司、交易、投资人、员工画像、治理/董事会记录和历史融资信息。",
    "boardroom_sim.llm:LLMClient.complete_text": "执行一次 OpenAI 兼容聊天补全请求，带重试、错误处理和 token 用量记录。",
    "boardroom_sim.llm:LLMClient.complete_json": "调用 complete_text 并解析 JSON；如果返回无法解析，会追加修复指令重试。",
    "boardroom_sim.llm:extract_json_object": "从模型输出文本中抽取第一个 JSON 对象，兼容模型在 JSON 前后夹带解释文字的情况。",
    "boardroom_sim.baselines:run_single_agent_baseline": "运行单智能体基线，对同一批案例直接预测，便于和多角色董事会讨论结果比较。",
    "run_batch_experiments:main": "批量实验入口。它读取配置和数据，运行多次重复实验、断点续跑、基线预测、指标计算和 manifest 写入。",
    "run_batch_experiments:_run_cases_with_checkpoints": "带断点文件的批量模拟循环。每完成一个 case 就落盘结果、trace 和 checkpoint，方便 Ctrl+C 后继续。",
    "analyze_debate_accuracy:analyze_cases": "按阶段评估讨论前后预测是否更接近标签，用于回答多轮讨论是否改善准确率。",
    "analyze_debate_changes:analyze_cases": "统计角色观点和最终提案在讨论过程中的变化方向、变化幅度和典型案例。",
    "render_trace_report:render_report": "把 traces.json 中的模拟过程渲染成可读 Markdown 报告，便于检查每个案例的董事会发言与结果。",
}


CLASS_PURPOSES = {
    "boardroom_sim.models:BoardCase": "一个融资决策案例的完整输入。它同时保存可见案例字段、历史融资、投资人背景、员工/治理画像、真实标签和 L5 文化变量。",
    "boardroom_sim.models:RolePolicy": "一个角色的长期设定，包括可见字段、关注重点、风险偏好、谈判杠杆和输出风格。",
    "boardroom_sim.models:RoleDecision": "角色在某个时点对交易的结构化判断。实验会比较初始 RoleDecision、讨论中更新后的 RoleDecision 和最终聚合结果。",
    "boardroom_sim.models:TermSheetProposal": "多角色讨论后的最终条款预测，是实验主要输出对象。",
    "boardroom_sim.models:SimulationResult": "单个案例完整运行结果，包括最终提案、角色决策、讨论历史、trace 和真实标签。",
    "boardroom_sim.config:BoardProcessConfig": "董事会过程变量配置。它控制 archetype、发言协议、讨论轮数、可见历史、L5 文化层和角色权重。",
    "boardroom_sim.config:ExperimentConfig": "实验级配置对象。它把输入文件、输出目录、prompt、角色策略、LLM 和过程控制统一起来。",
    "boardroom_sim.llm:LLMConfig": "LLM 请求配置，包括 base_url、model、api_key、温度、超时和重试次数。",
    "boardroom_sim.llm:LLMClient": "OpenAI 兼容接口的轻量客户端，负责文本补全、JSON 补全、重试和用量统计。",
    "boardroom_sim.agents:BoardAgent": "董事会中的一个角色智能体。它知道自己的 RolePolicy，并通过 PromptRenderer 和 LLMClient 完成观察、预测和讨论发言。",
    "boardroom_sim.process:BoardProcessController": "董事会过程控制器。它把 BoardProcessConfig 转换为每轮的发言顺序、可见历史和 prompt 上下文。",
    "boardroom_sim.prompts:PromptRenderer": "Prompt 模板读取与渲染器。它把模板文件和变量合成为发给 LLM 的最终文本。",
}


ARG_PURPOSES = {
    "self": "当前对象实例，方法通过它读取配置、状态或其他方法。",
    "cls": "当前类对象，常用于 from_dict 这类类方法构造实例。",
    "case": "单个 BoardCase，代表一家公司融资/董事会决策案例。",
    "cases": "多个 BoardCase 或 trace case，用于批量运行或统计。",
    "context": "角色名到 RoleDecision 的映射，表示当前各角色的判断状态。",
    "history": "讨论历史事件列表，通常会被裁剪后放入 prompt。",
    "decision": "某个角色当前的 RoleDecision。",
    "before": "变化前的结构化判断或数值。",
    "after": "变化后的结构化判断或数值。",
    "config": "配置对象，控制 LLM、角色、prompt、过程或输出。",
    "path": "文件路径对象。",
    "paths": "一组文件路径。",
    "rows": "结果行或 DataFrame 行集合。",
    "raw": "从文件、TOML、JSON 或 LLM 读取的原始数据。",
    "value": "待清洗、转换或校验的输入值。",
    "default": "值缺失或非法时使用的默认值。",
    "metrics": "评估指标字典。",
    "results": "SimulationResult 或基线预测结果集合。",
    "messages": "发给 LLM 的 chat messages。",
    "round_index": "从 0 开始的讨论轮次索引。",
    "round_number": "从 1 开始展示给人看的讨论轮次。",
    "role_name": "角色标识，例如 founder_ceo、lead_vc_director。",
    "role_order": "角色发言或构造顺序。",
    "base_weights": "角色原始聚合权重。",
    "l5_policy": "L5 文化解释后的策略对象。",
    "controls": "由 L5 文化层推导出的过程控制变量。",
}


EXTERNAL_CALL_EXPLANATIONS = {
    "print": "内置输出函数；把文本写到控制台，返回 None。",
    "len": "内置长度函数；返回序列、字典或集合的元素数量。",
    "str": "内置类型转换；返回字符串表示。",
    "int": "内置类型转换；返回整数。",
    "float": "内置类型转换；返回浮点数。",
    "bool": "内置类型转换；返回布尔值。",
    "list": "内置容器构造；返回 list。",
    "dict": "内置容器构造；返回 dict。",
    "set": "内置容器构造；返回 set。",
    "sum": "内置求和；返回可迭代数值总和。",
    "min": "内置最小值函数；返回最小元素。",
    "max": "内置最大值函数；返回最大元素。",
    "round": "内置四舍五入；返回数值。",
    "sorted": "内置排序；返回新的 list。",
    "enumerate": "内置枚举；返回 index 和元素组成的迭代器。",
    "zip": "内置配对；返回按位置组合的迭代器。",
    "isinstance": "内置类型检查；返回 bool。",
    "getattr": "内置属性读取；返回对象属性值或默认值。",
    "setattr": "内置属性写入；返回 None。",
    "hasattr": "内置属性存在性检查；返回 bool。",
    "range": "内置整数序列；返回 range 对象。",
    "any": "内置逻辑聚合；任一元素为真时返回 True。",
    "all": "内置逻辑聚合；全部元素为真时返回 True。",
    "abs": "内置绝对值；返回数值。",
    "html.escape": "HTML 转义函数；返回可安全嵌入页面的字符串。",
    "json.dumps": "把 Python 对象序列化为 JSON 字符串，返回 str。",
    "json.loads": "把 JSON 字符串解析为 Python 对象，通常返回 dict 或 list。",
    "Path": "pathlib 路径构造器；返回 Path 对象。",
    "Path.cwd": "返回当前工作目录的 Path。",
    "Path.read_text": "读取文本文件，返回 str。",
    "Path.write_text": "写入文本文件，返回写入字符数。",
    "Path.open": "打开文件，返回文件对象。",
    "Path.exists": "检查路径是否存在，返回 bool。",
    "Path.mkdir": "创建目录，返回 None。",
    "Path.glob": "按通配符查找路径，返回迭代器。",
    "Path.relative_to": "计算相对路径，返回 Path。",
    "pd.read_excel": "读取 Excel 文件，返回 DataFrame 或 sheet_name 到 DataFrame 的字典。",
    "pd.DataFrame": "构造 pandas DataFrame，返回表格对象。",
    "pd.to_numeric": "把 Series 或标量转换为数值，返回数值或 Series。",
    "pd.to_datetime": "把日期文本/序列转换为 datetime，返回 Timestamp 或 Series。",
    "pd.Timestamp": "构造 pandas 时间戳对象。",
    "pd.isna": "判断 pandas 缺失值，返回 bool 或布尔 Series。",
    "math.isnan": "判断浮点 NaN，返回 bool。",
    "json.dump": "把 Python 对象写入文件对象为 JSON，返回 None。",
    "csv.DictWriter": "构造 CSV 字典写入器，返回 writer 对象。",
    "argparse.ArgumentParser": "构造命令行参数解析器，返回 ArgumentParser。",
    "urllib.request.Request": "构造 HTTP 请求对象。",
    "urllib.request.urlopen": "发送 HTTP 请求，返回响应对象；读取响应体需要调用 response.read()。",
    "time.sleep": "暂停当前线程，返回 None。",
    "datetime.now": "返回当前本地时间 datetime。",
    "Counter": "collections 计数器；返回可统计频次的字典子类。",
    "defaultdict": "collections 默认字典；访问缺失键时自动构造默认值。",
    "asdict": "dataclasses 工具；把 dataclass 实例递归转换为 dict。",
    "dataclass": "dataclasses 装饰器；为类生成初始化、repr、比较等方法，返回类对象。",
    "field": "dataclasses 字段声明工具；返回字段描述对象。",
    "tomllib.load": "读取 TOML 文件对象并解析，返回 dict。",
    "re.search": "正则搜索；返回 match 对象或 None。",
    "re.sub": "正则替换；返回替换后的字符串。",
    "re.findall": "正则查找全部匹配；返回列表。",
}


def module_summary(path: Path) -> str:
    name = rel(path)
    if name == "run_batch_experiments.py":
        return "批量实验主脚本：读取 Excel/JSONL 输入，运行多次模拟、断点续跑、基线预测、指标计算和 manifest 输出。"
    if name == "run_experiment.py":
        return "单次实验脚本：适合小规模调试，从输入案例构造模拟器并写出 results/traces。"
    if name == "analyze_debate_accuracy.py":
        return "讨论准确率分析脚本：比较初始预测、各轮预测、最终预测与真实标签之间的关系。"
    if name == "analyze_debate_changes.py":
        return "讨论变化分析脚本：统计角色观点、数值预测和最终提案在讨论中的变化。"
    if name == "render_trace_report.py":
        return "trace 渲染脚本：把机器可读 traces.json 转为人类可读 Markdown 报告。"
    if name == "evaluate_results.py":
        return "结果评估入口：从 results.jsonl 读取模拟输出并生成指标。"
    if name.endswith("agents.py"):
        return "角色智能体模块：负责观察案例、构造 prompt、调用 LLM、清洗角色预测和记录讨论行为。"
    if name.endswith("baselines.py"):
        return "基线模块：实现单智能体历史信息预测，用来与多角色讨论实验对照。"
    if name.endswith("config.py"):
        return "配置模块：把 TOML 配置转换成 Python dataclass，集中管理实验变量。"
    if name.endswith("culture.py"):
        return "L5 文化层模块：把文化分数解释为会议行为约束和 prompt 指令。"
    if name.endswith("evaluation.py"):
        return "指标模块：读取结果并计算分类准确率、数值误差、案例级指标和摘要文本。"
    if name.endswith("io.py"):
        return "输入输出模块：读写 JSONL 结果、案例和 trace。"
    if name.endswith("llm.py"):
        return "LLM 客户端模块：封装 OpenAI 兼容接口、JSON 抽取、重试和用量记录。"
    if name.endswith("models.py"):
        return "数据模型模块：定义 BoardCase、RoleDecision、TermSheetProposal、SimulationResult 等核心结构。"
    if name.endswith("pitchbook.py"):
        return "PitchBook/Revelio 数据接入模块：从 Excel 多张表中构造实验案例和真实标签。"
    if name.endswith("process.py"):
        return "董事会流程控制模块：控制发言顺序、可见历史、archetype、L5 文化和每轮 prompt 上下文。"
    if name.endswith("prompts.py"):
        return "Prompt 模板模块：读取 Markdown prompt 并替换变量。"
    if name.endswith("roles.py"):
        return "角色策略模块：从 TOML 或内置默认值构建各董事会角色的 RolePolicy。"
    if name.endswith("simulator.py"):
        return "模拟器模块：组织角色初始预测、会议讨论、最终聚合和 trace 记录。"
    return "项目源文件。教程按函数和类解释它在实验中的作用。"


def explain_function(fn: FunctionInfo) -> str:
    key = f"{fn.module}:{fn.qualname}"
    if key in CORE_FUNCTION_PURPOSES:
        return CORE_FUNCTION_PURPOSES[key]
    if fn.doc:
        return f"源码文档说明：{compact(fn.doc)}"
    name = fn.name
    module = fn.module
    if name == "parse_args":
        return "解析命令行参数，返回 argparse.Namespace。调用方用它决定输入、输出、配置、case 数量和分析选项。"
    if name == "main":
        return "脚本入口函数。它串联参数解析、文件读写、核心计算和结果输出。"
    if name.startswith(("safe_", "coerce_", "_as_", "_optional_", "_normalize", "normalize")):
        return "数据清洗/标准化函数。它把原始值转换为实验需要的类型或标签，并在缺失、非法、大小写不一致时提供稳定兜底。"
    if name.startswith(("read_", "_read_")):
        return "读取函数。它从文件或结果对象中取出结构化数据，返回后续评估、渲染或模拟流程可直接使用的 Python 对象。"
    if name.startswith(("write_", "_write_")):
        return "写入函数。它把结果、指标、trace 或中间 checkpoint 落盘，通常返回 None。"
    if name.startswith(("render_", "_render_")):
        return "渲染函数。它把结构化结果转换为 Markdown/HTML/表格文本，方便人类阅读实验过程或指标。"
    if name.startswith(("build_", "_build_")):
        return "构造函数。它把原始配置、输入行或中间状态组装成更高层的数据结构。"
    if name.startswith(("analyze_", "_analyze_")):
        return "分析函数。它遍历案例或结果行，计算变化、准确率、误差或典型案例。"
    if name.startswith(("_aggregate", "aggregate_")):
        return "聚合函数。它把多个角色、多个阶段或多行结果合成为一个最终判断或统计值。"
    if name.startswith(("compare_", "_compare_")):
        return "比较函数。它把预测值和真实标签或前后状态放在一起，返回是否匹配、误差或变化方向。"
    if name.startswith(("_format", "format_", "_fmt")):
        return "格式化函数。它把数值或标签转成报告中更易读的字符串。"
    if name.startswith(("_is_", "is_")):
        return "判断函数。它检查输入是否满足某种条件，返回 bool。"
    if "pitchbook" in module:
        return "PitchBook 数据处理辅助函数。它从 DataFrame 中筛选、关联或派生字段，服务于 BoardCase 构造。"
    if "evaluation" in module:
        return "评估辅助函数。它服务于结果标准化、指标计算或案例级指标写出。"
    if "models" in module and name == "to_dict":
        return "把 dataclass 模型转换成可 JSON 序列化的 dict，供输出文件和 trace 使用。"
    if "models" in module and name == "from_dict":
        return "从原始字典构造数据模型实例，同时执行类型清洗和默认值处理。"
    return "项目辅助函数。它的具体行为可从参数、返回值和下方源码确认；调用关系区域列出了它依赖的内部函数和外部库函数。"


def compact(text: str, limit: int = 260) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def explain_arg(name: str) -> str:
    clean = name.lstrip("*")
    if clean in ARG_PURPOSES:
        return ARG_PURPOSES[clean]
    if clean.endswith("_path") or clean.endswith("path"):
        return "文件路径参数，通常是 pathlib.Path 或可转换为路径的值。"
    if clean.endswith("_dir"):
        return "目录路径参数，用于读取配置或写出结果。"
    if clean.endswith("_df") or clean in {"df", "deal_df", "employee_history"}:
        return "pandas DataFrame，表示 Excel 中的一张表或筛选后的表。"
    if clean.endswith("_id") or clean == "case_id":
        return "业务对象标识符，用于关联案例、公司、交易或投资人。"
    if clean.endswith("_limit") or clean == "limit":
        return "数量上限，用于截断历史记录、案例数量或输出条目。"
    if clean.endswith("_tolerance") or clean == "tolerance":
        return "误差容忍阈值，用于判断数值变化或预测是否可接受。"
    return "函数局部输入参数；结合签名和源码可看到它如何参与计算。"


def explain_return(fn: FunctionInfo) -> str:
    if fn.name == "__init__":
        return "初始化方法，通常返回 None；主要副作用是给 self 写入属性。"
    if fn.returns:
        return f"返回 `{esc(fn.returns)}` 类型或兼容该注解的对象。"
    if fn.name.startswith(("write_", "_write_", "main")):
        return "通常返回 None，主要通过写文件或打印结果产生副作用。"
    if fn.name.startswith(("is_", "_is_")):
        return "返回 bool。"
    if fn.name.startswith(("render_", "_render_", "format_", "_format", "_fmt")):
        return "返回字符串，供报告或控制台展示。"
    if fn.name.startswith(("read_", "_read_")):
        return "返回从文件读取并解析后的 Python 对象。"
    if fn.name.startswith(("build_", "_build_")):
        return "返回新构造的数据结构或模型对象。"
    return "返回值见源码中的 return 语句；若无显式 return，则返回 None。"


def build_indices(
    functions: list[FunctionInfo], classes: list[ClassInfo]
) -> tuple[dict[str, FunctionInfo], dict[str, list[FunctionInfo]], dict[str, ClassInfo], dict[str, list[ClassInfo]]]:
    fn_by_key = {f"{fn.module}:{fn.qualname}": fn for fn in functions}
    fn_by_name: dict[str, list[FunctionInfo]] = {}
    class_by_key = {f"{cls.module}:{cls.qualname}": cls for cls in classes}
    class_by_name: dict[str, list[ClassInfo]] = {}
    for fn in functions:
        fn_by_name.setdefault(fn.name, []).append(fn)
    for cls in classes:
        class_by_name.setdefault(cls.name, []).append(cls)
    return fn_by_key, fn_by_name, class_by_key, class_by_name


def resolve_project_call(
    call: str,
    current: FunctionInfo,
    fn_by_key: dict[str, FunctionInfo],
    fn_by_name: dict[str, list[FunctionInfo]],
    class_by_name: dict[str, list[ClassInfo]],
) -> list[FunctionInfo | ClassInfo]:
    last = call.split(".")[-1]
    if call.startswith("self.") and "." in current.qualname:
        class_part = current.qualname.rsplit(".", 1)[0]
        same_class_key = f"{current.module}:{class_part}.{last}"
        if same_class_key in fn_by_key:
            return [fn_by_key[same_class_key]]
    same_module_key = f"{current.module}:{call}"
    if same_module_key in fn_by_key:
        return [fn_by_key[same_module_key]]
    same_module_last_key = f"{current.module}:{last}"
    if same_module_last_key in fn_by_key:
        return [fn_by_key[same_module_last_key]]
    if last in fn_by_name:
        return list(fn_by_name[last])
    if call in class_by_name:
        return list(class_by_name[call])
    if last in class_by_name:
        return list(class_by_name[last])
    return []


def external_call_explanation(call: str) -> str:
    if call in EXTERNAL_CALL_EXPLANATIONS:
        return EXTERNAL_CALL_EXPLANATIONS[call]
    suffixes = {
        ".get": "字典或对象映射读取；按键取值，缺失时可返回默认值。",
        ".items": "字典遍历方法；返回 key/value 对迭代视图。",
        ".keys": "字典键视图；返回所有 key。",
        ".values": "字典值视图；返回所有 value。",
        ".append": "列表追加方法；把元素加入列表末尾，返回 None。",
        ".extend": "列表扩展方法；把多个元素追加到列表末尾，返回 None。",
        ".sort": "列表原地排序方法；返回 None。",
        ".strip": "字符串去除首尾空白，返回新字符串。",
        ".lower": "字符串转小写，返回新字符串。",
        ".upper": "字符串转大写，返回新字符串。",
        ".split": "字符串拆分，返回 list[str]。",
        ".join": "字符串连接，返回 str。",
        ".replace": "字符串替换，返回新字符串。",
        ".startswith": "字符串前缀判断，返回 bool。",
        ".endswith": "字符串后缀判断，返回 bool。",
        ".read": "文件或响应对象读取；返回 bytes 或 str，取决于对象类型。",
        ".decode": "bytes 解码为字符串，返回 str。",
        ".to_dict": "对象转字典方法；如果是 pandas/dataclass/项目模型，返回 dict。",
        ".to_csv": "pandas DataFrame 写 CSV，返回 None 或字符串。",
        ".sort_values": "pandas DataFrame 排序，返回新的 DataFrame。",
        ".dropna": "pandas 缺失值过滤，返回 Series/DataFrame。",
        ".fillna": "pandas 缺失值填充，返回 Series/DataFrame。",
        ".unique": "pandas/NumPy 唯一值提取，返回数组。",
        ".tolist": "pandas/NumPy 转 Python list。",
        ".iterrows": "pandas DataFrame 行遍历，返回 index 与 row 的迭代器。",
    }
    for suffix, explanation in suffixes.items():
        if call.endswith(suffix):
            return explanation
    if call.startswith("pd."):
        return "pandas 库函数；用于表格读取、转换、筛选或时间/数值处理，返回 pandas 对象或标量。"
    if call.startswith("json."):
        return "json 标准库函数；用于 JSON 序列化或反序列化。"
    if call.startswith("Path.") or call.startswith("path."):
        return "pathlib 路径方法；用于路径拼接、检测、读写或遍历。"
    if call.startswith("re."):
        return "正则表达式函数；返回匹配结果或处理后的字符串。"
    if call.startswith("math."):
        return "math 数学函数；返回数值或布尔判断。"
    return "外部库函数或对象方法；当前函数调用它取得中间结果、执行 IO 或完成对象方法调用。"


def call_rows(
    fn: FunctionInfo,
    fn_by_key: dict[str, FunctionInfo],
    fn_by_name: dict[str, list[FunctionInfo]],
    class_by_name: dict[str, list[ClassInfo]],
) -> str:
    if not fn.calls:
        return "<p class=\"muted\">这个函数没有显式函数调用，主要是字段访问、表达式或常量返回。</p>"

    rows: list[str] = []
    for call in fn.calls:
        targets = resolve_project_call(call, fn, fn_by_key, fn_by_name, class_by_name)
        if targets:
            links = []
            for target in targets[:6]:
                kind = "类" if isinstance(target, ClassInfo) else "函数"
                links.append(
                    f"<a href=\"#{target.anchor}\">{esc(target.module)}.{esc(target.qualname)}</a><span class=\"pill\">{kind}</span>"
                )
            if len(targets) > 6:
                links.append(f"<span class=\"muted\">另有 {len(targets) - 6} 个同名候选</span>")
            explanation = "项目内调用；点击链接可跳到对应函数或类说明。"
            if len(targets) > 1:
                explanation = "项目内同名候选；实际调用由对象类型或导入绑定决定，下面列出可跳转的候选说明。"
            rows.append(
                "<tr>"
                f"<td><code>{esc(call)}</code></td>"
                f"<td>{' '.join(links)}</td>"
                f"<td>{esc(explanation)}</td>"
                "</tr>"
            )
        else:
            rows.append(
                "<tr>"
                f"<td><code>{esc(call)}</code></td>"
                "<td><span class=\"pill external\">库/对象方法</span></td>"
                f"<td>{esc(external_call_explanation(call))}</td>"
                "</tr>"
            )
    return "<table class=\"call-table\"><thead><tr><th>调用名</th><th>目标</th><th>作用与返回</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def parameter_table(fn: FunctionInfo) -> str:
    if not fn.args:
        return "<p class=\"muted\">无显式参数。</p>"
    rows = [
        f"<tr><td><code>{esc(arg)}</code></td><td>{esc(explain_arg(arg))}</td></tr>"
        for arg in fn.args
    ]
    return "<table class=\"param-table\"><thead><tr><th>参数</th><th>含义</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def function_card(
    fn: FunctionInfo,
    fn_by_key: dict[str, FunctionInfo],
    fn_by_name: dict[str, list[FunctionInfo]],
    class_by_name: dict[str, list[ClassInfo]],
    reverse_calls: dict[str, list[FunctionInfo]],
) -> str:
    callers = reverse_calls.get(f"{fn.module}:{fn.qualname}", [])
    caller_links = " ".join(
        f"<a class=\"small-link\" href=\"#{caller.anchor}\">{esc(caller.module)}.{esc(caller.qualname)}</a>"
        for caller in callers[:12]
    )
    if len(callers) > 12:
        caller_links += f" <span class=\"muted\">另有 {len(callers) - 12} 个调用方</span>"
    if not caller_links:
        caller_links = "<span class=\"muted\">未发现项目内其他函数直接调用；可能由命令行入口、类实例化或外部调用触发。</span>"

    return f"""
<article class="function-card" id="{fn.anchor}">
  <div class="card-head">
    <div>
      <h3>{esc(fn.qualname)}</h3>
      <p class="path">{esc(rel(fn.file))}:{fn.lineno}-{fn.end_lineno}</p>
    </div>
    <a class="top-link" href="#top">回到顶部</a>
  </div>
  <pre class="signature"><code>{esc(fn.signature)}</code></pre>
  <section>
    <h4>功能</h4>
    <p>{esc(explain_function(fn))}</p>
  </section>
  <section>
    <h4>参数</h4>
    {parameter_table(fn)}
  </section>
  <section>
    <h4>返回值</h4>
    <p>{explain_return(fn)}</p>
  </section>
  <section>
    <h4>调用的函数</h4>
    {call_rows(fn, fn_by_key, fn_by_name, class_by_name)}
  </section>
  <section>
    <h4>被谁调用</h4>
    <p>{caller_links}</p>
  </section>
  <details>
    <summary>查看完整源码</summary>
    <pre class="code-block"><code>{esc(fn.source)}</code></pre>
  </details>
</article>
"""


def class_card(cls: ClassInfo, methods_by_class: dict[str, list[FunctionInfo]]) -> str:
    key = f"{cls.module}:{cls.qualname}"
    purpose = CLASS_PURPOSES.get(key) or "项目类。它把相关数据和行为组织在一起，字段与方法如下。"
    bases = ", ".join(cls.bases) if cls.bases else "无显式父类"
    fields = "".join(f"<li><code>{esc(field)}</code></li>" for field in cls.fields) or "<li class=\"muted\">未从源码中识别到固定字段。</li>"
    method_links = "".join(
        f"<li><a href=\"#{method.anchor}\">{esc(method.name)}</a></li>"
        for method in methods_by_class.get(key, [])
    ) or "<li class=\"muted\">无方法。</li>"
    example = class_example(cls)
    return f"""
<article class="class-card" id="{cls.anchor}">
  <div class="card-head">
    <div>
      <h3>{esc(cls.qualname)}</h3>
      <p class="path">{esc(rel(cls.file))}:{cls.lineno}-{cls.end_lineno}</p>
    </div>
    <a class="top-link" href="#top">回到顶部</a>
  </div>
  <p>{esc(purpose)}</p>
  <p><strong>父类/基类：</strong>{esc(bases)}</p>
  <div class="two-col">
    <div>
      <h4>字段/属性</h4>
      <ul>{fields}</ul>
    </div>
    <div>
      <h4>方法</h4>
      <ul>{method_links}</ul>
    </div>
  </div>
  {example}
</article>
"""


def class_example(cls: ClassInfo) -> str:
    key = f"{cls.module}:{cls.qualname}"
    examples = {
        "boardroom_sim.models:BoardCase": "例：`case_id='9244942_963111474T'` 表示一个交易案例；`deal_size_usd_m=12.5` 表示融资金额；`l5_culture={'trust': 0.7, ...}` 会进入流程控制和 prompt。",
        "boardroom_sim.models:RoleDecision": "例：Founder CEO 可以给出 `financing_intent='yes'`、`deal_size_usd_m=15`、`rationale=['cash runway is short']`，后续讨论会更新这些字段。",
        "boardroom_sim.models:TermSheetProposal": "例：最终输出 `deal_completion_view='completed'`、`deal_type='priced_round'`、`estimated_dilution_pct=18.0`，用于和真实标签计算误差。",
        "boardroom_sim.config:BoardProcessConfig": "例：`board_archetype='value_creating'` 会让会议更重视证据、挑战和替代方案；`discussion_rounds=3` 控制讨论轮数。",
        "boardroom_sim.llm:LLMConfig": "例：`base_url='https://api.openai.com/v1/chat/completions'`、`model='gpt-4.1-mini'`、`timeout_seconds=120` 控制请求目标和超时。",
        "boardroom_sim.agents:BoardAgent": "例：一个 `BoardAgent(role_policy=founder_ceo, ...)` 只看到创始人角色允许看到的字段，并按创始人的目标发言。",
        "boardroom_sim.process:BoardProcessController": "例：同样四个角色，在 `barbarian` 和 `clan` archetype 下会得到不同发言顺序、不同主席压力和不同 L5 行为指令。",
    }
    text = examples.get(key)
    if not text:
        return ""
    return f"<p class=\"example\"><strong>例子：</strong>{esc(text)}</p>"


def reverse_call_index(
    functions: list[FunctionInfo],
    fn_by_key: dict[str, FunctionInfo],
    fn_by_name: dict[str, list[FunctionInfo]],
    class_by_name: dict[str, list[ClassInfo]],
) -> dict[str, list[FunctionInfo]]:
    reverse: dict[str, list[FunctionInfo]] = {}
    for fn in functions:
        for call in fn.calls:
            for target in resolve_project_call(call, fn, fn_by_key, fn_by_name, class_by_name):
                if isinstance(target, FunctionInfo):
                    reverse.setdefault(f"{target.module}:{target.qualname}", []).append(fn)
    return reverse


def methods_by_class(functions: list[FunctionInfo]) -> dict[str, list[FunctionInfo]]:
    mapping: dict[str, list[FunctionInfo]] = {}
    for fn in functions:
        if "." in fn.qualname:
            class_qual = fn.qualname.rsplit(".", 1)[0]
            mapping.setdefault(f"{fn.module}:{class_qual}", []).append(fn)
    return mapping


def text_file_section(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return f"""
<section class="file-section" id="{safe_anchor('file', rel(path))}">
  <h2>{esc(rel(path))}</h2>
  <p>{esc(explain_text_file(path))}</p>
  <details open>
    <summary>查看文件内容</summary>
    <pre class="code-block"><code>{esc(text.rstrip())}</code></pre>
  </details>
</section>
"""


def explain_text_file(path: Path) -> str:
    name = rel(path)
    if name == "configs/boardroom_default.toml":
        return "默认实验配置。这里是后续最常修改的位置：输入文件、输出目录、LLM、角色顺序、角色权重、讨论轮数、archetype、L5 文化层和可见历史字段都在这里控制。"
    if name.startswith("policies/roles/"):
        return "角色策略配置。每个 TOML 文件定义一个董事会角色的目标、可见字段、风险偏好、谈判杠杆和行为风格。"
    if name.startswith("prompts/response_generators/"):
        return "回复风格片段。PromptRenderer 会把它嵌入角色 prompt，用来控制模型回答的推理深度和批判性。"
    if name.startswith("prompts/"):
        return "LLM prompt 模板。代码会用 `.format(...)` 注入案例、角色、历史、流程和 L5 文化变量。"
    if name == "requirements.txt":
        return "Python 依赖清单。新环境可以用 `python -m pip install -r requirements.txt` 一键安装。"
    if name == "one_case.sh":
        return "单案例运行脚本示例，便于快速 smoke test。"
    return "非 Python 源文件，教程保留原文以便直接查阅和修改。"


def workflow_section(functions: list[FunctionInfo]) -> str:
    fn_by_key = {f"{fn.module}:{fn.qualname}": fn for fn in functions}

    def link(key: str, label: str) -> str:
        fn = fn_by_key.get(key)
        if not fn:
            return esc(label)
        return f"<a href=\"#{fn.anchor}\">{esc(label)}</a>"

    steps = [
        (
            "读取配置与输入",
            f"{link('run_batch_experiments:main', 'run_batch_experiments.main')} 调用 {link('boardroom_sim.config:load_experiment_config', 'load_experiment_config')} 读取 TOML，再用 {link('boardroom_sim.pitchbook:build_cases_from_pitchbook', 'build_cases_from_pitchbook')} 从 Excel 构造 BoardCase。",
        ),
        (
            "构造角色和流程",
            f"配置中的角色 TOML 进入 RolePolicy；{link('boardroom_sim.process:BoardProcessController.prompt_context', 'BoardProcessController.prompt_context')} 每轮生成可见历史、会议阶段和 L5 文化指令。",
        ),
        (
            "初始预测",
            f"{link('boardroom_sim.agents:BoardAgent.evaluate', 'BoardAgent.evaluate')} 为每个角色生成初始 RoleDecision。",
        ),
        (
            "多轮讨论",
            f"{link('boardroom_sim.simulator:BoardroomSimulator._run_bargaining_round', 'BoardroomSimulator._run_bargaining_round')} 按发言顺序调用 {link('boardroom_sim.agents:BoardAgent.bargaining_step', 'BoardAgent.bargaining_step')}，并记录会议行为字段。",
        ),
        (
            "最终聚合",
            f"{link('boardroom_sim.simulator:BoardroomSimulator._build_proposal', 'BoardroomSimulator._build_proposal')} 把角色最终判断合成为 TermSheetProposal。",
        ),
        (
            "评估与报告",
            f"批量脚本写出 results/traces 后，再调用评估和分析脚本生成 case_metrics、aggregate_metrics、debate_accuracy_report 等文件。",
        ),
    ]
    items = "".join(f"<li><strong>{title}</strong><span>{body}</span></li>" for title, body in steps)
    return f"""
<section class="panel" id="workflow">
  <h2>函数调用主线</h2>
  <ol class="workflow">{items}</ol>
</section>
"""


def progress_section() -> str:
    return """
<section class="panel" id="progress">
  <h2>当前实验进度</h2>
  <p>当前代码已经从“硬编码 prompt 的简单模拟”改造成更接近可扩展框架的版本：角色、prompt、可见字段、讨论轮次、发言顺序、board archetype 和 L5 文化层都可以通过配置或模板文件调整。</p>
  <ul>
    <li><strong>框架化：</strong>配置集中在 <code>configs/boardroom_default.toml</code>，角色放在 <code>policies/roles/*.toml</code>，prompt 放在 <code>prompts/*.md</code>。</li>
    <li><strong>过程变量：</strong><code>BoardProcessController</code> 负责发言顺序、可见历史、会议阶段和过程指令。</li>
    <li><strong>L5 文化层：</strong><code>culture.py</code> 把文化分数解释为行为控制，再进入每轮 prompt。</li>
    <li><strong>数据升级：</strong>默认输入指向更完整的 PitchBook/Revelio Excel 文件，可从字段字典继续挑选更多变量。</li>
    <li><strong>可恢复运行：</strong>批量脚本支持 checkpoint，Ctrl+C 后可以通过 resume 逻辑继续已完成 case 后面的工作。</li>
  </ul>
</section>
"""


def file_index(source_files: list[Path], functions_by_file: dict[Path, list[FunctionInfo]], classes_by_file: dict[Path, list[ClassInfo]]) -> str:
    rows: list[str] = []
    for path in source_files:
        anchor = safe_anchor("module", rel(path)) if path.suffix == ".py" else safe_anchor("file", rel(path))
        rows.append(
            "<tr>"
            f"<td><a href=\"#{anchor}\">{esc(rel(path))}</a></td>"
            f"<td>{len(functions_by_file.get(path, []))}</td>"
            f"<td>{len(classes_by_file.get(path, []))}</td>"
            f"<td>{esc(module_summary(path) if path.suffix == '.py' else explain_text_file(path))}</td>"
            "</tr>"
        )
    return "<table class=\"index-table\"><thead><tr><th>文件</th><th>函数</th><th>类</th><th>作用</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table>"


def sidebar(source_files: list[Path]) -> str:
    links = [
        "<a href=\"#overview\">概览</a>",
        "<a href=\"#workflow\">调用主线</a>",
        "<a href=\"#progress\">进度报告</a>",
        "<a href=\"#classes\">类与参数</a>",
        "<a href=\"#python-files\">逐函数讲解</a>",
        "<a href=\"#text-files\">配置与 Prompt</a>",
    ]
    file_links = []
    for path in source_files:
        anchor = safe_anchor("module", rel(path)) if path.suffix == ".py" else safe_anchor("file", rel(path))
        file_links.append(f"<a href=\"#{anchor}\">{esc(rel(path))}</a>")
    return "<aside class=\"sidebar\"><h2>目录</h2>" + "".join(links) + "<h3>文件</h3>" + "".join(file_links) + "</aside>"


def build_html() -> str:
    source_files = collect_source_files()
    functions, classes, _ = parse_python_files(source_files)
    fn_by_key, fn_by_name, _, class_by_name = build_indices(functions, classes)
    reverse_calls = reverse_call_index(functions, fn_by_key, fn_by_name, class_by_name)
    method_map = methods_by_class(functions)

    functions_by_file: dict[Path, list[FunctionInfo]] = {}
    classes_by_file: dict[Path, list[ClassInfo]] = {}
    for fn in functions:
        functions_by_file.setdefault(fn.file, []).append(fn)
    for cls in classes:
        classes_by_file.setdefault(cls.file, []).append(cls)

    class_cards = "".join(class_card(cls, method_map) for cls in classes)

    py_sections: list[str] = []
    for path in [p for p in source_files if p.suffix == ".py"]:
        fn_cards = "".join(
            function_card(fn, fn_by_key, fn_by_name, class_by_name, reverse_calls)
            for fn in functions_by_file.get(path, [])
        )
        cls_links = " ".join(
            f"<a class=\"small-link\" href=\"#{cls.anchor}\">{esc(cls.qualname)}</a>"
            for cls in classes_by_file.get(path, [])
        )
        if not cls_links:
            cls_links = "<span class=\"muted\">无类定义</span>"
        py_sections.append(
            f"""
<section class="module-section" id="{safe_anchor('module', rel(path))}">
  <h2>{esc(rel(path))}</h2>
  <p>{esc(module_summary(path))}</p>
  <p><strong>类：</strong>{cls_links}</p>
  {fn_cards}
</section>
"""
        )

    text_sections = "".join(text_file_section(path) for path in source_files if path.suffix != ".py")
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Boardroom Sim MVP 完整代码教程</title>
  <style>
    :root {{
      color-scheme: light;
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #657282;
      --line: #d8dee6;
      --soft: #eef2f6;
      --accent: #2454a6;
      --accent-soft: #e8eefb;
      --code-bg: #0f1720;
      --code-text: #e8edf4;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", sans-serif;
      line-height: 1.65;
    }}
    a {{ color: var(--accent); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .layout {{
      display: grid;
      grid-template-columns: 300px minmax(0, 1fr);
      min-height: 100vh;
    }}
    .sidebar {{
      position: sticky;
      top: 0;
      height: 100vh;
      overflow: auto;
      padding: 24px 18px;
      background: #ffffff;
      border-right: 1px solid var(--line);
    }}
    .sidebar h2 {{ margin: 0 0 14px; font-size: 20px; }}
    .sidebar h3 {{ margin: 24px 0 10px; font-size: 13px; color: var(--muted); }}
    .sidebar a {{
      display: block;
      padding: 7px 8px;
      border-radius: 6px;
      font-size: 13px;
      color: #26384d;
      overflow-wrap: anywhere;
    }}
    .sidebar a:hover {{ background: var(--soft); text-decoration: none; }}
    main {{ max-width: 1180px; width: 100%; padding: 34px 42px 80px; }}
    .hero {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 28px;
      margin-bottom: 22px;
    }}
    .hero h1 {{ margin: 0 0 8px; font-size: 30px; letter-spacing: 0; }}
    .hero p {{ margin: 6px 0; color: var(--muted); }}
    .stats {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      margin-top: 18px;
    }}
    .stat {{
      background: var(--soft);
      border-radius: 8px;
      padding: 12px;
    }}
    .stat strong {{ display: block; font-size: 22px; }}
    .panel, .module-section, .file-section, .class-card, .function-card {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 22px;
      margin: 18px 0;
    }}
    h2 {{ margin: 0 0 14px; font-size: 24px; }}
    h3 {{ margin: 0; font-size: 19px; }}
    h4 {{ margin: 18px 0 8px; font-size: 14px; color: #33465f; }}
    .path, .muted {{ color: var(--muted); }}
    .path {{ margin: 3px 0 0; font-size: 13px; }}
    .card-head {{
      display: flex;
      justify-content: space-between;
      gap: 18px;
      align-items: flex-start;
      border-bottom: 1px solid var(--line);
      padding-bottom: 12px;
      margin-bottom: 14px;
    }}
    .top-link, .small-link {{
      display: inline-block;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 2px 8px;
      margin: 2px;
      font-size: 12px;
      background: #fff;
    }}
    .signature {{
      background: var(--accent-soft);
      color: #102544;
      border: 1px solid #ccd8ef;
      border-radius: 8px;
      padding: 12px;
      overflow-x: auto;
      white-space: pre;
    }}
    .code-block {{
      background: var(--code-bg);
      color: var(--code-text);
      border-radius: 8px;
      padding: 16px;
      overflow-x: auto;
      font-size: 13px;
      line-height: 1.55;
      tab-size: 4;
    }}
    code {{
      font-family: "Cascadia Code", "Consolas", "Menlo", monospace;
      font-size: 0.92em;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 10px 0;
      table-layout: auto;
    }}
    th, td {{
      border: 1px solid var(--line);
      padding: 9px 10px;
      vertical-align: top;
      text-align: left;
      overflow-wrap: anywhere;
    }}
    th {{
      background: var(--soft);
      color: #34465c;
      font-size: 13px;
    }}
    .call-table td:first-child, .param-table td:first-child {{
      width: 190px;
      white-space: nowrap;
    }}
    .index-table td:nth-child(2), .index-table td:nth-child(3) {{
      width: 72px;
      text-align: right;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 18px;
    }}
    .pill {{
      display: inline-block;
      padding: 1px 6px;
      margin-left: 5px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #274f93;
      font-size: 11px;
    }}
    .pill.external {{ background: #f3f4f6; color: #5b6470; margin-left: 0; }}
    details {{
      margin-top: 12px;
    }}
    summary {{
      cursor: pointer;
      color: var(--accent);
      font-weight: 600;
    }}
    .workflow {{
      padding-left: 22px;
    }}
    .workflow li {{
      margin: 12px 0;
    }}
    .workflow span {{
      display: block;
      color: #3d4d61;
    }}
    .example {{
      background: #fbfaf4;
      border: 1px solid #e7dcc2;
      border-radius: 8px;
      padding: 10px 12px;
    }}
    @media (max-width: 980px) {{
      .layout {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; height: auto; border-right: 0; border-bottom: 1px solid var(--line); }}
      main {{ padding: 22px 16px 60px; }}
      .stats, .two-col {{ grid-template-columns: 1fr; }}
      .card-head {{ flex-direction: column; }}
      .call-table td:first-child, .param-table td:first-child {{ width: auto; white-space: normal; }}
    }}
  </style>
</head>
<body>
<div class="layout" id="top">
  {sidebar(source_files)}
  <main>
    <section class="hero" id="overview">
      <h1>Boardroom Sim MVP 完整代码教程</h1>
      <p>生成时间：{esc(generated_at)}</p>
      <p>本版已取消逐行表格，改为逐函数讲解。每个函数包含功能、参数、返回值、调用关系和完整源码；项目内调用可跳转，库函数会解释作用和返回值。</p>
      <div class="stats">
        <div class="stat"><strong>{len(source_files)}</strong><span>纳入文件</span></div>
        <div class="stat"><strong>{len(functions)}</strong><span>函数/方法</span></div>
        <div class="stat"><strong>{len(classes)}</strong><span>类</span></div>
        <div class="stat"><strong>{sum(1 for p in source_files if p.suffix != '.py')}</strong><span>配置/Prompt</span></div>
      </div>
    </section>

    <section class="panel">
      <h2>文件索引</h2>
      {file_index(source_files, functions_by_file, classes_by_file)}
    </section>

    {workflow_section(functions)}
    {progress_section()}

    <section class="panel" id="classes">
      <h2>类与参数</h2>
      <p>这里集中解释项目中的类。类方法会链接到后面的逐函数讲解，字段用于理解每个对象携带的实验变量。</p>
    </section>
    {class_cards}

    <section class="panel" id="python-files">
      <h2>逐函数讲解</h2>
      <p>以下按文件排列。每个函数都保留完整源码块，但不再做逐行解释；重点解释函数功能、输入输出和它调用了哪些内部/外部函数。</p>
    </section>
    {''.join(py_sections)}

    <section class="panel" id="text-files">
      <h2>配置与 Prompt 文件</h2>
      <p>这些文件不是 Python 函数，但它们决定实验变量、角色策略和 LLM 行为。教程保留全文，方便直接修改。</p>
    </section>
    {text_sections}
  </main>
</div>
</body>
</html>
"""


def md_text(value: Any) -> str:
    return str(value).replace("\r", "").strip()


def md_table_cell(value: Any) -> str:
    text = re.sub(r"\s+", " ", str(value).replace("\r", " ")).strip()
    return text.replace("|", "\\|")


def md_inline_code(value: Any) -> str:
    text = str(value).replace("`", "\\`")
    return f"`{text}`"


def md_link(label: str, anchor: str) -> str:
    return f"[{md_table_cell(label)}](#{anchor})"


def md_fence(content: str, lang: str = "text") -> str:
    fence = "~~~~"
    while fence in content:
        fence += "~"
    return f"{fence}{lang}\n{content.rstrip()}\n{fence}"


def language_for(path: Path) -> str:
    if path.suffix == ".py":
        return "python"
    if path.suffix == ".toml":
        return "toml"
    if path.suffix == ".md":
        return "markdown"
    if path.suffix == ".sh":
        return "bash"
    if path.name == "requirements.txt":
        return "text"
    return "text"


def explain_return_markdown(fn: FunctionInfo) -> str:
    if fn.name == "__init__":
        return "初始化方法，通常返回 `None`；主要副作用是给 `self` 写入属性。"
    if fn.returns:
        return f"返回 `{fn.returns}` 类型或兼容该注解的对象。"
    if fn.name.startswith(("write_", "_write_", "main")):
        return "通常返回 `None`，主要通过写文件或打印结果产生副作用。"
    if fn.name.startswith(("is_", "_is_")):
        return "返回 `bool`。"
    if fn.name.startswith(("render_", "_render_", "format_", "_format", "_fmt")):
        return "返回字符串，供报告或控制台展示。"
    if fn.name.startswith(("read_", "_read_")):
        return "返回从文件读取并解析后的 Python 对象。"
    if fn.name.startswith(("build_", "_build_")):
        return "返回新构造的数据结构或模型对象。"
    return "返回值见源码中的 `return` 语句；若无显式 `return`，则返回 `None`。"


def markdown_parameter_table(fn: FunctionInfo) -> str:
    if not fn.args:
        return "无显式参数。"
    rows = ["| 参数 | 含义 |", "| --- | --- |"]
    for arg in fn.args:
        rows.append(f"| {md_inline_code(arg)} | {md_table_cell(explain_arg(arg))} |")
    return "\n".join(rows)


def markdown_call_table(
    fn: FunctionInfo,
    fn_by_key: dict[str, FunctionInfo],
    fn_by_name: dict[str, list[FunctionInfo]],
    class_by_name: dict[str, list[ClassInfo]],
) -> str:
    if not fn.calls:
        return "这个函数没有显式函数调用，主要是字段访问、表达式或常量返回。"

    rows = ["| 调用名 | 目标 | 作用与返回 |", "| --- | --- | --- |"]
    for call in fn.calls:
        targets = resolve_project_call(call, fn, fn_by_key, fn_by_name, class_by_name)
        if targets:
            links: list[str] = []
            for target in targets[:6]:
                kind = "类" if isinstance(target, ClassInfo) else "函数"
                links.append(f"{md_link(f'{target.module}.{target.qualname}', target.anchor)} ({kind})")
            if len(targets) > 6:
                links.append(f"另有 {len(targets) - 6} 个同名候选")
            explanation = "项目内调用；点击链接可跳到对应函数或类说明。"
            if len(targets) > 1:
                explanation = "项目内同名候选；实际调用由对象类型或导入绑定决定，表中列出可跳转的候选说明。"
            rows.append(
                f"| {md_inline_code(call)} | {'<br>'.join(links)} | {md_table_cell(explanation)} |"
            )
        else:
            rows.append(
                f"| {md_inline_code(call)} | 库函数或对象方法 | {md_table_cell(external_call_explanation(call))} |"
            )
    return "\n".join(rows)


def markdown_function_section(
    fn: FunctionInfo,
    fn_by_key: dict[str, FunctionInfo],
    fn_by_name: dict[str, list[FunctionInfo]],
    class_by_name: dict[str, list[ClassInfo]],
    reverse_calls: dict[str, list[FunctionInfo]],
) -> str:
    callers = reverse_calls.get(f"{fn.module}:{fn.qualname}", [])
    if callers:
        caller_links = "、".join(
            md_link(f"{caller.module}.{caller.qualname}", caller.anchor) for caller in callers[:12]
        )
        if len(callers) > 12:
            caller_links += f"、另有 {len(callers) - 12} 个调用方"
    else:
        caller_links = "未发现项目内其他函数直接调用；可能由命令行入口、类实例化或外部调用触发。"

    return "\n\n".join(
        [
            f'<a id="{fn.anchor}"></a>',
            f"### {fn.qualname}",
            f"文件：`{rel(fn.file)}:{fn.lineno}-{fn.end_lineno}`",
            "**签名**",
            md_fence(fn.signature, "python"),
            f"**功能**\n\n{md_text(explain_function(fn))}",
            "**参数**",
            markdown_parameter_table(fn),
            f"**返回值**\n\n{explain_return_markdown(fn)}",
            "**调用的函数**",
            markdown_call_table(fn, fn_by_key, fn_by_name, class_by_name),
            f"**被谁调用**\n\n{caller_links}",
            "**完整源码**",
            md_fence(fn.source, "python"),
            "[回到顶部](#top)",
        ]
    )


def markdown_class_example(cls: ClassInfo) -> str:
    key = f"{cls.module}:{cls.qualname}"
    examples = {
        "boardroom_sim.models:BoardCase": "例：`case_id='9244942_963111474T'` 表示一个交易案例；`deal_size_usd_m=12.5` 表示融资金额；`l5_culture={'trust': 0.7, ...}` 会进入流程控制和 prompt。",
        "boardroom_sim.models:RoleDecision": "例：Founder CEO 可以给出 `financing_intent='yes'`、`deal_size_usd_m=15`、`rationale=['cash runway is short']`，后续讨论会更新这些字段。",
        "boardroom_sim.models:TermSheetProposal": "例：最终输出 `deal_completion_view='completed'`、`deal_type='priced_round'`、`estimated_dilution_pct=18.0`，用于和真实标签计算误差。",
        "boardroom_sim.config:BoardProcessConfig": "例：`board_archetype='value_creating'` 会让会议更重视证据、挑战和替代方案；`discussion_rounds=3` 控制讨论轮数。",
        "boardroom_sim.llm:LLMConfig": "例：`base_url='https://api.openai.com/v1/chat/completions'`、`model='gpt-4.1-mini'`、`timeout_seconds=120` 控制请求目标和超时。",
        "boardroom_sim.agents:BoardAgent": "例：一个 `BoardAgent(role_policy=founder_ceo, ...)` 只看到创始人角色允许看到的字段，并按创始人的目标发言。",
        "boardroom_sim.process:BoardProcessController": "例：同样四个角色，在 `barbarian` 和 `clan` archetype 下会得到不同发言顺序、不同主席压力和不同 L5 行为指令。",
    }
    text = examples.get(key)
    return f"\n\n**例子**：{text}" if text else ""


def markdown_class_section(cls: ClassInfo, method_map: dict[str, list[FunctionInfo]]) -> str:
    key = f"{cls.module}:{cls.qualname}"
    purpose = CLASS_PURPOSES.get(key) or "项目类。它把相关数据和行为组织在一起，字段与方法如下。"
    bases = ", ".join(cls.bases) if cls.bases else "无显式父类"
    fields = "\n".join(f"- `{field}`" for field in cls.fields) or "- 未从源码中识别到固定字段。"
    methods = "\n".join(
        f"- {md_link(method.name, method.anchor)}" for method in method_map.get(key, [])
    ) or "- 无方法。"
    return "\n\n".join(
        [
            f'<a id="{cls.anchor}"></a>',
            f"### {cls.qualname}",
            f"文件：`{rel(cls.file)}:{cls.lineno}-{cls.end_lineno}`",
            purpose,
            f"**父类/基类**：{bases}",
            "**字段/属性**",
            fields,
            "**方法**",
            methods + markdown_class_example(cls),
            "[回到顶部](#top)",
        ]
    )


def markdown_file_index(
    source_files: list[Path],
    functions_by_file: dict[Path, list[FunctionInfo]],
    classes_by_file: dict[Path, list[ClassInfo]],
) -> str:
    rows = ["| 文件 | 函数 | 类 | 作用 |", "| --- | ---: | ---: | --- |"]
    for path in source_files:
        anchor = safe_anchor("module", rel(path)) if path.suffix == ".py" else safe_anchor("file", rel(path))
        summary = module_summary(path) if path.suffix == ".py" else explain_text_file(path)
        rows.append(
            f"| {md_link(rel(path), anchor)} | {len(functions_by_file.get(path, []))} | {len(classes_by_file.get(path, []))} | {md_table_cell(summary)} |"
        )
    return "\n".join(rows)


def markdown_workflow(functions: list[FunctionInfo]) -> str:
    fn_by_key = {f"{fn.module}:{fn.qualname}": fn for fn in functions}

    def link(key: str, label: str) -> str:
        fn = fn_by_key.get(key)
        return md_link(label, fn.anchor) if fn else label

    steps = [
        (
            "读取配置与输入",
            f"{link('run_batch_experiments:main', 'run_batch_experiments.main')} 调用 {link('boardroom_sim.config:load_experiment_config', 'load_experiment_config')} 读取 TOML，再用 {link('boardroom_sim.pitchbook:build_cases_from_pitchbook', 'build_cases_from_pitchbook')} 从 Excel 构造 BoardCase。",
        ),
        (
            "构造角色和流程",
            f"配置中的角色 TOML 进入 RolePolicy；{link('boardroom_sim.process:BoardProcessController.prompt_context', 'BoardProcessController.prompt_context')} 每轮生成可见历史、会议阶段和 L5 文化指令。",
        ),
        (
            "初始预测",
            f"{link('boardroom_sim.agents:BoardAgent.evaluate', 'BoardAgent.evaluate')} 为每个角色生成初始 RoleDecision。",
        ),
        (
            "多轮讨论",
            f"{link('boardroom_sim.simulator:BoardroomSimulator._run_bargaining_round', 'BoardroomSimulator._run_bargaining_round')} 按发言顺序调用 {link('boardroom_sim.agents:BoardAgent.bargaining_step', 'BoardAgent.bargaining_step')}，并记录会议行为字段。",
        ),
        (
            "最终聚合",
            f"{link('boardroom_sim.simulator:BoardroomSimulator._build_proposal', 'BoardroomSimulator._build_proposal')} 把角色最终判断合成为 TermSheetProposal。",
        ),
        (
            "评估与报告",
            "批量脚本写出 results/traces 后，再调用评估和分析脚本生成 case_metrics、aggregate_metrics、debate_accuracy_report 等文件。",
        ),
    ]
    lines = ['<a id="workflow"></a>', "## 函数调用主线"]
    for i, (title, body) in enumerate(steps, start=1):
        lines.append(f"{i}. **{title}**：{body}")
    return "\n\n".join(lines)


def markdown_progress() -> str:
    return """<a id="progress"></a>
## 当前实验进度

当前代码已经从“硬编码 prompt 的简单模拟”改造成更接近可扩展框架的版本：角色、prompt、可见字段、讨论轮次、发言顺序、board archetype 和 L5 文化层都可以通过配置或模板文件调整。

- **框架化**：配置集中在 `configs/boardroom_default.toml`，角色放在 `policies/roles/*.toml`，prompt 放在 `prompts/*.md`。
- **过程变量**：`BoardProcessController` 负责发言顺序、可见历史、会议阶段和过程指令。
- **L5 文化层**：`culture.py` 把文化分数解释为行为控制，再进入每轮 prompt。
- **数据升级**：默认输入指向更完整的 PitchBook/Revelio Excel 文件，可从字段字典继续挑选更多变量。
- **可恢复运行**：批量脚本支持 checkpoint，Ctrl+C 后可以通过 resume 逻辑继续已完成 case 后面的工作。"""


def markdown_text_file_section(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    return "\n\n".join(
        [
            f'<a id="{safe_anchor("file", rel(path))}"></a>',
            f"## {rel(path)}",
            explain_text_file(path),
            md_fence(text, language_for(path)),
            "[回到顶部](#top)",
        ]
    )


def build_markdown() -> str:
    source_files = collect_source_files()
    functions, classes, _ = parse_python_files(source_files)
    fn_by_key, fn_by_name, _, class_by_name = build_indices(functions, classes)
    reverse_calls = reverse_call_index(functions, fn_by_key, fn_by_name, class_by_name)
    method_map = methods_by_class(functions)

    functions_by_file: dict[Path, list[FunctionInfo]] = {}
    classes_by_file: dict[Path, list[ClassInfo]] = {}
    for fn in functions:
        functions_by_file.setdefault(fn.file, []).append(fn)
    for cls in classes:
        classes_by_file.setdefault(cls.file, []).append(cls)

    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    parts: list[str] = [
        '<a id="top"></a>',
        "# Boardroom Sim MVP 完整代码教程",
        f"生成时间：{generated_at}",
        "本版为 Markdown 阅读版，按函数组织内容。每个函数包含功能、参数、返回值、调用关系和完整源码；项目内调用可跳转，库函数会解释作用和返回值。",
        "## 统计",
        f"- 纳入文件：{len(source_files)}",
        f"- 函数/方法：{len(functions)}",
        f"- 类：{len(classes)}",
        f"- 配置/Prompt 文件：{sum(1 for p in source_files if p.suffix != '.py')}",
        "## 文件索引",
        markdown_file_index(source_files, functions_by_file, classes_by_file),
        markdown_workflow(functions),
        markdown_progress(),
        '<a id="classes"></a>',
        "## 类与参数",
        "这里集中解释项目中的类。类方法会链接到后面的逐函数讲解，字段用于理解每个对象携带的实验变量。",
    ]
    parts.extend(markdown_class_section(cls, method_map) for cls in classes)
    parts.extend(
        [
            '<a id="python-files"></a>',
            "## 逐函数讲解",
            "以下按文件排列。每个函数都保留完整源码块；重点解释函数功能、输入输出和它调用了哪些内部/外部函数。",
        ]
    )

    for path in [p for p in source_files if p.suffix == ".py"]:
        class_links = "、".join(
            md_link(cls.qualname, cls.anchor) for cls in classes_by_file.get(path, [])
        ) or "无类定义"
        parts.extend(
            [
                f'<a id="{safe_anchor("module", rel(path))}"></a>',
                f"## {rel(path)}",
                module_summary(path),
                f"**类**：{class_links}",
            ]
        )
        parts.extend(
            markdown_function_section(fn, fn_by_key, fn_by_name, class_by_name, reverse_calls)
            for fn in functions_by_file.get(path, [])
        )

    parts.extend(
        [
            '<a id="text-files"></a>',
            "## 配置与 Prompt 文件",
            "这些文件不是 Python 函数，但它们决定实验变量、角色策略和 LLM 行为。教程保留全文，方便直接修改。",
        ]
    )
    parts.extend(markdown_text_file_section(path) for path in source_files if path.suffix != ".py")
    return "\n\n".join(parts) + "\n"


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(build_html(), encoding="utf-8")
    OUT_MD.write_text(build_markdown(), encoding="utf-8")
    safe_out = str(OUT).encode("gbk", errors="backslashreplace").decode("gbk")
    safe_out_md = str(OUT_MD).encode("gbk", errors="backslashreplace").decode("gbk")
    print(f"Wrote {safe_out}")
    print(f"Wrote {safe_out_md}")


if __name__ == "__main__":
    main()
