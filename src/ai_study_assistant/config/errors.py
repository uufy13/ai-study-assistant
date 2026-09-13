"""Configuration-related exceptions."""


class ConfigError(Exception):
    """Base class for configuration errors."""


class MissingAPIKeyError(ConfigError):
    """Raised when a provider requires an API key but the env var is unset."""


class UnknownProviderError(ConfigError):
    """Raised when the requested provider is not builtin nor defined in config."""
