# AI Study Assistant

一个面向学生和知识工作者的本地 AI 学习助手。

将 Markdown/TXT 学习资料交给 AI，自动生成结构化学习笔记。

## ✨ 功能特性

-   多模型支持：OpenAI、DeepSeek、Kimi、Qwen、Ollama
-   OpenAI Compatible API，切换模型只需修改配置
-   Markdown/TXT 自动解析
-   自动分块、调用 LLM、生成结构化笔记
-   Markdown 文件输出
-   本地保存 API Key 和数据

## 工作流程

``` text
输入资料
   ↓
Parser 文件解析
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

示例：

``` bash
uv run ai-study-assistant demo/input-machine-learning.md -o notes/
```

## CLI

``` bash
ai-study-assistant <input> [-o OUTPUT] [--provider NAME] [--config PATH]
```

参数：

  参数         说明
  ------------ ------------------------
  input        输入 Markdown/TXT 文件
  -o           输出目录
  --provider   指定 AI 服务
  --config     指定配置文件

## 支持格式

  格式       状态
  ---------- ------
  Markdown   ✅
  TXT        ✅
  DOCX       计划
  PDF        计划
  PPTX       计划

## 项目结构

``` text
src/ai_study_assistant/

config/      配置管理
llm/         AI 客户端
parsers/     文件解析
pipeline/    笔记生成
storage/     文件保存
cli.py       命令入口
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

-   74 tests passed
-   ruff clean

## Roadmap

### v0.1.0

-   Markdown/TXT 支持
-   CLI
-   多模型支持
-   自动生成学习笔记

### 后续

-   Web UI
-   PDF/DOCX/PPTX
-   批量处理
-   知识库

## License

MIT License
