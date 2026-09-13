# AI Study Assistant

本地运行的 AI 学习资料整理工具——读取 Markdown/TXT 资料，调用大语言模型，自动生成结构化学习笔记。

![Python](https://img.shields.io/badge/Python-3.11-blue)
![uv](https://img.shields.io/badge/uv-managed-9b6cff)
![License](https://img.shields.io/badge/License-MIT-green)

## 功能特性

- **厂商无关**：通过 OpenAI 兼容 API 接入，切换厂商只改配置，不改代码。
- **可插拔解析器**：按扩展名分发，已支持 Markdown/TXT，DOCX/PDF/PPTX 预留接口。
- **分层管线**：`解析 → 分段 → LLM 调用 → 结构化输出 → 落盘`，各层解耦、可独立测试。
- **CLI 一条命令**：`ai-study-assistant input.md` 即可产出笔记。

## 快速开始

### 环境要求

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)

### 安装

```bash
uv sync
```

### 配置

1. 复制配置模板：`cp config.example.yaml config.yaml`（Windows 用 `copy`）
2. 复制环境变量模板：`cp .env.example .env`，填入你的 API Key
3. （可选）修改 `config.yaml` 的 `provider` 切换厂商

### 运行

```bash
uv run ai-study-assistant input.md -o notes/
```

## CLI 使用方式

```
ai-study-assistant <input> [-o OUTPUT] [--provider NAME] [--config PATH]
```

| 参数 | 说明 | 默认 |
|---|---|---|
| `input` | 输入文件（.md/.txt） | 必填 |
| `-o, --output` | 输出目录 | `./output` |
| `--provider` | 覆盖 provider | 配置文件默认 |
| `--config` | 配置文件路径 | 默认加载 config.yaml |

示例：

```bash
# 用 kimi 生成笔记
uv run ai-study-assistant input.md -o notes/ --provider kimi
```

## 配置说明

配置分两处：

**`config.yaml`**（厂商与生成参数）：

```yaml
provider: openai        # openai | deepseek | kimi | qwen | ollama

llm:
  temperature: 0.3
  max_tokens: null      # null = 不限制
```

**`.env`**（API Key，经 `api_key_env` 读取，不写死密钥）：

```bash
OPENAI_API_KEY=sk-xxx   # 或 DEEPSEEK_API_KEY / KIMI_API_KEY / QWEN_API_KEY
```

### 内置 provider

| 名称 | base_url | model | 需要的环境变量 |
|---|---|---|---|
| openai | https://api.openai.com/v1 | gpt-4o-mini | `OPENAI_API_KEY` |
| deepseek | https://api.deepseek.com/v1 | deepseek-chat | `DEEPSEEK_API_KEY` |
| kimi | https://api.moonshot.cn/v1 | moonshot-v1-8k | `KIMI_API_KEY` |
| qwen | https://dashscope.aliyuncs.com/compatible-mode/v1 | qwen-plus | `QWEN_API_KEY` |
| ollama | http://localhost:11434/v1 | qwen2.5 | 无需 key |

完整说明见 `config.example.yaml`。

## 项目架构

```
输入文件
  ↓ parsers.parse_file()
Document
  ↓ pipeline.StudyPipeline.run()
StudyNote
  ↓ storage.save()
Markdown 笔记文件
```

```
src/ai_study_assistant/
├── config/      # 配置加载 + 厂商 preset（AppConfig / ResolvedLLM）
├── llm/         # 厂商无关 LLM 客户端（LLMClient 协议 + OpenAI 兼容实现）
├── parsers/     # 解析器注册表（可插拔，按扩展名分发）
├── pipeline/    # 整理管线（分段 + prompt + 结构化输出）
├── storage/     # 输出落盘（StudyNote → Markdown 文件）
└── cli.py       # 命令行入口（组装各层）
```

## 开发

```bash
# 运行测试
uv run pytest

# 代码规范检查
uv run ruff check
```

提交遵循 [Conventional Commits](https://www.conventionalcommits.org/)。

## 当前限制

- 仅支持 Markdown/TXT 输入（DOCX/PDF/PPTX 预留中）
- 需自备 OpenAI 兼容 API 的 Key
- 单文件处理（批处理未实现）

## Roadmap

- ✅ Phase 1：MVP — Markdown/TXT → LLM → 生成 Markdown 学习笔记
- ⏳ Phase 2：Web UI + 模型配置界面
- ⏳ Phase 3：DOCX / PPTX 解析
- ⏳ Phase 4：PDF 解析
- ⏳ Phase 5：高级整理（多文件、批处理）

## License

[MIT](LICENSE)
