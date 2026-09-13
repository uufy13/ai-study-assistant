"""Configuration loading and merging."""

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from .models import AppConfig

DEFAULT_CONFIG_PATH = Path("config.yaml")
DEFAULT_ENV_PATH = Path(".env")


def load_config(config_path: str | os.PathLike[str] | None = None,
                env_path: str | os.PathLike[str] | None = None) -> AppConfig:
    """Load application configuration.

    Steps:
    1. Load ``.env`` if it exists (``env_path`` or ``.env`` in cwd).
    2. Load ``config.yaml`` if it exists (``config_path`` or ``config.yaml`` in cwd).
    3. Merge with builtin presets and validate via ``AppConfig``.

    Args:
        config_path: Optional explicit path to the YAML config file.
        env_path: Optional explicit path to the ``.env`` file.

    Returns:
        A validated and fully merged ``AppConfig``.
    """
    env_file = Path(env_path) if env_path is not None else DEFAULT_ENV_PATH
    if env_file.is_file():
        load_dotenv(dotenv_path=env_file, override=True)

    cfg_file = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    raw: dict[str, Any] = {}
    if cfg_file.is_file():
        with cfg_file.open("r", encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}

    # Merge partial user overrides with builtin presets so that e.g. only
    # changing ``model`` for a builtin provider is valid.
    from .presets import BUILTIN_PRESETS

    user_providers = raw.get("providers", {})
    for name, spec in user_providers.items():
        if name in BUILTIN_PRESETS:
            preset = BUILTIN_PRESETS[name].model_dump()
            merged = {**preset, **spec}
            user_providers[name] = merged

    return AppConfig.from_raw(raw)
