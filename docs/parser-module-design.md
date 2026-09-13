# parser 模块设计文档

> 所属阶段：Phase 1（MVP 第三层）
> 状态：已确认，待实现
> 上游依赖：无（只依赖 pydantic + pathlib）
> 下游消费方：pipeline

## 1. 需求分析

| 编号 | 需求 | 优先级 |
|---|---|---|
| FR1 | 读取文件并产出统一的 `Document` 结构 | P0 |
| FR2 | 支持 Markdown（.md/.markdown）与 TXT（.txt） | P0 |
| FR3 | 按扩展名自动路由到对应 parser，调用方不关心具体格式 | P0 |
| FR4 | 注册表机制，未来新增格式无需改 core | P0 |
| FR5 | 明确错误处理（文件不存在 / 未知格式 / 编码错误） | P0 |
| FR6 | 测试零外部依赖，纯文件操作 | P0 |

非功能需求：单一职责（只读文件→结构化文本，不调 LLM、不分块、不生成 prompt）、无 pipeline 依赖、可扩展（DOCX/PDF/PPTX 通过注册表热插拔）。

## 2. 输入输出数据结构设计

输入：`Path`（文件路径），parser 内部完成读取。

输出：统一的 `Document`（pydantic 模型，与 config/llm 一致）：

```python
class Document(BaseModel):
    source: Path                  # 源文件路径（供笔记引用/溯源）
    format: str                   # 格式名（registry 的 key，如 "markdown"/"text"）
    content: str                  # 纯文本正文（pipeline 分块 + LLM 输入）
    metadata: dict[str, Any] = Field(default_factory=dict)  # 预留：DOCX/PDF 的标题/作者/页数
```

设计决策：
- MVP 的 `content` 是扁平纯文本——MVP 数据流只需要文本，Markdown 结构暂不解析。未来需要再加 `elements` 字段，现在不加。
- `format` 用自由 str（registry key）而非 Literal——格式集是开放的，硬编码 Literal 违背扩展性。
- `metadata` 空 dict 预留，DOCX/PDF 落地时填「标题/作者/页数」，Document 结构零改动。

## 3. parser registry 设计

Parser 协议（可 mock 的接缝）：

```python
class Parser(Protocol):
    def parse(self, path: Path) -> Document: ...
```

注册表（「格式名 + 扩展名列表」两级映射）：

```python
class ParserRegistry:
    def register(self, name: str, parser: Parser, extensions: Iterable[str]) -> None: ...
    def parse(self, path: Path) -> Document: ...      # 按扩展名路由
    def get(self, name: str) -> Parser: ...            # 按格式名取 parser
    def supported_extensions(self) -> set[str]: ...     # 对外暴露能力
```

设计决策：用「格式名 → (parser, 扩展名列表)」而非「扩展名 → parser」裸 dict。理由：多扩展名归一（.md/.markdown）、语义化格式名（错误信息用 "markdown" 而非 ".md"）、扩展名匹配统一小写化。

便捷入口（pipeline 只调用这一个函数）：

```python
default_registry = ParserRegistry()   # 模块加载时注册内置 markdown/text
def parse_file(path) -> Document:     # = default_registry.parse(path)
```

## 4. Markdown/TXT MVP 设计

两者 MVP 都是「读 UTF-8 文本 + 返回 Document」，仅 format 与接受的扩展名不同：

| parser | 扩展名 | format | 处理 |
|---|---|---|---|
| MarkdownParser | .md / .markdown | "markdown" | 读取原文，不解析结构 |
| TextParser | .txt | "text" | 读取原文 |

编码处理：统一用 `encoding="utf-8-sig"` 读取——兼容「无 BOM 的 UTF-8」与「带 BOM 的 UTF-8」。其它编码抛 `DecodeError`，不做静默替换（会污染 LLM 输入）。

为何分开两个 parser 而非合并：语义清晰，且未来会分化（Markdown 将解析标题结构，TXT 不会）。

## 5. DOCX/PDF/PPTX 未来扩展方案

注册表机制天然支持，新增格式三步不动 core：

```python
from .docx import DocxParser
default_registry.register("docx", DocxParser(), {".docx"})
```

三个预留扩展点：
1. 注册表热插拔：新增 docx.py / pdf.py / pptx.py，各实现 Parser 协议。
2. Document.metadata：DOCX/PDF 解析时填「标题/作者/页数」。
3. 可选依赖分组：pyproject.toml 加 `[dependency-groups] docx/pdf/pptx`，按需 `uv sync --group docx` 安装。MVP 不引入这些重量级依赖。

## 6. 文件结构设计

```
parsers/
├── __init__.py      # 导出 + 组装 default_registry + parse_file 便捷入口
├── document.py      # Document 模型
├── registry.py      # Parser 协议 + ParserRegistry（纯核心，不含内置实例）
├── markdown.py      # MarkdownParser
├── text.py          # TextParser
└── errors.py        # ParserError 异常层次
```

职责边界：registry.py 只定义协议与注册表（不含内置 parser），内置 parser 的注册在 __init__.py 组装——保证「每个格式一个文件」的对称性（未来 docx.py 同理），也避免 core 与具体格式耦合。

错误层次（errors.py）：

```
ParserError (base)
├── UnknownFormatError    # 扩展名未注册
├── FileReadError         # 文件不存在 / 不可读
└── DecodeError           # 编码错误（非 UTF-8）
```

## 7. 测试方案

全部用 tmp_path 创建临时文件，零网络、零 LLM、零外部依赖。

| # | 用例 | 验证点 |
|---|---|---|
| 1 | 解析 .md | format=="markdown"、content==原文 |
| 2 | 解析 .txt | format=="text"、content==原文 |
| 3 | .markdown 扩展名 | 路由到 markdown parser |
| 4 | 大小写不敏感 | .MD / .Txt 命中 |
| 5 | 未知扩展名 | → UnknownFormatError |
| 6 | 文件不存在 | → FileReadError |
| 7 | UTF-8 BOM 文件 | 正确去 BOM |
| 8 | 非 UTF-8 编码 | → DecodeError |
| 9 | registry 多扩展名 | .md/.markdown 指向同一 parser |
| 10 | 自定义 parser 注册 | 验证扩展性（新增格式无需改 core） |
| 11 | parse_file 便捷函数 | 端到端返回 Document |
| 12 | 空文件 | content==""，不报错 |

## 8. 决策总结

| 决策 | 选择 | 理由 |
|---|---|---|
| 输出类型 | pydantic Document（扁平 content） | 与 config/llm 一致，够用，预留 metadata |
| 路由机制 | 格式名 → (parser, 扩展名列表) | 多扩展名归一 + 语义化错误 |
| 编码 | 统一 utf-8-sig，错误即抛 | 兼容 BOM，不静默替换 |
| 扩展性 | 注册表热插拔 + 可选依赖分组 | 新格式不动 core，MVP 不背重量级依赖 |
| Markdown 处理 | MVP 仅读原文，不解析结构 | 数据流不需要结构，未来加 elements |
| 依赖 | 仅 pydantic + pathlib | 不依赖 pipeline/llm |
