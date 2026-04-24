"""Kimi (Moonshot AI) Provider — 128K 长上下文 + 中文金融数据."""

from __future__ import annotations

import os

from ..base import LLMProviderError
from ._openai_compat import openai_compatible_complete


DEFAULT_MODEL = "moonshot-v1-128k"
BASE_URL = "https://api.moonshot.cn/v1"


class KimiProvider:
    """Moonshot Kimi provider，OpenAI 兼容 API."""

    name = "kimi"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        self._api_key = api_key or os.getenv("KIMI_API_KEY", "")
        self._model = model

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.35,
    ) -> str:
        if not self._api_key:
            raise LLMProviderError("KIMI_API_KEY 未设置")
        return openai_compatible_complete(
            base_url=BASE_URL,
            api_key=self._api_key,
            model=self._model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_s=180,  # Kimi 长上下文可能较慢
            provider_name="kimi",
        )

    @property
    def available(self) -> bool:
        return bool(self._api_key or os.getenv("KIMI_API_KEY"))

    @property
    def model_id(self) -> str:
        return self._model
