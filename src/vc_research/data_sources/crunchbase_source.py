"""Crunchbase 数据源 — 海外创投标配 (Phase 2 接入).

当前: 骨架 + NotImplementedError.
Phase 2 真实接入时:
    - 需要 CRUNCHBASE_API_KEY (在 .env)
    - GET https://api.crunchbase.com/api/v4/entities/organizations/...
    - 返回字段映射到 fixtures 的 crunchbase 子对象结构
"""

from __future__ import annotations

import os
from typing import Any


class CrunchbaseSource:
    """Crunchbase API 客户端骨架."""

    name = "crunchbase"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CRUNCHBASE_API_KEY")

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        if not self.api_key:
            return None
        raise NotImplementedError(
            "Crunchbase API 接入在 Phase 2. "
            "参考 docs/architecture.md 的 4.3 节实现 search()."
        )
