"""模块 4: 产业趋势 — 赛道热度/Gartner 周期/政策/退出窗口 + 细分赛道 + 产业链 + 头部玩家."""

from __future__ import annotations

from ..data_sources import RawCompanyData
from ..schema import Competitor, IndustryTrend, SubSegment, ValueChain
from ..utils import to_decimal


def analyze_industry(raw: RawCompanyData, industry: str) -> IndustryTrend:
    """聚合赛道级数据.

    TODO Phase 2: 接入清科/艾瑞/CB Insights 的赛道级聚合 API。
    """
    src = raw.itjuzi or raw.crunchbase or {}
    ind_raw = src.get("industry_data") or {}

    sub_segments = [
        SubSegment(
            name=(s.get("name") or "").strip(),
            size_usd=to_decimal(s.get("size_usd")),
            growth_rate=s.get("growth_rate"),
            notes=s.get("notes"),
        )
        for s in (ind_raw.get("sub_segments") or [])
        if (s.get("name") or "").strip()
    ]

    value_chain = _parse_value_chain(ind_raw.get("value_chain"))

    top_players = [
        Competitor(
            name=(p.get("name") or "").strip() or "未公开",
            hq=p.get("hq"),
            stage_or_status=p.get("stage_or_status"),
            valuation_usd=to_decimal(p.get("valuation_usd")),
            market_share_pct=p.get("market_share_pct"),
            differentiator=p.get("differentiator"),
            threat_level=p.get("threat_level"),
        )
        for p in (ind_raw.get("top_players") or [])
        if (p.get("name") or "").strip()
    ]

    raw_metrics = ind_raw.get("industry_key_metrics") or {}
    industry_key_metrics = {
        str(k): str(v)
        for k, v in raw_metrics.items()
        if k and v is not None
    } if isinstance(raw_metrics, dict) else {}

    return IndustryTrend(
        industry=industry,
        funding_total_12m_usd=to_decimal(ind_raw.get("funding_total_12m_usd")),
        deal_count_12m=ind_raw.get("deal_count_12m"),
        gartner_phase=ind_raw.get("gartner_phase") or "待定位",
        policy_tailwinds=ind_raw.get("policy_tailwinds") or [],
        policy_headwinds=ind_raw.get("policy_headwinds") or [],
        exit_window=ind_raw.get("exit_window") or "窗口情况待评估",
        hot_keywords=ind_raw.get("hot_keywords") or [],
        sub_segments=sub_segments,
        value_chain=value_chain,
        top_players=top_players,
        growth_drivers=[
            str(d).strip() for d in (ind_raw.get("growth_drivers") or []) if d
        ],
        barriers_to_entry=[
            str(b).strip() for b in (ind_raw.get("barriers_to_entry") or []) if b
        ],
        industry_key_metrics=industry_key_metrics,
    )


def _parse_value_chain(raw_vc: dict | None) -> ValueChain | None:
    if not raw_vc or not isinstance(raw_vc, dict):
        return None
    upstream = [str(x).strip() for x in (raw_vc.get("upstream") or []) if x]
    midstream = [str(x).strip() for x in (raw_vc.get("midstream") or []) if x]
    downstream = [str(x).strip() for x in (raw_vc.get("downstream") or []) if x]
    if not (upstream or midstream or downstream):
        return None
    return ValueChain(
        upstream=upstream, midstream=midstream, downstream=downstream
    )
