"""数据采集层 — 统一接口 fetch_company(name) -> RawCompanyData."""

from .aggregator import DataAggregator, RawCompanyData
from .base import DataSource
from .fixtures_source import FixturesSource
from .hkex_source import HkexSource, lookup_hk_ticker
from .ollama_researcher import OllamaResearcher
from .sec_edgar_source import SecEdgarSource
from .web_verifier import VerificationReport, VerifyStatus, WebVerifier

__all__ = [
    "DataAggregator",
    "RawCompanyData",
    "DataSource",
    "FixturesSource",
    "HkexSource",
    "OllamaResearcher",
    "SecEdgarSource",
    "VerificationReport",
    "VerifyStatus",
    "WebVerifier",
    "lookup_hk_ticker",
]
