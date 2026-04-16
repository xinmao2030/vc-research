"""IT桔子数据源 — 国内创投数据最全 (Phase 2 接入).

当前: 骨架 + NotImplementedError,保证接口兼容.
Phase 2 真实接入时:
    - 需要 ITJUZI_API_KEY (在 .env)
    - POST https://api.itjuzi.com/... 按公司名搜索
    - 返回字段映射到 fixtures 的 itjuzi 子对象结构
"""

from __future__ import annotations

import os
from typing import Any


class ITJuziSource:
    """IT桔子 API 客户端骨架."""

    name = "itjuzi"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ITJUZI_API_KEY")

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        raise NotImplementedError(
            "IT桔子 API 接入在 Phase 2. "
            "参考 docs/architecture.md 的 4.3 节实现 search()."
        )
