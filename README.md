# AI Study Assistant

本地运行的 AI 学习资料整理工具。

## 目标

读取学习资料（Markdown / TXT / DOCX / PPTX / PDF），调用大语言模型，自动生成结构化学习笔记。

## 核心设计

- **厂商无关**：通过 OpenAI 兼容 API 接入，切换厂商只改配置，不改代码。
- **可插拔解析器**：每种文件格式是一个独立解析器，通过注册表按扩展名分发，未来新增 DOCX/PDF/PPTX 是增量添加。
- **管线分层**：`解析 → 分段 → LLM 调用 → 结构化输出`，各层解耦。

## 技术栈

- Python 3.11 + uv
- OpenAI 兼容 API（openai SDK）
- CLI 优先（MVP 阶段不使用 Web 框架）

## 项目结构

```
src/ai_study_assistant/
├── config/      # 配置加载 + 厂商 preset
├── parsers/     # 解析器注册表（可插拔）
├── llm/         # 厂商无关 LLM 客户端
├── pipeline/    # 整理管线（分段 + prompt + 结构化输出）
└── storage/     # 输出保存
```

## 开发状态

**Phase 0（初始化）** 进行中。业务代码尚未开始。

## 快速开始

> 待环境就绪后补充。

```bash
uv sync
uv run ai-study
```

## 路线图

- Phase 1：MVP — Markdown/TXT 解析 → LLM 调用 → 生成 Markdown 学习笔记
- Phase 2：Web UI（FastAPI）+ 模型配置界面
- Phase 3：DOCX / PPTX 解析
- Phase 4：PDF 解析
- Phase 5：高级整理功能（多文件、批处理等）
