# llm 模块设计文档

> 所属阶段：Phase 1（MVP 第二层）
> 状态：已确认，待实现
> 上游依赖：config 模块（消费 `config.resolve()` 的 `ResolvedLLM`）
> 下游消费方：pipeline

## 0. 设计前提

`cfg.resolve()` 返回的 `ResolvedLLM` 已是厂商无关的完整端点配置：

```python
ResolvedLLM(base_url, api_key, model, temperature, max_tokens)
```

openai SDK 3.13.0 已确认兼容：`OpenAI(api_key=..., base_url=...)` 构造 + `chat.completions.create(model, messages, temperature, max_tokens)` 调用。llm 模块不新增任何依赖（openai 已在 pyproject）。

## 1. 需求分析

| 编号 | 需求 | 优先级 |
|---|---|---|
| FR1 | 封装 OpenAI 兼容 API，提供统一的文本生成接口 | P0 |
| FR2 | 消费 `config.resolve()` 的 `ResolvedLLM`，不感知厂商 | P0 |
| FR3 | 参数默认取自 `ResolvedLLM`，支持单次调用覆盖（如换 model/temperature） | P0 |
| FR4 | 将 OpenAI SDK 异常映射为领域异常，屏蔽 SDK 细节 | P0 |
| FR5 | 可注入依赖（fake/mock），零真实调用即可测试 | P0 |
| FR6 | 处理无密钥的本地端点（如 Ollama，`api_key=""`） | P1 |

非功能需求：厂商无关、同步优先（MVP CLI，异步留给 Phase 2）、测试零网络零额度。

## 2. 模块职责

llm 模块是唯一接触 openai SDK 的地方，对上层（pipeline）隐藏 SDK：

| 职责 | 说明 |
|---|---|
| 构造客户端 | 从 `ResolvedLLM` 构造 OpenAI 兼容客户端 |
| 文本生成 | `generate(messages) -> str`，屏蔽 SDK 请求细节 |
| 参数合并 | `ResolvedLLM` 默认值 + 单次调用覆盖 |
| 错误归一 | SDK 异常 → 领域异常层次 |
| 依赖注入 | 允许注入 fake 客户端，支撑测试 |

**明确不做**：不做 prompt 模板、不做分段（chunker 在 pipeline）、不做结构化解析（JSON schema 属于 pipeline）。

## 3. 文件结构

```
llm/
├── __init__.py      # 公开导出
├── client.py        # Message / LLMClient 协议 / OpenAICompatClient / create_client 工厂
└── errors.py        # LLMError 异常层次
```

## 4. 类和接口设计

### 4.1 消息类型

```python
class Message(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str
```

用 pydantic（与 config 一致），`model_dump()` 直接得到 SDK 需要的 role/content 结构。

### 4.2 客户端协议（测试 mock 的关键接缝）

```python
class LLMClient(Protocol):
    def generate(self, messages: Sequence[Message], **overrides) -> str:
        """发起一次对话补全，返回文本内容。"""
```

用 Protocol 而非 ABC：pipeline 只依赖「能生成文本」的能力，不关心实现。

### 4.3 具体实现（唯一接触 SDK 的类）

```python
class OpenAICompatClient:
    def __init__(self, resolved: ResolvedLLM, *, client: Any | None = None): ...
    def generate(self, messages: Sequence[Message], **overrides) -> str: ...
```

- `client` 参数：默认 None 时内部从 resolved 构造 `OpenAI(api_key, base_url)`；测试注入 fake。
- `generate`：合并参数（resolved 默认 + overrides 覆盖）→ 调 SDK → 提取 `choices[0].message.content` 返回。

### 4.4 工厂函数（消费 config.resolve() 的入口）

```python
def create_client(resolved: ResolvedLLM) -> LLMClient: ...
```

上层调用方式（pipeline 视角）：

```python
cfg = load_config()
client = create_client(cfg.resolve())                     # 默认厂商
text = client.generate([Message("user", "...")])

other = create_client(cfg.resolve("kimi"))                # ① 换厂商 → 新客户端
text2 = client.generate(msgs, model="deepseek-reasoner")  # ② 同厂商换 model → 单次覆盖
```

### 4.5 公开导出

```python
# llm/__init__.py
__all__ = ["create_client", "LLMClient", "OpenAICompatClient", "Message",
           "LLMError", "LLMAuthenticationError", "LLMRateLimitError",
           "LLMConnectionError", "LLMTimeoutError", "LLMAPIError",
           "LLMResponseError", "LLMConfigurationError"]
```

### 4.6 空密钥处理（设计决策）

OpenAI SDK 要求 api_key 非空，但 Ollama 等本地端点无密钥（resolve() 返回 ""）。
决策：`OpenAICompatClient` 构造时若 api_key 为空，使用占位符 `"not-required"` 传给 SDK。
理由：本地端点忽略该值，同时不污染 config 层。

## 5. 错误处理方案

### 异常层次（领域错误，屏蔽 SDK）

```
LLMError                        # 基类
├── LLMAuthenticationError      # 401 — 密钥错误/无权限
├── LLMRateLimitError           # 429 — 限流/额度不足
├── LLMConnectionError          # 网络/连接失败
├── LLMTimeoutError             # 请求超时
├── LLMAPIError                 # 其它 4xx/5xx，携带 status_code
├── LLMResponseError            # 响应缺失/无法解析（无 choices 等）
└── LLMConfigurationError       # 配置问题（如必需参数缺失）
```

### SDK 异常 → 领域异常映射

| openai SDK 异常 | 领域异常 | 典型场景 |
|---|---|---|
| AuthenticationError | LLMAuthenticationError | key 填错/过期 |
| RateLimitError | LLMRateLimitError | 429 限流 |
| APITimeoutError | LLMTimeoutError | 请求超时 |
| APIConnectionError | LLMConnectionError | 网络断开/base_url 不可达 |
| APIStatusError | LLMAPIError | 其它 HTTP 错误（带状态码） |
| APIError（兜底） | LLMError | 未分类 SDK 错误 |

映射在 generate() 内部 try/except 完成，上层只需捕获 LLMError。错误信息面向用户（如「401 认证失败：请检查 api_key」），并保留原始异常作 __cause__。

## 6. 测试方案

### Mock 策略（零真实调用）

| 层级 | 手段 | 验证目标 |
|---|---|---|
| 客户端级 | 注入 FakeOpenAI（含 .chat.completions.create() 返回假响应） | SDK 调用参数、文本提取、错误映射 |
| 接口级 | 纯 Python FakeLLMClient（实现 Protocol） | 证明 Protocol 可被下游（pipeline）mock |

### 测试用例表

| # | 用例 | 验证点 |
|---|---|---|
| 1 | 工厂构造 | create_client 把 base_url/api_key/model 正确传给 SDK |
| 2 | 文本返回 | 假响应 → 正确提取 choices[0].message.content |
| 3 | 消息传递 | Message 列表正确转成 SDK 的 role/content 结构 |
| 4 | 默认参数 | temperature/max_tokens 取 ResolvedLLM 的值 |
| 5 | 参数覆盖 | generate(..., temperature=0.9) 覆盖默认值 |
| 6 | model 覆盖 | generate(..., model="x") 覆盖默认 model |
| 7 | 认证错误映射 | AuthenticationError → LLMAuthenticationError |
| 8 | 限流映射 | RateLimitError → LLMRateLimitError |
| 9 | 连接映射 | APIConnectionError → LLMConnectionError |
| 10 | 空响应报错 | 无 choices → LLMResponseError |
| 11 | 空密钥占位 | api_key="" → SDK 收到占位符 "not-required" |
| 12 | Protocol 可 mock | FakeLLMClient 直接实现 LLMClient，返回 canned 文本 |

### 关键原则

零网络零额度（所有用例注入 fake）、每个用例独立、复用 config 的 ResolvedLLM 字面量构造。

## 7. 决策总结

| 决策 | 选择 | 理由 |
|---|---|---|
| 抽象方式 | Protocol（非 ABC） | 最小化耦合 |
| 依赖注入 | 构造器注入 client | 生产用默认 SDK，测试注入 fake |
| 消息类型 | pydantic Message | 与 config 一致，model_dump() 直通 SDK |
| 错误处理 | 领域异常层次 + 映射 | 上层只捕 LLMError |
| 空密钥 | 占位符 "not-required" | 兼容 Ollama，不污染 config |
| 同步/异步 | MVP 同步，异步预留 | CLI 不需要 async |
| 依赖变更 | 无 | openai 已在依赖中 |
