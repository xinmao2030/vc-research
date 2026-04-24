"""LLM Provider 注册表 — 自动发现 + 按名选择 + 优先级降级."""

from __future__ import annotations

import logging
import os

from .base import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)

# 优先级顺序：Claude > DeepSeek > GPT-4o > Kimi > Perplexity > Ollama
PROVIDER_PRIORITY = ["claude", "deepseek", "gpt4o", "kimi", "perplexity", "ollama"]


def _create_provider(name: str) -> LLMProvider:
    """按名称实例化 provider (延迟导入避免循环依赖)."""
    if name == "claude":
        from .providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider()
    elif name == "deepseek":
        from .providers.deepseek_provider import DeepSeekProvider
        return DeepSeekProvider()
    elif name == "gpt4o":
        from .providers.openai_provider import OpenAIProvider
        return OpenAIProvider()
    elif name == "kimi":
        from .providers.kimi_provider import KimiProvider
        return KimiProvider()
    elif name == "perplexity":
        from .providers.perplexity_provider import PerplexityProvider
        return PerplexityProvider()
    elif name == "ollama":
        from .providers.ollama_provider import OllamaProvider
        return OllamaProvider()
    else:
        raise LLMProviderError(f"未知 provider: {name}，可选: {', '.join(PROVIDER_PRIORITY)}")


def get_provider(name: str | None = None) -> LLMProvider:
    """获取 LLM provider.

    优先级:
        1. 显式指定 name
        2. VC_LLM_PROVIDER 环境变量
        3. 自动选择第一个 available 的 provider

    Raises:
        LLMProviderError: 没有可用的 provider
    """
    # 显式指定
    if name and name != "auto":
        provider = _create_provider(name)
        if not provider.available:
            logger.warning(
                "指定的 provider '%s' 不可用，尝试自动降级", name
            )
        else:
            return provider

    # 环境变量
    env_name = os.getenv("VC_LLM_PROVIDER", "").strip().lower()
    if env_name and env_name != "auto":
        try:
            provider = _create_provider(env_name)
            if provider.available:
                return provider
            logger.warning("VC_LLM_PROVIDER=%s 不可用，自动降级", env_name)
        except LLMProviderError:
            logger.warning("VC_LLM_PROVIDER=%s 无效", env_name)

    # 自动选择
    for pname in PROVIDER_PRIORITY:
        try:
            provider = _create_provider(pname)
            if provider.available:
                logger.info("自动选择 LLM provider: %s (%s)", pname, provider.model_id)
                return provider
        except LLMProviderError:
            continue

    raise LLMProviderError(
        "没有可用的 LLM provider。请设置以下任一 API key:\n"
        "  ANTHROPIC_API_KEY / DEEPSEEK_API_KEY / OPENAI_API_KEY / "
        "KIMI_API_KEY / PERPLEXITY_API_KEY\n"
        "或启动本地 Ollama: ollama serve"
    )


def list_providers() -> list[dict[str, str | bool]]:
    """列出所有已注册的 provider 及其可用状态."""
    result = []
    for pname in PROVIDER_PRIORITY:
        try:
            provider = _create_provider(pname)
            result.append({
                "name": pname,
                "model": provider.model_id,
                "available": provider.available,
            })
        except LLMProviderError:
            result.append({
                "name": pname,
                "model": "N/A",
                "available": False,
            })
    return result
