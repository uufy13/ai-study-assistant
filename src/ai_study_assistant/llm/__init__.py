"""Public surface of the LLM module."""

from .client import LLMClient, Message, OpenAICompatClient, create_client
from .errors import (
    LLMAPIError,
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)

__all__ = [
    "LLMAPIError",
    "LLMAuthenticationError",
    "LLMClient",
    "LLMConfigurationError",
    "LLMConnectionError",
    "LLMError",
    "LLMRateLimitError",
    "LLMResponseError",
    "LLMTimeoutError",
    "Message",
    "OpenAICompatClient",
    "create_client",
]
