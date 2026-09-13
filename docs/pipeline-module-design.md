# pipeline 模块设计文档

> 所属阶段：Phase 1（MVP 第四层，编排层）
> 状态：已确认，待实现
> 上游依赖：parsers（Document）、llm（LLMClient / Message）
> 下游消费方：storage / CLI

## 1. 需求分析

| 编号 | 需求 | 优先级 |
|---|---|---|
| FR1 | 编排「Document → 分块 → LLM → StudyNote」主流程 | P0 |
| FR2 | 分块策略可配置（chunk_size） | P0 |
| FR3 | Prompt 与业务逻辑分离 | P0 |
| FR4 | 通过 LLMClient 协议调用模型，可注入 mock | P0 |
| FR5 | 组装结构化 StudyNote 输出 | P0 |
| FR6 | 明确错误处理（空内容 / LLM 错误传播） | P0 |
| FR7 | 依赖 Document 抽象，天然支持未来所有格式 | P0 |

非功能需求：单一职责（只编排，不读文件/不连模型/不写盘）、依赖注入（LLMClient 由外部注入，不接触 config/openai）、可测试（FakeLLMClient，零真实调用）。

分层关系：

```
main/CLI ──► cfg.resolve() ──► create_client() ──► LLMClient
                                                      │ 注入
parse_file(path) ──► Document ──► StudyPipeline.run() ──► StudyNote ──► storage
```

## 2. 输入输出数据结构设计

输入：`Document`（parsers 产出，pipeline 不关心来源格式）。

输出：`StudyNote`（结构化笔记，storage 消费）。

内部中间产物：`Chunk`（分块单元，瞬态，不对外）。

## 3. 文档分块（chunker）设计

```python
class Chunk:
    index: int      # 序号（0 起）
    text: str       # 该片段的文本

def chunk_text(text: str, *, chunk_size: int = 2000) -> list[Chunk]: ...
```

算法（贪心段落聚合）：
1. 按 `\n\n` 分割段落；
2. 逐段累加，累加长度达到 chunk_size 即切分（在段落边界切，不截断段落）；
3. 单段超过 chunk_size 时按字符硬切（剩余继续）；
4. 文本长度 ≤ chunk_size 时返回单个 chunk。

设计决策：字符数（非 token 数，避免 tokenizer 依赖）、overlap 预留但 MVP 不实现（默认 0）、Chunk 用轻量 dataclass（内部瞬态）。

## 4. Prompt 管理设计

```python
SYSTEM_PROMPT: str = """你是一个专业的学习助手……"""

def build_messages(chunk_text: str) -> list[Message]:
    return [
        Message(role="system", content=SYSTEM_PROMPT),
        Message(role="user", content=f"请根据以下学习材料生成学习笔记：\n\n{chunk_text}"),
    ]
```

系统提示词要点：输出结构化 Markdown（标题/列表/代码块）、客观不增编、中文输出。

设计决策：Prompt 是模块级常量 + 纯函数（MVP 无需模板引擎）；未来扩展点——按科目/语言/风格换模板，改 prompts.py 即可。

## 5. LLM 调用流程设计

```python
class StudyPipeline:
    def __init__(self, client: LLMClient, *, chunk_size: int = 2000): ...
    def run(self, document: Document) -> StudyNote: ...
```

run(document) 流程：
1. 校验 content 非空（空 → EmptyContentError）；
2. chunks = chunk_text(content, chunk_size);
3. 对每个 chunk：section_content = client.generate(build_messages(chunk.text));
4. 组装 StudyNote(source, title=source.stem, sections=[...])。

设计决策：串行调用（MVP，接口预留并发）；LLM 错误直接传播（pipeline 不吞错、不包装）。

## 6. StudyNote 结构设计

```python
class NoteSection(BaseModel):
    index: int      # 对应 chunk 序号（可追溯）
    content: str    # 该 chunk 的 Markdown 笔记

class StudyNote(BaseModel):
    source: Path
    title: str
    sections: list[NoteSection]

    def to_markdown(self) -> str: ...   # 合并 sections 为完整 Markdown
```

设计决策：保留 sections 结构化（可追溯、未来生成目录/分段保存）；title MVP 用 source.stem；to_markdown() 由 storage 调用，避免冗余存合并文本。

## 7. 文件结构设计

```
pipeline/
├── __init__.py      # 导出 + run() 便捷函数
├── chunker.py       # Chunk + chunk_text()
├── prompts.py       # SYSTEM_PROMPT + build_messages()
├── notes.py         # NoteSection + StudyNote
├── runner.py        # StudyPipeline 编排器
└── errors.py        # PipelineError + EmptyContentError
```

职责边界：chunker.py / prompts.py / notes.py / errors.py 是纯逻辑；runner.py 是唯一编排处，只依赖 Document + LLMClient + 内部模块。

错误层次：

```
PipelineError (base)
└── EmptyContentError    # document.content 为空
```

（LLM 错误来自 llm 模块的 LLMError，pipeline 直接传播。）

## 8. 测试方案

全部注入 FakeLLMClient（纯 Python 实现 LLMClient 协议），零真实 LLM、零网络。

| # | 用例 | 验证点 |
|---|---|---|
| 1 | 短文本分块 | ≤ chunk_size → 1 个 chunk |
| 2 | 长文本分块 | 多个 chunk，每个 ≤ chunk_size |
| 3 | 段落边界对齐 | 切分点在 \n\n 处，不截断段落 |
| 4 | 超长单段 | 硬切且不丢内容 |
| 5 | 空文本分块 | 返回空列表 |
| 6 | run 单 chunk | LLM 调用 1 次，StudyNote 含 1 section |
| 7 | run 多 chunk | LLM 调用 N 次，sections 数 = chunk 数 |
| 8 | prompt 正确性 | fake 记录 messages，验证 system/user 内容 |
| 9 | StudyNote 组装 | source/title/sections 正确 |
| 10 | to_markdown | 合并结果正确 |
| 11 | 空 document | → EmptyContentError |
| 12 | LLM 异常传播 | fake 抛 LLMError → pipeline 原样抛出 |

## 9. 决策总结

| 决策 | 选择 | 理由 |
|---|---|---|
| 编排形态 | StudyPipeline 类 | 一次配置多次 run，易注入测试 |
| 分块 | 字符数 + 段落边界对齐 | 无 tokenizer 依赖，不截断段落 |
| overlap | 预留，MVP 不实现 | 避免 MVP 过度设计 |
| Prompt | 常量 + 纯函数 | 与业务分离，MVP 无需模板引擎 |
| LLM 调用 | 串行，错误直接传播 | 简单稳定，pipeline 不管错误策略 |
| StudyNote | 结构化 sections + to_markdown() | 可追溯，storage 消费便捷 |
| 依赖 | Document + LLMClient（注入） | 不碰 config/openai/storage |
