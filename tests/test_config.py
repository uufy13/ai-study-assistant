"""Tests for the config module.

All 12 test cases from docs/config-module-design.md section 6 are covered here.
"""

import pytest
from pydantic import ValidationError

from ai_study_assistant.config import (
    BUILTIN_PRESETS,
    MissingAPIKeyError,
    UnknownProviderError,
    load_config,
)


# ---------------------------------------------------------------------------
# Case 1: minimal config loads and defaults are filled correctly
# ---------------------------------------------------------------------------
def test_minimal_config_loads_defaults(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("provider: deepseek\n")

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek")

    cfg = load_config(config_path=cfg_file)
    assert cfg.provider == "deepseek"
    assert cfg.llm.temperature == pytest.approx(0.3)
    assert cfg.llm.max_tokens is None

    resolved = cfg.resolve()
    assert resolved.base_url == "https://api.deepseek.com/v1"
    assert resolved.model == "deepseek-chat"
    assert resolved.api_key == "sk-deepseek"


# ---------------------------------------------------------------------------
# Case 2: builtin presets are complete and valid
# ---------------------------------------------------------------------------
def test_builtin_presets_complete():
    expected = {"deepseek", "kimi", "qwen", "openai", "ollama"}
    assert set(BUILTIN_PRESETS.keys()) == expected
    for name, spec in BUILTIN_PRESETS.items():
        assert spec.base_url.startswith(("http://", "https://"))
        assert spec.model
        if name != "ollama":
            assert spec.api_key_env


# ---------------------------------------------------------------------------
# Case 3: provider switching only changes the resolved provider
# ---------------------------------------------------------------------------
def test_provider_switching(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("provider: kimi\n")
    monkeypatch.setenv("KIMI_API_KEY", "sk-kimi")

    cfg = load_config(config_path=cfg_file)

    kimi = cfg.resolve("kimi")
    assert kimi.base_url == "https://api.moonshot.cn/v1"
    assert kimi.model == "moonshot-v1-8k"

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek")
    deepseek = cfg.resolve("deepseek")
    assert deepseek.base_url == "https://api.deepseek.com/v1"
    assert deepseek.model == "deepseek-chat"


# ---------------------------------------------------------------------------
# Case 4: api_key_env points to the correct env var value
# ---------------------------------------------------------------------------
def test_api_key_resolution(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("provider: qwen\n")
    monkeypatch.setenv("QWEN_API_KEY", "sk-qwen")

    cfg = load_config(config_path=cfg_file)
    resolved = cfg.resolve()
    assert resolved.api_key == "sk-qwen"


# ---------------------------------------------------------------------------
# Case 5: missing api key raises MissingAPIKeyError
# ---------------------------------------------------------------------------
def test_missing_api_key_raises(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("provider: openai\n")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    cfg = load_config(config_path=cfg_file)
    with pytest.raises(MissingAPIKeyError) as exc_info:
        cfg.resolve()
    assert "OPENAI_API_KEY" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Case 6: unknown provider raises UnknownProviderError
# ---------------------------------------------------------------------------
def test_unknown_provider_raises(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("provider: nonexistent\n")

    cfg = load_config(config_path=cfg_file)
    with pytest.raises(UnknownProviderError) as exc_info:
        cfg.resolve()
    assert "nonexistent" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Case 7: user overrides builtin preset fields
# ---------------------------------------------------------------------------
def test_user_override_builtin_model(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "provider: deepseek\n"
        "providers:\n"
        "  deepseek:\n"
        "    model: deepseek-reasoner\n"
    )
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-deepseek")

    cfg = load_config(config_path=cfg_file)
    resolved = cfg.resolve()
    assert resolved.model == "deepseek-reasoner"
    assert resolved.base_url == "https://api.deepseek.com/v1"


# ---------------------------------------------------------------------------
# Case 8: custom vendor can be used without a builtin preset
# ---------------------------------------------------------------------------
def test_custom_provider(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "provider: my_gateway\n"
        "providers:\n"
        "  my_gateway:\n"
        "    base_url: http://192.168.1.10:8000/v1\n"
        "    model: llama3\n"
        "    api_key_env: MY_GATEWAY_KEY\n"
    )
    monkeypatch.setenv("MY_GATEWAY_KEY", "sk-gateway")

    cfg = load_config(config_path=cfg_file)
    resolved = cfg.resolve()
    assert resolved.base_url == "http://192.168.1.10:8000/v1"
    assert resolved.model == "llama3"
    assert resolved.api_key == "sk-gateway"


# ---------------------------------------------------------------------------
# Case 9: ${VAR} placeholders are substituted from environment
# ---------------------------------------------------------------------------
def test_env_var_placeholder_substitution(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text(
        "provider: openai\n"
        "providers:\n"
        "  openai:\n"
        "    base_url: ${OPENAI_BASE_URL}\n"
        "    model: gpt-4o\n"
    )
    monkeypatch.setenv("OPENAI_BASE_URL", "https://proxy.example.com/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")

    cfg = load_config(config_path=cfg_file)
    resolved = cfg.resolve()
    assert resolved.base_url == "https://proxy.example.com/v1"


# ---------------------------------------------------------------------------
# Case 10: environment has highest priority (secrets come from .env, not YAML)
# ---------------------------------------------------------------------------
def test_env_file_supplies_api_key(tmp_path, monkeypatch):
    """密钥只能来自环境（.env 文件），体现 env 的最高优先级。

    同时覆盖 load_config 的 env_path 可注入参数（此前未测）。
    """
    env_file = tmp_path / ".env"
    env_file.write_text("OPENAI_API_KEY=sk-from-envfile\n")
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("provider: openai\n")

    # 先删除同名环境变量，隔离 load_dotenv 对 os.environ 的全局写入
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    cfg = load_config(config_path=cfg_file, env_path=env_file)
    resolved = cfg.resolve()
    assert resolved.api_key == "sk-from-envfile"


# ---------------------------------------------------------------------------
# Case 11: default provider falls back to openai
# ---------------------------------------------------------------------------
def test_default_provider_openai(tmp_path, monkeypatch):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("llm:\n  temperature: 0.5\n")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")

    cfg = load_config(config_path=cfg_file)
    assert cfg.provider == "openai"
    resolved = cfg.resolve()
    assert resolved.base_url == "https://api.openai.com/v1"
    assert resolved.model == "gpt-4o-mini"
    assert resolved.temperature == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# Case 12: invalid values raise ValidationError
# ---------------------------------------------------------------------------
def test_invalid_temperature_raises_validation(tmp_path):
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("llm:\n  temperature: not-a-number\n")

    with pytest.raises(ValidationError):
        load_config(config_path=cfg_file)


def test_ollama_does_not_require_key(tmp_path):
    """Local Ollama preset works without any API key."""
    cfg_file = tmp_path / "config.yaml"
    cfg_file.write_text("provider: ollama\n")

    cfg = load_config(config_path=cfg_file)
    resolved = cfg.resolve()
    assert resolved.base_url == "http://localhost:11434/v1"
    assert resolved.model == "qwen2.5"
    assert resolved.api_key == ""
