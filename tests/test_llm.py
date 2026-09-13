"""Tests for the llm module.

All tests use injected fakes; no real network calls or API tokens are needed.
"""

from collections.abc import Sequence
from typing import Any
from unittest.mock import MagicMock

import pytest
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    RateLimitError,
)

from ai_study_assistant.config import ResolvedLLM
from ai_study_assistant.llm import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMClient,
    LLMConnectionError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
    Message,
    OpenAICompatClient,
    create_client,
)


def _resolved(
    *,
    base_url: str = "https://api.example.com/v1",
    api_key: str = "secret",
    model: str = "default-model",
    temperature: float = 0.3,
    max_tokens: int | None = 100,
) -> ResolvedLLM:
    return ResolvedLLM(
        base_url=base_url,
        api_key=api_key,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
    )


def _make_fake_openai(content: str = "fake response") -> Any:
    """Build a minimal fake OpenAI-like client that returns ``content``."""
    fake_client = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = [MagicMock()]
    fake_response.choices[0].message.content = content
    fake_client.chat.completions.create.return_value = fake_response
    return fake_client


def test_factory_passes_config_to_sdk_client(monkeypatch) -> None:
    """create_client wires ResolvedLLM into the OpenAI SDK client."""
    captured: dict[str, Any] = {}

    class SpyOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setattr("ai_study_assistant.llm.client.OpenAI", SpyOpenAI)
    create_client(_resolved(base_url="https://factory.test/v1", api_key="factory-key"))

    assert captured["api_key"] == "factory-key"
    assert captured["base_url"] == "https://factory.test/v1"


def test_generate_extracts_text_from_response() -> None:
    """The text content is pulled from choices[0].message.content."""
    fake = _make_fake_openai(content="hello world")
    client = OpenAICompatClient(_resolved(), client=fake)

    text = client.generate([Message(role="user", content="hi")])

    assert text == "hello world"


def test_generate_passes_messages_to_sdk() -> None:
    """Messages are converted to the role/content dict shape."""
    fake = _make_fake_openai(content="ok")
    client = OpenAICompatClient(_resolved(), client=fake)

    client.generate(
        [
            Message(role="system", content="you are a test"),
            Message(role="user", content="ping"),
        ]
    )

    call_args = fake.chat.completions.create.call_args
    messages = call_args.kwargs["messages"]
    assert messages == [
        {"role": "system", "content": "you are a test"},
        {"role": "user", "content": "ping"},
    ]


def test_generate_uses_resolved_defaults() -> None:
    """temperature and max_tokens default to the ResolvedLLM values."""
    fake = _make_fake_openai(content="ok")
    client = OpenAICompatClient(
        _resolved(model="resolved-model", temperature=0.5, max_tokens=256),
        client=fake,
    )

    client.generate([Message(role="user", content="hi")])

    kwargs = fake.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "resolved-model"
    assert kwargs["temperature"] == 0.5
    assert kwargs["max_tokens"] == 256


def test_generate_override_temperature() -> None:
    """generate(**overrides) can override temperature."""
    fake = _make_fake_openai(content="ok")
    client = OpenAICompatClient(_resolved(temperature=0.3), client=fake)

    client.generate([Message(role="user", content="hi")], temperature=0.9)

    kwargs = fake.chat.completions.create.call_args.kwargs
    assert kwargs["temperature"] == 0.9


def test_generate_override_model() -> None:
    """generate(**overrides) can override model."""
    fake = _make_fake_openai(content="ok")
    client = OpenAICompatClient(_resolved(model="default"), client=fake)

    client.generate([Message(role="user", content="hi")], model="deepseek-reasoner")

    kwargs = fake.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "deepseek-reasoner"


def test_authentication_error_mapping() -> None:
    """AuthenticationError is mapped to LLMAuthenticationError."""
    fake = MagicMock()
    fake.chat.completions.create.side_effect = AuthenticationError(
        "invalid key",
        response=MagicMock(),
        body=None,
    )
    client = OpenAICompatClient(_resolved(), client=fake)

    with pytest.raises(LLMAuthenticationError) as exc_info:
        client.generate([Message(role="user", content="hi")])

    assert "401" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_rate_limit_error_mapping() -> None:
    """RateLimitError is mapped to LLMRateLimitError."""
    fake = MagicMock()
    fake.chat.completions.create.side_effect = RateLimitError(
        "rate limited",
        response=MagicMock(),
        body=None,
    )
    client = OpenAICompatClient(_resolved(), client=fake)

    with pytest.raises(LLMRateLimitError) as exc_info:
        client.generate([Message(role="user", content="hi")])

    assert "429" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_connection_error_mapping() -> None:
    """APIConnectionError is mapped to LLMConnectionError."""
    fake = MagicMock()
    fake.chat.completions.create.side_effect = APIConnectionError(message="broken", request=MagicMock())
    client = OpenAICompatClient(_resolved(), client=fake)

    with pytest.raises(LLMConnectionError) as exc_info:
        client.generate([Message(role="user", content="hi")])

    assert "连接失败" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_timeout_error_mapping() -> None:
    """APITimeoutError is mapped to LLMTimeoutError."""
    fake = MagicMock()
    fake.chat.completions.create.side_effect = APITimeoutError(
        request=MagicMock()
    )
    client = OpenAICompatClient(_resolved(), client=fake)

    with pytest.raises(LLMTimeoutError) as exc_info:
        client.generate([Message(role="user", content="hi")])

    assert "超时" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None


def test_empty_response_raises_response_error() -> None:
    """A response with no choices raises LLMResponseError."""
    fake = MagicMock()
    fake_response = MagicMock()
    fake_response.choices = []
    fake.chat.completions.create.return_value = fake_response
    client = OpenAICompatClient(_resolved(), client=fake)

    with pytest.raises(LLMResponseError):
        client.generate([Message(role="user", content="hi")])


def test_empty_api_key_uses_placeholder(monkeypatch) -> None:
    """api_key='' is replaced by 'not-required' before instantiating the SDK."""
    captured: dict[str, Any] = {}

    class SpyOpenAI:
        def __init__(self, *, api_key: str, base_url: str) -> None:
            captured["api_key"] = api_key
            captured["base_url"] = base_url

    monkeypatch.setattr("ai_study_assistant.llm.client.OpenAI", SpyOpenAI)
    create_client(_resolved(api_key="", base_url="http://localhost:11434/v1"))

    assert captured["api_key"] == "not-required"
    assert captured["base_url"] == "http://localhost:11434/v1"


class FakeLLMClient:
    """A pure-Python fake showing that ``LLMClient`` can be mocked by protocol."""

    def __init__(self, canned: str) -> None:
        self.canned = canned

    def generate(self, messages: Sequence[Message], **overrides: Any) -> str:
        return self.canned


def test_protocol_can_be_mocked() -> None:
    """A plain Python class implementing ``generate`` satisfies ``LLMClient``."""
    fake: LLMClient = FakeLLMClient("protocol works")
    assert isinstance(fake, LLMClient)
    assert fake.generate([]) == "protocol works"


def test_api_status_error_carries_status_code() -> None:
    """Other HTTP errors map to LLMAPIError and preserve the status code."""
    fake = MagicMock()
    fake_response = MagicMock()
    fake_response.status_code = 500
    fake.chat.completions.create.side_effect = APIStatusError(
        message="server error",
        response=fake_response,
        body=None,
    )
    client = OpenAICompatClient(_resolved(), client=fake)

    with pytest.raises(LLMAPIError) as exc_info:
        client.generate([Message(role="user", content="hi")])

    assert exc_info.value.status_code == 500
    assert "500" in str(exc_info.value)
