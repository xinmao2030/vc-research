"""港交所披露易数据源 — Phase 2.1 最简实现.

限制说明:
    - HKEX 无官方 JSON API (要 Market Data Services 付费订阅)
    - www1.hkexnews.hk 的搜索页面 JS 动态渲染,静态抓取拿不到有效数据
    - 因此本 Phase 只维护一份手工 symbology 表 + 标准披露 URL 构造器
    - 未来 Phase 2.2 可接入 AAStocks / Yahoo HK 等三方汇总源

对上层的价值:
    - 快速确认 fixture 声称的港股代码 (如 小米=01810.HK) 是否合法
    - 提供招股章程/年报的标准 URL 拼接 (虽然需手工找 accession code)
"""

from __future__ import annotations

from typing import Any

# 公司中文名 → 港股代码 (5 位,含前导 0)
_HK_TICKER_BY_NAME: dict[str, str] = {
    "小米": "01810",
    "小米集团": "01810",
    "Xiaomi": "01810",
    "蔚来": "09866",
    "NIO": "09866",
    "百济神州": "06160",
    "BeiGene": "06160",
    "BeOne Medicines": "06160",
    "商汤科技": "00020",
    "商汤": "00020",
    "SenseTime": "00020",
    "阿里巴巴": "09988",
    "Alibaba": "09988",
    "京东集团": "09618",
    "JD": "09618",
    "腾讯": "00700",
    "Tencent": "00700",
    "美团": "03690",
    "快手": "01024",
}


class HkexSource:
    """港交所上市公司元数据 (静态)."""

    name = "hkex"
    provenance = "港交所披露易 · 静态 symbology"

    BASE_PROFILE = "https://www.hkexnews.hk/index_es.htm?stockcode={ticker}"
    BASE_SEARCH = (
        "https://www1.hkexnews.hk/search/titlesearch.xhtml?"
        "lang=zh&category=0&market=SEHK&stockId={ticker}"
    )

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        ticker = _HK_TICKER_BY_NAME.get(company_name)
        if not ticker:
            return None
        return {
            "hk_ticker": ticker,
            "hk_ticker_full": f"{ticker}.HK",
            "hkex_profile_url": self.BASE_PROFILE.format(ticker=ticker),
            "hkex_search_url": self.BASE_SEARCH.format(ticker=ticker),
            "notes": (
                "Phase 2.1 静态 symbology — 后续接入 HKEX 搜索 API 后自动补披露文档"
            ),
        }


def lookup_hk_ticker(company_name: str) -> str | None:
    """供 cross_verify 直接查询,不走完整 DataSource 流."""
    return _HK_TICKER_BY_NAME.get(company_name)
