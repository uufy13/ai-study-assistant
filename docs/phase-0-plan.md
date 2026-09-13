# Phase 0 — 项目初始化规划

> 项目：AI Study Assistant
> 目标：本地运行的 AI 学习资料整理工具
> 状态：规划已确认，正在执行

## 已确认方向

1. 输入格式：Markdown / TXT / DOCX / PPTX / PDF
2. 模型接入：OpenAI Compatible API，不绑定单一厂商
3. MVP：仅 Markdown / TXT
4. 流程：软件工程流程，每步解释设计原因
5. 技术栈：**Python 3.11 + uv + CLI**（MVP 不使用 FastAPI）
6. MVP 数据流：`Markdown/TXT 读取 → LLM 调用 → 生成 Markdown 学习笔记`

## 技术选型结论

| 决策 | 选择 | 设计原因 |
|---|---|---|
| 语言 | Python 3.11+ | 文档解析生态最强（docx/pptx/PyMuPDF），OpenAI SDK 一等公民 |
| 依赖管理 | uv | 快、锁定文件干净；降级用 pip+venv |
| MVP 入口 | CLI | 最易测试、最快出可验证结果；UI 延后到 Phase 2 |
| 配置格式 | YAML + .env | YAML 人可读（多厂商 preset），.env 存密钥不进 Git |
| 核心原则 | 解析器注册表 + 厂商无关 LLM 抽象 | 让「不绑定厂商」「五种格式增量添加」成立的关键 |

## 目录结构

```
ai-study-assistant/
├── docs/                        # 文档
├── src/ai_study_assistant/      # 主包（src 布局）
│   ├── config/                  # 配置加载 + 厂商 preset
│   ├── parsers/                 # 解析器注册表（可插拔）
│   ├── llm/                     # 厂商无关 LLM 抽象
│   ├── pipeline/                # 整理管线
│   └── storage/                 # 输出保存
├── tests/                       # 测试（镜像 src 结构）
├── data/                        # 本地样本（gitignore）
├── .env.example
├── config.example.yaml
├── .python-version
├── pyproject.toml
└── README.md
```

## 第一阶段（MVP）任务列表

| # | 任务 | 验收标准 | 设计原因 |
|---|---|---|---|
| 1 | 项目脚手架 | pytest 空跑、ruff 无错 | 先有可测空壳 |
| 2 | 配置模块 | 加载 YAML + .env，切换厂商 preset | 满足「配置可切换」核心验收点 |
| 3 | LLM 客户端封装 | 同代码指向任一 base_url 发起对话 | 换厂商零改代码 |
| 4 | 解析器注册表 + 基类 | 装饰器注册，按扩展名分发 | 为 DOCX/PPTX/PDF 预留接口 |
| 5 | Markdown 解析器 | 抽取正文/标题，忽略 front-matter | 结构化抽取是整理前提 |
| 6 | TXT 解析器 | 编码探测（UTF-8/GBK） | 中文 TXT 常见 GBK |
| 7 | 分段器 | 语义边界切块，不超上下文 | LLM token 上限 |
| 8 | 整理管线 | 文件 → 结构化结果（摘要/要点等） | 端到端闭环 |
| 9 | CLI 入口 | 指定文件+配置即可出结果 | 最快验收 |
| 10 | 单元测试 | 核心逻辑覆盖，LLM 用 mock | 不烧额度 |
| 11 | 文档 | README 可一键跑通 | 交付可复现 |

> 排序逻辑：1→4 是地基（可测壳 + 两个可插拔抽象），5→8 是功能，9→10 是验收保障。
> **3 号（LLM 抽象）和 4 号（解析器注册表）是全局最重要两步**——做对则后续格式/厂商都是增量添加，做错则全部返工。

## Git 规范

- 分支：`main`
- 提交规范：Conventional Commits（feat/fix/chore/docs/test）
- 密钥与资料：`.env`、`data/` 不入库
