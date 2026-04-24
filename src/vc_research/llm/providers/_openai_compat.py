"""OpenAI 兼容 API 共享实现 — DeepSeek / GPT-4o / Kimi / Perplexity 共用."""

from __future__ import annotations

import json
import logging
from urllib import error as urlerror
from urllib import request as urlrequest

from ..base import LLMProviderError

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT_S = 120


def openai_compatible_complete(
    base_url: str,
    api_key: str,
    model: str,
    system: str,
    user: str,
    *,
    max_tokens: int = 4096,
    temperature: float = 0.35,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    provider_name: str = "openai-compat",
) -> str:
    """调用 OpenAI 兼容的 chat/completions 端点.

    DeepSeek / GPT-4o / Kimi / Perplexity 都走这个。
    用 stdlib urllib 避免额外依赖。
    """
    url = f"{base_url.rstrip('/')}/chat/completions"
    body = json.dumps(
        {
            "model": model,
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
            "Authorization": f"Bearer {api_key}",
        },
    )

    try:
        with urlrequest.urlopen(req, timeout=timeout_s) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urlerror.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode("utf-8", errors="replace")[:500]
        except Exception:
            pass
        raise LLMProviderError(
            f"{provider_name} API HTTP {e.code}: {body_text}"
        ) from e
    except (urlerror.URLError, TimeoutError, OSError) as e:
        raise LLMProviderError(
            f"{provider_name} 连接失败: {e}"
        ) from e

    choices = payload.get("choices", [])
    if not choices:
        raise LLMProviderError(
            f"{provider_name} 返回空 choices: {json.dumps(payload, ensure_ascii=False)[:300]}"
        )
    return choices[0].get("message", {}).get("content", "")
