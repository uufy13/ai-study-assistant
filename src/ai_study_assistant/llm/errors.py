"""Domain-level exceptions for the LLM module.

These exceptions intentionally do not depend on the OpenAI SDK, keeping the
error surface vendor-neutral for upstream consumers (pipeline).
"""


class LLMError(Exception):
    """Base class for all LLM-related errors."""


class LLMAuthenticationError(LLMError):
    """Authentication failed (e.g. invalid or expired API key)."""


class LLMRateLimitError(LLMError):
    """Rate limit or quota exceeded."""


class LLMConnectionError(LLMError):
    """Network or connection failure."""


class LLMTimeoutError(LLMError):
    """Request timed out."""


class LLMAPIError(LLMError):
    """Other HTTP 4xx/5xx error from the upstream API.

    Attributes:
        status_code: The HTTP status code returned by the API, if available.
    """

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class LLMResponseError(LLMError):
    """Malformed or missing response content (e.g. no choices)."""


class LLMConfigurationError(LLMError):
    """Invalid or incomplete configuration preventing a request."""
