"""Ollama 本地 Provider — 零成本离线兜底."""

from __future__ import annotations

import json
import logging
import os
from urllib import error as urlerror
from urllib import request as urlrequest

from ..base import LLMProviderError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "qwen3:8b"
DEFAULT_URL = "http://localhost:11434"
DEFAULT_TIMEOUT_S = 600


class OllamaProvider:
    """Ollama 本地推理 provider，通过 /api/generate 端点通信."""

    name = "ollama"

    def __init__(
        self,
        model: str | None = None,
        base_url: str | None = None,
        timeout_s: int = DEFAULT_TIMEOUT_S,
    ):
        self._model = model or os.getenv("OLLAMA_MODEL", DEFAULT_MODEL)
        self._base_url = (
            base_url or os.getenv("OLLAMA_URL", DEFAULT_URL)
        ).rstrip("/")
        self._timeout_s = timeout_s

    def complete(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 8192,
        temperature: float = 0.35,
    ) -> str:
        prompt = f"{system}\n\n{user}"
        body = json.dumps(
            {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }
        ).encode("utf-8")

        req = urlrequest.Request(
            f"{self._base_url}/api/generate",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlrequest.urlopen(req, timeout=self._timeout_s) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except (urlerror.URLError, TimeoutError, OSError) as e:
            raise LLMProviderError(f"Ollama 连接失败: {e}") from e
        except json.JSONDecodeError as e:
            raise LLMProviderError(f"Ollama 响应非 JSON: {e}") from e

        text = payload.get("response", "")
        if not text:
            raise LLMProviderError("Ollama 返回空响应")
        return text

    @property
    def available(self) -> bool:
        """检测 Ollama 服务是否可达 (快速 HEAD 请求)."""
        try:
            req = urlrequest.Request(self._base_url, method="HEAD")
            with urlrequest.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    @property
    def model_id(self) -> str:
        return self._model
