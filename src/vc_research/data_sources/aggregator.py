"""数据聚合器 — 通过 DataSource 协议统一调度国内+海外数据源."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .base import DataSource


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
    """调度各数据源并合并结果.

    Phase 1: fixtures (FixturesSource)
    Phase 2: fixtures fallback + ITJuziSource + CrunchbaseSource

    数据合并规则:
        - fixtures 命中时一次性填充所有子字段 (与原行为一致)
        - 真实 API source 按 source.name 填到对应子字段 (itjuzi→raw.itjuzi 等)
        - 多源同时命中时,后注入的源不覆盖已有的非空字段
    """

    def __init__(
        self,
        use_fixtures: bool = True,
        fixtures_dir: str | None = None,
        sources: list[DataSource] | None = None,
    ):
        self.use_fixtures = use_fixtures
        self.fixtures_dir = fixtures_dir
        self._custom_sources = sources
        self._sources: list[DataSource] | None = None

    def _build_sources(self) -> list[DataSource]:
        if self._custom_sources is not None:
            return self._custom_sources
        if self.use_fixtures:
            from .fixtures_source import FixturesSource
            return [FixturesSource(self.fixtures_dir)]
        # Phase 2: itjuzi → crunchbase → fixtures fallback
        from .crunchbase_source import CrunchbaseSource
        from .fixtures_source import FixturesSource
        from .itjuzi_source import ITJuziSource
        return [
            ITJuziSource(),
            CrunchbaseSource(),
            FixturesSource(self.fixtures_dir),  # 最终兜底
        ]

    def fetch(self, company_name: str) -> RawCompanyData:
        data = RawCompanyData(name=company_name)
        if self._sources is None:
            self._sources = self._build_sources()

        for src in self._sources:
            payload = src.fetch(company_name)
            if not payload:
                continue
            self._merge(data, src.name, payload)

        return data

    @staticmethod
    def _merge(data: RawCompanyData, source_name: str, payload: dict) -> None:
        """把单个源的返回合并进 RawCompanyData.

        fixtures 返回聚合 dict (含多个子源);API source 返回单源 dict.
        """
        if source_name == "fixtures":
            # fixtures JSON 里直接带着 itjuzi/crunchbase/qichacha 子 key
            data.qichacha = data.qichacha or payload.get("qichacha")
            data.itjuzi = data.itjuzi or payload.get("itjuzi")
            data.crunchbase = data.crunchbase or payload.get("crunchbase")
            data.news_items = data.news_items or payload.get("news_items", [])
            hits = payload.get("sources_hit", [source_name])
            for h in hits:
                if h not in data.sources_hit:
                    data.sources_hit.append(h)
        else:
            # API source 整个 payload 对应一个子字段
            slot = getattr(data, source_name, None)
            if slot is None:
                setattr(data, source_name, payload)
                if source_name not in data.sources_hit:
                    data.sources_hit.append(source_name)
