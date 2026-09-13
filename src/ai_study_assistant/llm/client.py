"""Vendor-neutral LLM client implementation.

This module is the only place in the codebase that imports the OpenAI SDK.
Upstream callers interact with the ``LLMClient`` protocol and the
``create_client`` factory, remaining fully decoupled from vendor details.
"""

from collections.abc import Sequence
from typing import Any, Literal, Protocol, runtime_checkable

from openai import (
    APIConnectionError,
    APIError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel

from ai_study_assistant.config import ResolvedLLM

from .errors import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)


class Message(BaseModel):
    """A single chat message.

    ``model_dump()`` produces the exact ``{"role": ..., "content": ...}``
    structure expected by OpenAI-compatible completion APIs.
    """

    role: Literal["system", "user", "assistant"]
    content: str


@runtime_checkable
class LLMClient(Protocol):
    """Minimal protocol for text-generating clients.

    Implementations must expose ``generate(messages, **overrides) -> str``.
    Both :class:`OpenAICompatClient` and plain Python fakes satisfy this
    protocol, which keeps pipeline mock-friendly and vendor-agnostic.
    """

    def generate(self, messages: Sequence[Message], **overrides: Any) -> str:
        """Request a chat completion and return the generated text."""


class OpenAICompatClient:
    """An OpenAI-compatible client driven by a vendor-neutral ``ResolvedLLM``.

    The constructor accepts an optional ``client`` keyword argument so tests
    and downstream callers can inject a fake or shim without ever touching
    the real SDK.
    """

    def __init__(self, resolved: ResolvedLLM, *, client: Any | None = None) -> None:
        self._resolved = resolved
        self._client = client if client is not None else self._build_sdk_client(resolved)

    @staticmethod
    def _build_sdk_client(resolved: ResolvedLLM) -> OpenAI:
        # The OpenAI SDK rejects an empty api_key, but local endpoints such as
        # Ollama do not require one. We substitute a placeholder without
        # leaking that concern into the config layer.
        api_key = resolved.api_key or "not-required"
        return OpenAI(api_key=api_key, base_url=resolved.base_url)

    def generate(self, messages: Sequence[Message], **overrides: Any) -> str:
        """Generate text, mapping all SDK errors to domain exceptions."""
        if not messages:
            raise LLMResponseError("At least one message is required.")

        model = overrides.get("model", self._resolved.model)
        temperature = overrides.get("temperature", self._resolved.temperature)
        max_tokens = overrides.get("max_tokens", self._resolved.max_tokens)

        sdk_messages = [msg.model_dump() for msg in messages]
        payload: dict[str, Any] = {
            "model": model,
            "messages": sdk_messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        try:
            response = self._client.chat.completions.create(**payload)
        except AuthenticationError as exc:
            raise LLMAuthenticationError(
                "401 认证失败：请检查 api_key"
            ) from exc
        except RateLimitError as exc:
            raise LLMRateLimitError(
                "429 请求受限：已达到额度或速率上限"
            ) from exc
        except APITimeoutError as exc:
            raise LLMTimeoutError("请求超时：请稍后重试") from exc
        except APIConnectionError as exc:
            raise LLMConnectionError(
                "连接失败：请检查网络或 base_url 配置"
            ) from exc
        except APIStatusError as exc:
            raise LLMAPIError(
                f"API 返回错误 ({exc.status_code})：{exc.message}",
                status_code=exc.status_code,
            ) from exc
        except APIError as exc:
            raise LLMError(f"调用模型服务时发生错误：{exc}") from exc

        try:
            content = response.choices[0].message.content
        except (AttributeError, IndexError, TypeError) as exc:
            raise LLMResponseError(
                "模型响应异常：未找到有效的 completion 内容"
            ) from exc

        if content is None:
            raise LLMResponseError("模型响应异常：返回内容为空")

        return content


def create_client(resolved: ResolvedLLM) -> LLMClient:
    """Create a vendor-neutral LLM client from a resolved configuration."""
    return OpenAICompatClient(resolved)
