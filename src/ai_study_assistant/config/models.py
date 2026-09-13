"""Pydantic data models for the config module."""

import os
from typing import Any

from pydantic import BaseModel, Field

from .errors import MissingAPIKeyError, UnknownProviderError


class LLMParams(BaseModel):
    """Generation parameters shared across all providers."""

    temperature: float = 0.3
    max_tokens: int | None = None


class ProviderSpec(BaseModel):
    """Endpoint configuration for an OpenAI-compatible provider."""

    base_url: str
    model: str
    api_key_env: str | None = None


class ResolvedLLM(BaseModel):
    """Fully resolved configuration ready for the llm module."""

    base_url: str
    api_key: str
    model: str
    temperature: float
    max_tokens: int | None = None


class AppConfig(BaseModel):
    """Top-level application configuration."""

    provider: str = "openai"
    llm: LLMParams = Field(default_factory=LLMParams)
    providers: dict[str, ProviderSpec] = Field(default_factory=dict)

    def resolve(self, name: str | None = None) -> ResolvedLLM:
        """Resolve the named (or default) provider to a fully populated config.

        The lookup is data-driven: ``self.providers`` overrides builtin presets,
        and the resulting ``ProviderSpec`` is merged with global ``llm`` params.
        """
        from .presets import BUILTIN_PRESETS

        provider_name = name if name is not None else self.provider

        if provider_name in self.providers:
            spec = self.providers[provider_name]
        elif provider_name in BUILTIN_PRESETS:
            spec = BUILTIN_PRESETS[provider_name]
        else:
            raise UnknownProviderError(
                f"Unknown provider '{provider_name}'. "
                f"Define it under 'providers' or use one of: "
                f"{', '.join(sorted(BUILTIN_PRESETS.keys()))}."
            )

        if spec.api_key_env is not None:
            api_key = os.getenv(spec.api_key_env, "")
            if not api_key:
                raise MissingAPIKeyError(
                    f"Provider '{provider_name}' requires the environment variable "
                    f"'{spec.api_key_env}' to be set."
                )
        else:
            api_key = ""

        return ResolvedLLM(
            base_url=spec.base_url,
            api_key=api_key,
            model=spec.model,
            temperature=self.llm.temperature,
            max_tokens=self.llm.max_tokens,
        )

    @classmethod
    def _substitute_env_vars(cls, value: Any) -> Any:
        """Recursively replace ``${VAR}`` placeholders with environment values."""
        if isinstance(value, str):
            result = value
            # Simple linear scan for ${...} placeholders.
            while True:
                start = result.find("${")
                if start == -1:
                    break
                end = result.find("}", start + 2)
                if end == -1:
                    break
                var_name = result[start + 2 : end]
                replacement = os.getenv(var_name, "")
                result = result[:start] + replacement + result[end + 1 :]
            return result
        if isinstance(value, dict):
            return {k: cls._substitute_env_vars(v) for k, v in value.items()}
        if isinstance(value, list):
            return [cls._substitute_env_vars(item) for item in value]
        return value

    @classmethod
    def from_raw(cls, raw: dict[str, Any]) -> "AppConfig":
        """Build an ``AppConfig`` after applying environment substitution."""
        substituted = cls._substitute_env_vars(raw)
        return cls.model_validate(substituted)
