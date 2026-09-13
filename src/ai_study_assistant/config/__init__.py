"""Config module public API.

The config layer is vendor-agnostic: ``BUILTIN_PRESETS`` supplies curated
defaults, and ``AppConfig.resolve()`` returns a provider-agnostic ``ResolvedLLM``
that the ``llm`` module can use directly.
"""

from .errors import ConfigError, MissingAPIKeyError, UnknownProviderError
from .loader import load_config
from .models import AppConfig, LLMParams, ProviderSpec, ResolvedLLM
from .presets import BUILTIN_PRESETS

__all__ = [
    "BUILTIN_PRESETS",
    "AppConfig",
    "ConfigError",
    "LLMParams",
    "MissingAPIKeyError",
    "ProviderSpec",
    "ResolvedLLM",
    "UnknownProviderError",
    "load_config",
]
