"""LLM Provider 抽象层 — 统一接口支持 Claude/DeepSeek/GPT-4o/Qwen/Kimi."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


class LLMProviderError(RuntimeError):
    """LLM 提供商调用失败 — 调用方应降级或切换 provider."""


@runtime_checkable
class LLMProvider(Protocol):
    """通用 LLM 提供商协议.

    所有 provider (Anthropic / DeepSeek / OpenAI / Ollama / Kimi / Perplexity)
    实现此协议，上层代码通过 registry.get_provider() 获取实例。
    """

    name: str

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.35,
    ) -> str:
        """发送 system + user prompt，返回文本.

        Raises:
            LLMProviderError: API 调用失败 / 网络异常 / 认证错误
        """
        ...

    @property
    def available(self) -> bool:
        """该 provider 是否已配置可用 (API key 存在 / 服务可达)."""
        ...

    @property
    def model_id(self) -> str:
        """当前使用的模型标识符."""
        ...
