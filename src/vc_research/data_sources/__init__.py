"""数据采集层 — 统一接口 fetch_company(name) -> RawCompanyData."""

from .aggregator import DataAggregator, RawCompanyData
from .base import DataSource
from .fixtures_source import FixturesSource

__all__ = ["DataAggregator", "RawCompanyData", "DataSource", "FixturesSource"]
