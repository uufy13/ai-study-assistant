# storage 模块设计文档

> 所属阶段：Phase 1（MVP 第五层，持久化层）
> 状态：已确认，待实现
> 上游依赖：pipeline（StudyNote）
> 下游消费方：CLI

## 1. 需求分析

输入：`StudyNote`（pipeline 产出，含 source/title/sections 与 to_markdown()）+ `output_dir`（写入目标目录）。

输出：落盘后的 Markdown 文件 `Path`（返回给调用方）。

核心功能：

| 编号 | 功能 |
|---|---|
| FR1 | 把 StudyNote 渲染为 Markdown 文本（复用 to_markdown()） |
| FR2 | 确定输出路径（output_dir / {title}.md） |
| FR3 | 自动创建输出目录（不存在时） |
| FR4 | 写入文件并返回路径 |

非功能需求：单一职责（只持久化）、可测试（纯文件操作）、可预测（输出路径确定性）。

不负责：不读文件（parser）、不生成笔记内容（pipeline）、不调 LLM、不编排。

## 2. 数据结构设计

如何消费 StudyNote：storage 只读两个字段 + 一个方法：
- note.title → 文件命名；
- note.to_markdown() → 文件内容（渲染已在 pipeline 的 StudyNote 上实现，storage 不重复渲染）。

是否需要额外 OutputConfig：不需要。storage 是最薄模块，唯一可变项是 output_dir；overwrite/filename_template 是未来扩展，MVP 用 write_text 默认覆盖（YAGNI）。

文件路径管理：output_dir 由调用方必传，storage 不内置默认目录（无状态可预测）；文件名 = f"{note.title}.md"。当前 title 来自 source.stem（文件系统安全），无需 sanitize；未来 title 由 LLM 生成时再加 sanitize（预留）。

## 3. Markdown 输出设计

```
StudyNote ──► to_markdown() ──► Markdown 字符串 ──► write_text ──► 文件
```

- 标题格式：`# {title}`（H1，由 to_markdown() 生成）。
- section 合并方式：`# title` + 各 section.content，用 `\n\n` 连接（由 to_markdown() 生成）。
- 文件命名规则：`{title}.md`。
- 输出目录规则：调用方指定；不存在则 mkdir(parents=True, exist_ok=True) 自动创建。

关键设计点：渲染逻辑归 pipeline 的 StudyNote.to_markdown()，storage 只负责「字符串 → 文件」。

## 4. 文件结构设计

```
storage/
├── __init__.py      # save() 便捷函数 + 导出
├── writer.py        # MarkdownWriter 类（路径管理 + 写文件）
└── errors.py        # StorageError 层次
```

为何 3 文件（无 markdown.py）：渲染已由 StudyNote.to_markdown() 承担，storage 设独立 markdown.py 会成为「一行 return note.to_markdown()」的冗余层，模糊分层边界。未来需 frontmatter/目录等增强渲染时再扩展。

接口：

```python
class MarkdownWriter:
    def __init__(self, output_dir: Path): ...
    def save(self, note: StudyNote) -> Path: ...   # 渲染→确定路径→mkdir→写→返回 Path

def save(note: StudyNote, output_dir: Path) -> Path: ...   # 便捷函数
```

## 5. 错误处理设计

```
StorageError (base)
├── OutputDirectoryError    # 输出目录创建失败（权限/路径非法）
└── WriteError              # 文件写入失败（磁盘满/权限/只读）
```

映射：mkdir 抛 OSError/PermissionError → OutputDirectoryError；write_text 抛 OSError/PermissionError → WriteError。均用 from exc 保留原始异常。

## 6. 测试方案

全部用 tmp_path 临时目录，零 LLM、零网络、零真实文件冲突。

| # | 用例 | 验证点 |
|---|---|---|
| 1 | save 返回路径 | 返回 output_dir / "{title}.md" |
| 2 | 文件内容正确 | 读回文件 == note.to_markdown() |
| 3 | 目录不存在自动创建 | 首次 save 到不存在的 output_dir，目录被创建 |
| 4 | 目录已存在正常写入 | exist_ok 不报错 |
| 5 | 覆盖已存在文件 | 同路径二次 save 内容被覆盖 |
| 6 | 空 sections | 只写 # title |
| 7 | 目录创建失败 | monkeypatch mkdir 抛 OSError → OutputDirectoryError |
| 8 | 写入失败 | monkeypatch write_text 抛 OSError → WriteError |

## 7. 明确边界

不实现：数据库、云存储、文件同步、Web API。storage 只做本地 Markdown 落盘，输出是本地 Path，调用方决定后续动作。

## 8. 决策总结

| 决策 | 选择 | 理由 |
|---|---|---|
| 渲染归属 | 复用 StudyNote.to_markdown() | 分层清晰，不重复 pipeline 职责 |
| 配置 | 不引入 OutputConfig，仅 output_dir | YAGNI，最薄模块 |
| 命名 | {title}.md | title 当前安全，未来 sanitize 预留 |
| 目录 | 调用方指定 + 自动 mkdir | 无状态可预测 |
| 文件结构 | 3 文件（无 markdown.py） | 避免冗余渲染层 |
| 错误 | 2 具体错误 + base | 覆盖目录/写入两类失败 |
