"""数据采集层 — 统一接口 fetch_company(name) -> RawCompanyData."""

from .aggregator import DataAggregator, RawCompanyData

__all__ = ["DataAggregator", "RawCompanyData"]
