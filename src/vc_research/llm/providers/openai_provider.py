"""OpenAI GPT-4o Provider — 海外公司分析 + 英文研报."""

from __future__ import annotations

import os

from ..base import LLMProviderError
from ._openai_compat import openai_compatible_complete


DEFAULT_MODEL = "gpt-4o"
BASE_URL = "https://api.openai.com/v1"


class OpenAIProvider:
    """OpenAI GPT 系列 provider."""

    name = "gpt4o"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        self._api_key = api_key or os.getenv("OPENAI_API_KEY", "")
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
            raise LLMProviderError("OPENAI_API_KEY 未设置")
        return openai_compatible_complete(
            base_url=BASE_URL,
            api_key=self._api_key,
            model=self._model,
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
            provider_name="openai",
        )

    @property
    def available(self) -> bool:
        return bool(self._api_key or os.getenv("OPENAI_API_KEY"))

    @property
    def model_id(self) -> str:
        return self._model
