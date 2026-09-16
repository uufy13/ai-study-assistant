# AI Study Assistant

一个面向学生和知识工作者的本地 AI 学习助手。

将 Markdown / TXT / DOCX / PDF / PPTX 学习资料交给 AI，自动生成结构化学习笔记。

## ✨ 功能特性

-   多模型支持：OpenAI、DeepSeek、Kimi、Qwen、Ollama
-   OpenAI Compatible API，切换模型只需修改配置
-   支持 Markdown / TXT / DOCX / PDF / PPTX，按扩展名自动路由
-   自动分块、调用 LLM、生成结构化笔记
-   Markdown 文件输出
-   API Key 与数据保存在本地

## 支持格式

| 格式 | 扩展名 | 状态 |
|---|---|---|
| Markdown | `.md` / `.markdown` | ✅ |
| TXT | `.txt` | ✅ |
| DOCX | `.docx` | ✅ |
| PDF | `.pdf` | ✅ |
| PPTX | `.pptx` | ✅ |

**自动格式路由**：`parse_file()` 依据文件扩展名（不区分大小写）自动选择解析器，无需手动指定格式。

### DOCX / PDF / PPTX 支持范围

| 格式 | 支持 | 不支持 |
|---|---|---|
| DOCX | 标题、段落、项目符号/编号列表、表格、超链接文本 | 图片、页眉页脚 |
| PDF | 文本层内容（含多栏排序）、分页边界、表格 | 扫描件图片、OCR |
| PPTX | 标题占位符、文本框段落（含有序/无序列表）、分页边界、演讲者备注、表格 | SmartArt、图表、动画、视频、图片 |

### 明确限制

-   PDF OCR 暂不支持：扫描版 PDF 若无文本层，无法提取内容
-   图片理解暂不支持：图片不会被 LLM 读取
-   图片二进制不提取：DOCX / PDF / PPTX 中的图片一律跳过
-   SmartArt / 动画 / 视频等不解析
-   加密文档不解密：加密的 DOCX / PDF / PPTX 会报错退出

## 工作流程

``` text
输入资料
   ↓
Parser 文件解析（自动路由）
   ↓
Document
   ↓
Pipeline 笔记生成
   ↓
LLM
   ↓
StudyNote
   ↓
Markdown 输出
```

## 快速开始

安装：

``` bash
uv sync
```

配置：

``` powershell
copy config.example.yaml config.yaml
copy .env.example .env
```

填写 API Key：

``` env
DEEPSEEK_API_KEY=your_key
```

选择模型：

``` yaml
provider: deepseek
```

运行：

``` bash
uv run ai-study-assistant input.md -o notes/
```

## CLI

``` bash
ai-study-assistant <input> [-o OUTPUT] [--provider NAME] [--config PATH]
```

参数：

| 参数 | 说明 | 默认 |
|---|---|---|
| input | 输入文件（.md/.markdown/.txt/.docx/.pdf/.pptx） | — |
| -o, --output | 输出目录 | ./output |
| --provider | 指定 AI 服务 | 配置文件默认 |
| --config | 指定配置文件路径 | config.yaml |

## 示例（Demo）

``` bash
# Markdown 输入
uv run ai-study-assistant demo/input-machine-learning.md -o notes/

# DOCX / PDF / PPTX 输入
uv run ai-study-assistant demo/input-example.docx -o notes/
uv run ai-study-assistant demo/input-example.pdf -o notes/
uv run ai-study-assistant demo/input-example.pptx -o notes/
```

`demo/` 目录包含虚构/脱敏的示例文件，详见 `demo/README.md`。

## 项目结构

``` text
src/ai_study_assistant/

config/      配置管理
llm/         AI 客户端
parsers/     文件解析（md/txt/docx/pdf/pptx）
pipeline/    笔记生成
storage/     文件保存
cli.py       命令入口
```

## 安全

本项目默认开启多层安全防护：

| 机制 | 说明 |
|---|---|
| `.gitignore` | 排除 .env / config.yaml / 私钥 / 真实文档 / 私人资料 |
| gitleaks | `.gitleaks.toml` 规则 + 提交前/CI 全历史密钥扫描 |
| pre-commit | `.pre-commit-config.yaml`，commit 时自动运行 gitleaks |
| GitHub Actions | `test.yml`（pytest + ruff）+ `security.yml`（gitleaks 全历史） |
| Dependabot | `.github/dependabot.yml`，每周检查 uv 依赖更新 |
| Secret Scanning / Push Protection | GitHub 平台功能，建议在仓库 Settings → Code security 中启用 |

### 本地开发安全安装

``` bash
# 1. 安装 gitleaks（用于本地密钥扫描，见 https://github.com/gitleaks/gitleaks）
# 2. 安装依赖
uv sync
# 3. 安装 pre-commit hook
uv run pre-commit install
```

## 开发

测试：

``` bash
uv run pytest
```

代码检查：

``` bash
uv run ruff check .
```

质量：

-   130 tests passed
-   ruff clean
-   gitleaks clean

## Roadmap

### v0.2.0（当前）

-   Markdown / TXT / DOCX / PDF / PPTX 支持
-   自动格式路由
-   CLI
-   多模型支持
-   安全门（gitleaks / pre-commit / GitHub Actions / Dependabot）

### v0.1.0

-   Markdown / TXT 支持
-   CLI
-   多模型支持
-   自动生成学习笔记

### 后续

-   PDF OCR
-   图片理解
-   Web UI
-   批量处理
-   知识库

## License

MIT License
