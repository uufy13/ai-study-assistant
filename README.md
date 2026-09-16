# AI Study Assistant

[![Test](https://github.com/uufy13/ai-study-assistant/actions/workflows/test.yml/badge.svg)](https://github.com/uufy13/ai-study-assistant/actions/workflows/test.yml)
[![Security](https://github.com/uufy13/ai-study-assistant/actions/workflows/security.yml/badge.svg)](https://github.com/uufy13/ai-study-assistant/actions/workflows/security.yml)
[![Release](https://img.shields.io/github/v/release/uufy13/ai-study-assistant)](https://github.com/uufy13/ai-study-assistant/releases)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **本地优先的 AI 学习资料整理工具 / A local-first AI study assistant for turning study materials into structured Markdown notes.**

## 中文

> 本节为 v0.2.0 的 GitHub README，基于当前已发布版本整理。

### 项目定位

**AI Study Assistant** 是一个面向学生和知识工作者的本地 AI 学习助手。它将 Markdown、TXT、DOCX、PDF、PPTX 学习资料统一解析为 `Document`，再交给现有 LLM Pipeline 生成结构化 Markdown 学习笔记。

### v0.2.0 已完成

- 支持 Markdown / TXT / DOCX / PDF / PPTX
- 基于 `ParserRegistry` 自动按扩展名路由
- DOCX：标题、段落、列表、表格、外部超链接、文档属性
- PDF：文本层、多页边界、表格、多栏文本排序、文档属性
- PPTX：Slide、标题、文本、列表、表格、演讲者备注、文档属性
- Parser → Document → Pipeline → StudyNote → Storage 的统一数据流
- 130 个测试全部通过
- gitleaks + pre-commit + GitHub Actions + Dependabot 安全基础设施
- 已正式发布 `v0.2.0`

### 支持格式

| 格式 | 扩展名 | 状态 |
|---|---|---|
| Markdown | `.md`, `.markdown` | ✅ |
| TXT | `.txt` | ✅ |
| DOCX | `.docx` | ✅ |
| PDF | `.pdf` | ✅ |
| PPTX | `.pptx` | ✅ |

`parse_file()` 根据扩展名自动选择解析器，并支持大小写不敏感路由。

### 支持范围与边界

| 格式 | 当前支持 | 当前限制 |
|---|---|---|
| DOCX | 标题、段落、列表、表格、外部超链接、文档属性 | 图片、页眉页脚、SmartArt、OLE 等不解析 |
| PDF | 文本层、分页边界、多栏排序、表格、文档属性 | 扫描 PDF 不做 OCR，图片不提取 |
| PPTX | Slide、标题、文本、列表、表格、演讲者备注、文档属性 | SmartArt、图表、动画、视频、图片不解析 |

v0.2.0 不包含：

- PDF OCR
- 图片理解
- 图片二进制提取
- SmartArt 解析
- 动画 / 视频解析
- 加密文档解密
- RAG
- Web UI
- 数据库

### 架构

```text
学习资料
   │
   ▼
parse_file()
   │
   ▼
ParserRegistry
   ├── MarkdownParser
   ├── TextParser
   ├── DocxParser
   ├── PdfParser
   └── PptxParser
   │
   ▼
Document
   │
   ▼
StudyPipeline
   │
   ▼
LLM
   │
   ▼
StudyNote
   │
   ▼
Markdown 输出
```

Parser 负责读取和标准化资料，Pipeline 负责生成学习笔记。v0.2.0 保持两者边界分离，核心 Pipeline / Storage / LLM 不需要感知具体输入格式。

### 快速开始

项目使用 [uv](https://docs.astral.sh/uv/) 管理 Python 环境和依赖。

```bash
git clone git@github.com:uufy13/ai-study-assistant.git
cd ai-study-assistant
uv sync
```

**PowerShell：**

```powershell
copy config.example.yaml config.yaml
copy .env.example .env
```

在 `.env` 中填写 API Key：

```env
DEEPSEEK_API_KEY=your_key
```

在 `config.yaml` 中选择 provider：

```yaml
provider: deepseek
```

运行：

```bash
uv run ai-study-assistant input.md -o notes/
```

### CLI

```text
ai-study-assistant <input> [-o OUTPUT] [--provider NAME] [--config PATH]
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `input` | `.md` / `.markdown` / `.txt` / `.docx` / `.pdf` / `.pptx` | — |
| `-o, --output` | Markdown 输出目录 | `./output` |
| `--provider` | 指定 AI 服务 | 配置文件 |
| `--config` | 指定配置文件 | `config.yaml` |

查看帮助：

```bash
uv run ai-study-assistant --help
```

### Demo

仓库包含虚构、脱敏的 Demo 文件：

```bash
uv run ai-study-assistant demo/input-machine-learning.md -o notes/
uv run ai-study-assistant demo/input-example.docx -o notes/
uv run ai-study-assistant demo/input-example.pdf -o notes/
uv run ai-study-assistant demo/input-example.pptx -o notes/
```

详见 [`demo/README.md`](demo/README.md)。

不要将真实学习资料、`.env`、`config.yaml` 或包含私人内容的输出文件提交到公开仓库。

### 多模型与 OpenAI Compatible API

当前配置体系支持：

- OpenAI
- DeepSeek
- Kimi
- Qwen
- Ollama

项目使用统一的 LLM 客户端抽象。OpenAI Compatible API 的 `base_url`、模型名和 API Key 环境变量通过配置管理，业务层不绑定具体厂商。

### 安全

公开仓库采用多层防误提交机制：

```text
.gitignore
    ↓
gitleaks + pre-commit
    ↓
GitHub Actions
    ↓
GitHub Secret Scanning / Push Protection
```

| 机制 | 作用 |
|---|---|
| `.gitignore` | 忽略 `.env`、`config.yaml`、私钥/证书、真实 DOCX/PDF/PPTX、`notes/`、`output/` 等 |
| `gitleaks` | 本地与 CI Secret 扫描 |
| `pre-commit` | `git commit` 时自动扫描 staged 文件 |
| GitHub Actions | `test.yml`：pytest + ruff；`security.yml`：gitleaks |
| Dependabot | 每周检查 uv 依赖更新 |
| Secret Scanning / Push Protection | GitHub 平台额外防线；请在仓库设置中确认 |

本地开发安全初始化：

```bash
# 先安装 gitleaks：https://github.com/gitleaks/gitleaks
uv sync
uv run pre-commit install
```

手动扫描：

```bash
gitleaks detect --config .gitleaks.toml --exit-code 1
```

> `.gitignore` 和 Secret scanning 主要用于降低凭据与文件误提交风险；它们不能识别所有语义层面的私人信息。

### 开发

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pre-commit run --all-files
```

当前 v0.2.0：

```text
pytest       130/130 passed
ruff         clean
gitleaks     clean
GitHub CI    passed
```

### 项目结构

```text
src/ai_study_assistant/
├── config/      配置管理
├── llm/         LLM 客户端
├── parsers/     Markdown / TXT / DOCX / PDF / PPTX 解析
├── pipeline/    学习笔记生成
├── storage/     Markdown 输出
└── cli.py       CLI 入口
```

### 版本历史

#### v0.2.0

- DOCX / PDF / PPTX 支持
- ParserRegistry 自动路由
- Parser / Registry / Pipeline / CLI 集成与 E2E 测试
- dotenv 优先级与测试隔离修复
- gitleaks / pre-commit / GitHub Actions / Dependabot
- 正式 GitHub Release

#### v0.1.0

- Markdown / TXT 支持
- CLI
- 多模型接入
- 自动生成学习笔记

### 后续路线

- PDF OCR
- 图片理解
- 批量处理
- Web UI
- 知识库

具体顺序根据实际需求和架构稳定性确定。

### License

MIT License

---

## English

**AI Study Assistant** is a local-first AI study assistant for students and knowledge workers. It accepts Markdown, TXT, DOCX, PDF, and PPTX study materials, routes them through a common parser registry, and generates structured Markdown study notes through the LLM pipeline.

### v0.2.0

- Markdown / TXT / DOCX / PDF / PPTX support
- Automatic extension-based routing with `ParserRegistry`
- DOCX headings, paragraphs, lists, tables, external hyperlinks, and document properties
- PDF text extraction, page boundaries, table extraction, multi-column ordering, and document properties
- PPTX slides, titles, text, lists, tables, speaker notes, and document properties
- Unified `Parser → Document → Pipeline → StudyNote → Storage` flow
- 130 tests passing
- gitleaks + pre-commit + GitHub Actions + Dependabot security infrastructure
- Released as `v0.2.0`

### Supported formats

| Format | Extensions | Status |
|---|---|---|
| Markdown | `.md`, `.markdown` | ✅ |
| TXT | `.txt` | ✅ |
| DOCX | `.docx` | ✅ |
| PDF | `.pdf` | ✅ |
| PPTX | `.pptx` | ✅ |

`parse_file()` automatically selects the parser from the file extension and supports case-insensitive routing.

### Support and limitations

| Format | Supported | Current limitations |
|---|---|---|
| DOCX | Headings, paragraphs, lists, tables, external hyperlinks, document properties | Images, headers/footers, SmartArt, OLE, etc. are not parsed |
| PDF | Text layer, page boundaries, multi-column ordering, tables, document properties | No OCR for scanned PDFs; images are not extracted |
| PPTX | Slides, titles, text, lists, tables, speaker notes, document properties | SmartArt, charts, animation, video, and images are not parsed |

v0.2.0 does not include PDF OCR, image understanding, image extraction, SmartArt parsing, animation/video parsing, encrypted-document decryption, RAG, Web UI, or database integration.

### Architecture

```text
Study material
      │
      ▼
  parse_file()
      │
      ▼
 ParserRegistry
      ├── MarkdownParser
      ├── TextParser
      ├── DocxParser
      ├── PdfParser
      └── PptxParser
      │
      ▼
   Document
      │
      ▼
 StudyPipeline
      │
      ▼
      LLM
      │
      ▼
  StudyNote
      │
      ▼
 Markdown output
```

### Quick start

```bash
git clone git@github.com:uufy13/ai-study-assistant.git
cd ai-study-assistant
uv sync
```

**PowerShell:**

```powershell
copy config.example.yaml config.yaml
copy .env.example .env
```

Set an API key in `.env`:

```env
DEEPSEEK_API_KEY=your_key
```

Choose a provider in `config.yaml`:

```yaml
provider: deepseek
```

Run:

```bash
uv run ai-study-assistant input.md -o notes/
```

### CLI

```text
ai-study-assistant <input> [-o OUTPUT] [--provider NAME] [--config PATH]
```

| Argument | Description | Default |
|---|---|---|
| `input` | `.md` / `.markdown` / `.txt` / `.docx` / `.pdf` / `.pptx` | — |
| `-o, --output` | Markdown output directory | `./output` |
| `--provider` | AI provider | Configured provider |
| `--config` | Configuration file | `config.yaml` |

```bash
uv run ai-study-assistant --help
```

### Demo

```bash
uv run ai-study-assistant demo/input-machine-learning.md -o notes/
uv run ai-study-assistant demo/input-example.docx -o notes/
uv run ai-study-assistant demo/input-example.pdf -o notes/
uv run ai-study-assistant demo/input-example.pptx -o notes/
```

See [`demo/README.md`](demo/README.md).

Do not commit real study materials, `.env`, `config.yaml`, or outputs containing private information.

### Multi-model and OpenAI-compatible APIs

The current configuration supports:

- OpenAI
- DeepSeek
- Kimi
- Qwen
- Ollama

The project uses a unified LLM client abstraction. OpenAI-compatible API details such as `base_url`, model name, and API-key environment variables are handled through configuration.

### Security

The public repository uses multiple layers to reduce accidental data exposure:

```text
.gitignore
    ↓
gitleaks + pre-commit
    ↓
GitHub Actions
    ↓
GitHub Secret Scanning / Push Protection
```

| Mechanism | Purpose |
|---|---|
| `.gitignore` | Ignores `.env`, `config.yaml`, keys/certificates, real DOCX/PDF/PPTX, `notes/`, `output/`, etc. |
| `gitleaks` | Local and CI Secret scanning |
| `pre-commit` | Scans staged files during `git commit` |
| GitHub Actions | `test.yml`: pytest + ruff; `security.yml`: gitleaks |
| Dependabot | Weekly uv dependency update checks |
| Secret Scanning / Push Protection | Additional GitHub-side protection; verify in repository settings |

Local security setup:

```bash
# Install gitleaks: https://github.com/gitleaks/gitleaks
uv sync
uv run pre-commit install
```

Manual scan:

```bash
gitleaks detect --config .gitleaks.toml --exit-code 1
```

> `.gitignore` and Secret scanning reduce accidental exposure but cannot identify every form of private information.

### Development

```bash
uv sync
uv run pytest
uv run ruff check .
uv run pre-commit run --all-files
```

Current v0.2.0 verification:

```text
pytest       130/130 passed
ruff         clean
gitleaks     clean
GitHub CI    passed
```

### Project structure

```text
src/ai_study_assistant/
├── config/      Configuration
├── llm/         LLM client
├── parsers/     Markdown / TXT / DOCX / PDF / PPTX parsers
├── pipeline/    Study-note generation
├── storage/     Markdown output
└── cli.py       CLI entry point
```

### Release history

#### v0.2.0

- DOCX / PDF / PPTX support
- Automatic ParserRegistry routing
- Parser / Registry / Pipeline / CLI integration and E2E coverage
- dotenv precedence and test-isolation fix
- gitleaks / pre-commit / GitHub Actions / Dependabot
- Official GitHub Release

#### v0.1.0

- Markdown / TXT support
- CLI
- Multi-model integration
- Automatic study-note generation

### Roadmap

Potential future work includes:

- PDF OCR
- Image understanding
- Batch processing
- Web UI
- Knowledge base

The order will follow actual requirements and architecture stability.

### License

MIT License
