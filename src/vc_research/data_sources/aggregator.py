"""数据聚合器 — 统一封装国内+海外数据源."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RawCompanyData:
    """原始数据容器 — 多个数据源拉回来的原始 payload."""

    name: str
    sources_hit: list[str] = field(default_factory=list)
    qichacha: dict[str, Any] | None = None
    itjuzi: dict[str, Any] | None = None
    crunchbase: dict[str, Any] | None = None
    news_items: list[dict[str, Any]] = field(default_factory=list)
    patents: list[dict[str, Any]] = field(default_factory=list)
    job_postings: list[dict[str, Any]] = field(default_factory=list)

    def is_empty(self) -> bool:
        return not (self.qichacha or self.itjuzi or self.crunchbase)


class DataAggregator:
    """调度各数据源并聚合结果.

    Phase 1: 全部返回 None,走 fixtures 模式 (examples/ 下的静态 JSON)
    Phase 2: 接入真实 API
    """

    def __init__(self, use_fixtures: bool = True, fixtures_dir: str | None = None):
        self.use_fixtures = use_fixtures
        self.fixtures_dir = fixtures_dir

    def fetch(self, company_name: str) -> RawCompanyData:
        data = RawCompanyData(name=company_name)

        if self.use_fixtures:
            self._load_from_fixtures(company_name, data)
        else:
            # Phase 2: 并行调用各数据源
            # data.qichacha = qichacha_client.search(company_name)
            # data.itjuzi = itjuzi_client.search(company_name)
            # data.crunchbase = crunchbase_client.search(company_name)
            raise NotImplementedError(
                "真实数据源接入在 Phase 2, 当前请使用 use_fixtures=True"
            )

        return data

    def _load_from_fixtures(self, name: str, data: RawCompanyData) -> None:
        """从 examples/fixtures/{name}.json 加载静态数据."""
        import json
        from pathlib import Path

        base = Path(self.fixtures_dir) if self.fixtures_dir else (
            Path(__file__).resolve().parents[3] / "examples" / "fixtures"
        )
        candidate = base / f"{name}.json"
        if candidate.exists():
            payload = json.loads(candidate.read_text(encoding="utf-8"))
            data.qichacha = payload.get("qichacha")
            data.itjuzi = payload.get("itjuzi")
            data.crunchbase = payload.get("crunchbase")
            data.news_items = payload.get("news_items", [])
            data.sources_hit = payload.get("sources_hit", ["fixtures"])
