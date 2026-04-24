"""Anthropic Claude Provider — 支持 prompt caching."""

from __future__ import annotations

import os

from ..base import LLMProviderError


DEFAULT_MODEL = "claude-opus-4-6"


class AnthropicProvider:
    """Claude 系列模型 provider，封装 anthropic SDK."""

    name = "claude"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        self._api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self._model = model
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from anthropic import Anthropic
        except ImportError:
            raise LLMProviderError(
                "anthropic SDK 未安装，请 `uv add anthropic`"
            )
        if not self._api_key:
            raise LLMProviderError("ANTHROPIC_API_KEY 未设置")
        self._client = Anthropic(api_key=self._api_key)
        return self._client

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.35,
    ) -> str:
        client = self._get_client()
        try:
            response = client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=[
                    {
                        "type": "text",
                        "text": system,
                        "cache_control": {"type": "ephemeral"},
                    },
                ],
                messages=[{"role": "user", "content": user}],
            )
        except Exception as e:
            raise LLMProviderError(f"Claude API 调用失败: {e}") from e
        return "".join(b.text for b in response.content if b.type == "text")

    @property
    def available(self) -> bool:
        return bool(self._api_key or os.getenv("ANTHROPIC_API_KEY"))

    @property
    def model_id(self) -> str:
        return self._model
