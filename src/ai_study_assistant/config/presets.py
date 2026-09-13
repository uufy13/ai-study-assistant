"""Built-in provider presets.

Presets are pure data: switching providers means selecting a different entry,
not executing provider-specific logic.
"""

from .models import ProviderSpec

BUILTIN_PRESETS: dict[str, ProviderSpec] = {
    "deepseek": ProviderSpec(
        base_url="https://api.deepseek.com/v1",
        model="deepseek-chat",
        api_key_env="DEEPSEEK_API_KEY",
    ),
    "kimi": ProviderSpec(
        base_url="https://api.moonshot.cn/v1",
        model="moonshot-v1-8k",
        api_key_env="KIMI_API_KEY",
    ),
    "qwen": ProviderSpec(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        model="qwen-plus",
        api_key_env="QWEN_API_KEY",
    ),
    "openai": ProviderSpec(
        base_url="https://api.openai.com/v1",
        model="gpt-4o-mini",
        api_key_env="OPENAI_API_KEY",
    ),
    "ollama": ProviderSpec(
        base_url="http://localhost:11434/v1",
        model="qwen2.5",
        api_key_env=None,
    ),
}
