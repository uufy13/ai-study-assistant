# config 模块设计文档

> 所属阶段：Phase 1（MVP 基础层）
> 状态：已确认，待实现
> 依赖方：llm / pipeline / cli

## 1. 需求分析

### 功能需求（FR）

| 编号 | 需求 | 优先级 |
|---|---|---|
| FR1 | 从 `config.yaml` 读取配置 | P0 |
| FR2 | 从 `.env` 读取密钥（密钥绝不进 YAML/代码/版本库） | P0 |
| FR3 | 内置 DeepSeek/Kimi/Qwen/OpenAI/Ollama 厂商预设 | P0 |
| FR4 | 切换厂商只改一个字段（`provider`） | P0 |
| FR5 | 允许用户覆盖内置预设字段、自定义未知厂商 | P1 |
| FR6 | 配置缺失/非法时启动即报错（fail-fast，清晰错误信息） | P0 |
| FR7 | 支持 `${VAR}` 占位符引用环境变量 | P1 |

### 非功能需求（NFR）

- **厂商无关**：模块内不出现任何厂商专属分支（禁止 `if provider == "deepseek"` 这类代码）。
- **类型安全**：配置经 schema 校验后交给下游，下游无需再做防御性判断。
- **可测试**：加载是纯函数，路径/环境可注入，不依赖全局状态。
- **只读**：加载后配置对象冻结，运行期不可被业务代码篡改。

### 约束

- 符合现有架构：`config/` 是被 `llm/`、`pipeline/`、`cli` 依赖的最底层，它本身不依赖任何业务模块。
- MVP 只用 Markdown/TXT，但配置结构要为后续 DOCX/PDF/PPTX 及多厂商 UI 切换预留扩展点。

## 2. 配置文件格式设计（YAML）

```yaml
# config.yaml
provider: deepseek          # ① 激活的厂商名（唯一的切换点）

llm:                        # ② 生成参数（与厂商无关）
  temperature: 0.3
  max_tokens: 2000

providers:                  # ③ 可选：覆盖内置预设 / 自定义厂商
  deepseek:
    model: deepseek-reasoner          # 覆盖内置默认 model
  my_gateway:                        # 自定义任意 OpenAI 兼容端点
    base_url: http://192.168.1.10:8000/v1
    model: llama3
    api_key_env: MY_GATEWAY_KEY
```

### 字段说明

| 字段 | 必填 | 说明 |
|---|---|---|
| `provider` | 否（默认 `openai`） | 激活的厂商名，指向 `providers` 或内置预设 |
| `llm.temperature` | 否（默认 0.3） | 采样温度 |
| `llm.max_tokens` | 否 | 单次最大输出 token，可空 |
| `providers.<name>.base_url` | 自定义时必填 | OpenAI 兼容端点地址 |
| `providers.<name>.model` | 否 | 默认模型 |
| `providers.<name>.api_key_env` | 否 | 密钥来源的环境变量名 |

### 内置厂商预设（写在代码 `presets.py`，非 YAML）

> 设计原因：URL 和默认模型是「厂商知识」，用户不该去记；放进代码里作为策展默认值，YAML 只负责「选择 + 覆盖」。换厂商 = 改一个 `provider` 字段。

| 预设名 | base_url | 默认 model | 密钥环境变量 |
|---|---|---|---|
| `deepseek` | `https://api.deepseek.com/v1` | `deepseek-chat` | `DEEPSEEK_API_KEY` |
| `kimi` | `https://api.moonshot.cn/v1` | `moonshot-v1-8k` | `KIMI_API_KEY` |
| `qwen` | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-plus` | `QWEN_API_KEY` |
| `openai` | `https://api.openai.com/v1` | `gpt-4o-mini` | `OPENAI_API_KEY` |
| `ollama` | `http://localhost:11434/v1` | `qwen2.5` | 无（本地无需密钥） |

> `api_key_env` 是密钥读取的间接层：用户已有官方名 `DASHSCOPE_API_KEY` 也没关系，在 YAML 里把 `qwen.api_key_env` 改成它即可。

## 3. 环境变量设计（.env）

```bash
# .env（只存密钥 + 可选覆盖，绝不入库）
DEEPSEEK_API_KEY=sk-xxxx
KIMI_API_KEY=sk-xxxx
QWEN_API_KEY=sk-xxxx
OPENAI_API_KEY=sk-xxxx
MY_GATEWAY_KEY=sk-xxxx

# 可选：用环境变量临时覆盖 provider（CLI 一次切换用）
# AI_STUDY_PROVIDER=kimi
```

### 命名规则

| 类别 | 前缀 | 示例 |
|---|---|---|
| 各厂商密钥 | `<VENDOR>_API_KEY` | `DEEPSEEK_API_KEY` |
| 全局覆盖（可选） | `AI_STUDY_*` | `AI_STUDY_PROVIDER` |

### 优先级（高 → 低，逐级覆盖）

```
1. 环境变量 (.env)      ← 密钥、最终覆盖，最高
2. config.yaml providers  ← 覆盖内置预设 / 自定义厂商
3. config.yaml provider + llm ← 选择厂商 + 生成参数
4. 内置预设（代码）        ← 厂商 URL / 默认 model，最低
```

**核心安全原则**：`api_key` 只通过 `api_key_env` 间接读取，任何一层（YAML/预设/代码）都不存明文密钥。

## 4. OpenAI Compatible API 支持方案

### 核心洞察

DeepSeek / Kimi / Qwen / OpenAI / Ollama 都提供 OpenAI 兼容端点——它们只是 `base_url + api_key + model` 三个值不同。因此：

> 一个统一的 `ResolvedLLM` 结构就能描述任意厂商，切换厂商 = 换这三个值的来源，下游 `llm/` 模块的调用代码完全不变。

### 两层抽象（关键设计）

| 层 | 字段 | 归属 |
|---|---|---|
| 端点配置（连谁） | `base_url`、`api_key`、默认 `model` | 由 provider 决定 |
| 生成参数（怎么调） | `temperature`、`max_tokens` | 全局，与厂商无关 |

**设计原因**：对应 OpenAI SDK 的两处用法——`base_url/api_key` 是客户端构造参数，`model/temperature` 是每次请求参数。分开后，未来 `pipeline` 可「同厂商、不同 temperature」而不改端点配置。

### 厂商无关的达成方式

- 预设以数据形式存在（`presets.py` 里的字典），不是代码分支。
- `resolve()` 返回完全解析后的 `ResolvedLLM`，`llm/` 模块拿到的是可直接构造客户端的对象，不感知「厂商」。

## 5. 模块接口设计

### 文件结构

```
config/
├── __init__.py      # 公开导出（模块对外契约）
├── models.py        # pydantic 数据模型（schema + 校验）
├── presets.py       # BUILTIN_PRESETS 内置厂商预设
├── loader.py        # load_config() 加载 + 合并 + 解析
└── errors.py        # ConfigError / MissingAPIKeyError / UnknownProviderError
```

### 数据模型（接口契约）

```python
class LLMParams(BaseModel):
    temperature: float = 0.3
    max_tokens: int | None = None

class ProviderSpec(BaseModel):
    base_url: str
    model: str
    api_key_env: str | None = None

class ResolvedLLM(BaseModel):        # 交给 llm 模块的最终结果
    base_url: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int | None

class AppConfig(BaseModel):
    provider: str = "openai"
    llm: LLMParams = LLMParams()
    providers: dict[str, ProviderSpec] = {}   # 合并内置 + 用户覆盖后
    def resolve(self, name: str | None = None) -> ResolvedLLM: ...
```

### 公开 API（模块对外的唯一入口）

```python
# config/__init__.py
__all__ = ["load_config", "AppConfig", "ProviderSpec", "LLMParams", "ResolvedLLM",
           "BUILTIN_PRESETS", "ConfigError", "MissingAPIKeyError", "UnknownProviderError"]

def load_config(config_path=None, env_path=None) -> AppConfig:
    """加载配置：读 .env → 读 YAML → 合并内置预设 → 校验 → 返回 AppConfig。"""
```

### 下游调用方式（llm 模块视角）

```python
cfg = load_config()
r = cfg.resolve()                 # 用默认 provider
# r = cfg.resolve("kimi")          # 或显式切换
client = OpenAI(base_url=r.base_url, api_key=r.api_key)   # 厂商无关
```

> `load_config` 无参数时用默认路径（`config.yaml` + `.env`），参数可注入以便测试。

## 6. 测试方案

### 依赖注入策略

- 用 `tmp_path`（pytest fixture）生成临时 YAML/.env 文件，不碰真实配置。
- 用 `monkeypatch` 注入环境变量，测试后自动还原。
- `load_config` 必须接受 `config_path` / `env_path` 参数（上面接口已体现）。

### 测试用例表

| # | 用例 | 验证点 |
|---|---|---|
| 1 | 最小配置加载 | 只有 `provider: deepseek` 时，默认值正确补齐 |
| 2 | 内置预设完整性 | 5 个预设都有合法 `base_url` 与 `model` |
| 3 | 厂商切换 | `resolve("kimi")` 返回 Kimi 的 URL/model，`resolve("deepseek")` 返回 DeepSeek 的 |
| 4 | 密钥解析 | `api_key_env` 指向的环境变量值被正确读入 `api_key` |
| 5 | 密钥缺失报错 | 未设置对应密钥 → 抛 `MissingAPIKeyError`（fail-fast） |
| 6 | 未知厂商报错 | `provider: nonexistent` → 抛 `UnknownProviderError` |
| 7 | 用户覆盖预设 | YAML 覆盖内置 `model` 生效 |
| 8 | 自定义厂商 | 无预设的 `base_url+model+api_key_env` 可直接使用 |
| 9 | `${VAR}` 占位符 | YAML 里 `${VAR}` 正确替换为环境变量值 |
| 10 | 环境变量最高优先 | env 覆盖 YAML 同名字段 |
| 11 | 默认 provider | 未指定 `provider` 时回退 `openai` |
| 12 | 非法值校验 | `temperature` 越界/类型错误 → 抛 `ValidationError` |

### 关键测试原则

- 不真实调用任何 API：全部是纯加载/合并/校验测试，零网络、零额度消耗。
- 每个用例独立、无共享状态（`monkeypatch`/`tmp_path` 隔离）。

## 7. 决策总结

| 决策 | 选择 | 理由 |
|---|---|---|
| Schema 校验 | pydantic | 已在依赖树；启动即校验，错误信息清晰 |
| YAML 解析 | pyyaml | 已是直接依赖 |
| .env 加载 | python-dotenv | 小而标准，处理引号/注释/插值 |
| 密钥存储 | 仅 `.env`，经 `api_key_env` 间接读 | 安全 + 可切换 |
| 厂商知识 | 内置 preset（数据） | 用户只选不背 URL |

**实现时的依赖变更**：`pyproject.toml` 增补 `pydantic>=2.0` 与 `python-dotenv>=1.0` 为直接依赖（pydantic 当前只是 openai 的传递依赖，直接用需显式声明）。
