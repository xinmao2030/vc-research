"""模块 4: 产业趋势 — 赛道热度/Gartner 周期/政策/退出窗口."""

from __future__ import annotations

from decimal import Decimal

from ..data_sources import RawCompanyData
from ..schema import IndustryTrend


def analyze_industry(raw: RawCompanyData, industry: str) -> IndustryTrend:
    """聚合赛道级数据.

    TODO Phase 2: 接入清科/艾瑞/CB Insights 的赛道级聚合 API。
    """
    src = raw.itjuzi or raw.crunchbase or {}
    ind_raw = src.get("industry_data", {})

    return IndustryTrend(
        industry=industry,
        funding_total_12m_usd=_d(ind_raw.get("funding_total_12m_usd")),
        deal_count_12m=ind_raw.get("deal_count_12m"),
        gartner_phase=ind_raw.get("gartner_phase", "待定位"),
        policy_tailwinds=ind_raw.get("policy_tailwinds", []),
        policy_headwinds=ind_raw.get("policy_headwinds", []),
        exit_window=ind_raw.get("exit_window", "窗口情况待评估"),
        hot_keywords=ind_raw.get("hot_keywords", []),
    )


def _d(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (ValueError, ArithmeticError):
        return None
