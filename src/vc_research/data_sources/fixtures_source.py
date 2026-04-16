"""Fixtures 数据源 — 从 examples/fixtures/{name}.json 读静态数据.

Phase 1 默认数据源. Phase 2 仍保留用于离线测试和 CI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class FixturesSource:
    """从本地 JSON 文件读数据."""

    name = "fixtures"

    def __init__(self, fixtures_dir: str | Path | None = None):
        if fixtures_dir:
            self.base = Path(fixtures_dir)
        else:
            self.base = (
                Path(__file__).resolve().parents[3] / "examples" / "fixtures"
            )

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        candidate = self.base / f"{company_name}.json"
        if not candidate.exists():
            return None
        return json.loads(candidate.read_text(encoding="utf-8"))
