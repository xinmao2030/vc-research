"""Perplexity Provider — 实时 Web 搜索 + 引用交叉验证."""

from __future__ import annotations

import json
import os
from urllib import error as urlerror
from urllib import request as urlrequest

from ..base import LLMProviderError


DEFAULT_MODEL = "sonar"
BASE_URL = "https://api.perplexity.ai"


class PerplexityProvider:
    """Perplexity Sonar provider，带引用的实时搜索增强 LLM."""

    name = "perplexity"

    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
    ):
        self._api_key = api_key or os.getenv("PERPLEXITY_API_KEY", "")
        self._model = model

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.35,
    ) -> str:
        text, _ = self.complete_with_citations(
            system, user, max_tokens=max_tokens, temperature=temperature
        )
        return text

    def complete_with_citations(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.35,
    ) -> tuple[str, list[str]]:
        """调用 Perplexity API，返回 (文本, 引用列表)."""
        if not self._api_key:
            raise LLMProviderError("PERPLEXITY_API_KEY 未设置")

        url = f"{BASE_URL}/chat/completions"
        body = json.dumps(
            {
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        ).encode("utf-8")

        req = urlrequest.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

        try:
            with urlrequest.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urlerror.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise LLMProviderError(
                f"Perplexity API HTTP {e.code}: {body_text}"
            ) from e
        except (urlerror.URLError, TimeoutError, OSError) as e:
            raise LLMProviderError(f"Perplexity 连接失败: {e}") from e

        choices = payload.get("choices", [])
        if not choices:
            raise LLMProviderError("Perplexity 返回空 choices")

        text = choices[0].get("message", {}).get("content", "")
        citations = payload.get("citations", [])
        return text, citations

    @property
    def available(self) -> bool:
        return bool(self._api_key or os.getenv("PERPLEXITY_API_KEY"))

    @property
    def model_id(self) -> str:
        return self._model
