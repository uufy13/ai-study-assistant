# CLI 模块设计文档

> 所属阶段：Phase 1.5（用户入口，组装层）
> 状态：已确认，待实现
> 上游依赖：config / llm / parsers / pipeline / storage（全部完成）
> 下游消费方：终端用户

## 1. 需求分析

CLI 解决什么问题：把已完成的 5 个模块组装成「一条命令」的用户入口——`ai-study-assistant input.md` 直接产出学习笔记，用户无需感知分层。

用户操作流程：

```
$ ai-study-assistant input.md -o notes/ --provider kimi
  → 解析参数 → 加载配置 → 构造 LLMClient → 解析文件 → 生成笔记 → 落盘 → 打印输出路径
```

MVP 范围：单文件输入、单文件笔记输出、支持切换 provider、支持自定义配置路径。不做：批量处理、多文件、交互式。

非功能需求：用户友好（清晰帮助/错误提示/成功反馈）、可测试（流程函数可注入 FakeLLMClient）、无状态。

## 2. 命令设计

```
ai-study-assistant <input> [-o OUTPUT] [--provider NAME] [--config PATH]
```

| 参数 | 必填 | 说明 | 默认 |
|---|---|---|---|
| input | 是（位置参数） | 输入文件（.md/.txt，由 parser 决定） | — |
| -o, --output | 否 | 输出目录 | ./output |
| --provider | 否 | 覆盖 provider，映射 cfg.resolve(name) | 配置文件默认 |
| --config | 否 | 配置文件路径 | 无（load_config() 用默认） |

刻意不暴露（未来扩展）：--chunk-size（用 pipeline 默认 2000）、--model（具体模型覆盖，可经 config 自定义 providers）。

入口注册（实现阶段加 pyproject.toml）：

```toml
[project.scripts]
ai-study-assistant = "ai_study_assistant.cli:main"
```

## 3. 调用流程

```
用户输入 → main() 解析参数 → load_config(config_path) → cfg.resolve(provider)
        → create_client(resolved) → parse_file(input) → StudyPipeline.run(document)
        → storage.save(note, output_dir) → 打印输出路径 → exit 0
```

核心流程封装为可注入 client 的函数：

```python
def run_pipeline(input_path, output_dir, *, provider=None, config_path=None, client=None) -> Path:
    # client 参数用于测试注入 FakeLLMClient；为 None 时才从 config 构造
```

## 4. 配置加载

- API Key 读取：完全由 config 处理——load_config() 内部 load_dotenv(override=True) 读 .env，key 经 api_key_env 间接读取。CLI 不直接接触 key。
- config 加载：load_config(config_path)，--config 传入时用该路径，否则用默认。
- CLI 覆盖配置：仅两处——--provider 覆盖默认 provider；--config 覆盖配置文件路径。其余走配置文件。

## 5. 错误处理

CLI 统一捕获下层领域异常 → 用户友好消息 + 非零退出码。

| 场景 | 下层异常 | 退出码 |
|---|---|---|
| 文件不存在 | FileReadError | 1 |
| 格式不支持 | UnknownFormatError | 1 |
| 配置失败 | ConfigError | 1 |
| API 认证失败 | LLMAuthenticationError | 1 |
| API 限流 | LLMRateLimitError | 1 |
| 网络失败 | LLMConnectionError | 1 |
| 输入为空 | EmptyContentError | 1 |
| 输出失败 | StorageError | 1 |
| 未知异常 | — | 2 |

策略：捕获已知领域异常（ConfigError/ParserError/LLMError/PipelineError/StorageError）→ 友好提示 + exit 1；未知 → 堆栈 + exit 2。

## 6. 文件结构设计

单文件方案：

```
src/ai_study_assistant/cli.py
```

内部函数分离（保证可测试）：

| 函数 | 职责 |
|---|---|
| build_parser() -> ArgumentParser | argparse 参数定义 |
| run_pipeline(input, output_dir, *, provider, config_path, client) -> Path | 核心流程（client 可注入） |
| main(argv=None) -> int | 入口：parse → 调 run_pipeline → 打印 → 返回退出码 |

为何单文件而非 cli/ 包：CLI 是薄胶水层（约 100 行），单文件足够；拆包是过度设计。

## 7. 测试方案

测 run_pipeline()（可注入 FakeLLMClient）为主。

| # | 用例 | 验证点 |
|---|---|---|
| 1 | 端到端 | tmp 输入 + FakeLLMClient + tmp 输出 → 生成笔记，内容正确 |
| 2 | 输出路径 | 返回 output_dir/{title}.md |
| 3 | 文件不存在 | → FileReadError |
| 4 | 格式不支持 | → UnknownFormatError |
| 5 | provider 切换 | 验证 cfg.resolve(provider) 用对 provider（monkeypatch） |
| 6 | argparse | 解析 input/output/provider/config 正确 |
| 7 | 成功退出码 | main() 成功返回 0 |

零真实 API、零网络、输出用 tmp_path。

## 8. 明确边界

不设计：Web 界面、GUI、数据库、云服务。CLI 只是本地命令行入口。

## 9. 决策总结

| 决策 | 选择 | 理由 |
|---|---|---|
| 结构 | 单文件 cli.py + 内部函数分离 | 薄胶水层，避免过度设计 |
| 核心可测性 | run_pipeline(client=...) 注入 | FakeLLMClient 端到端测试 |
| 参数 | input + -o + --provider + --config | MVP 最小，chunk-size/model 预留 |
| 配置 | 复用 config，CLI 仅覆盖 provider/config 路径 | 不重复造配置系统 |
| 错误 | 捕获领域异常 → 友好消息 + exit code | 用户友好，非零退出 |
| 入口 | pyproject [project.scripts] | uv run ai-study-assistant 可用 |
