"""模块 3: 投资依据 — 团队/市场/护城河/单位经济学/增长指标."""

from __future__ import annotations

from ..data_sources import RawCompanyData
from ..schema import (
    Competitor,
    GrowthMetrics,
    InvestmentThesis,
    MarketSize,
    MoatAnalysis,
    MoatDimension,
    ThesisPoint,
    UnitEconomics,
)
from ..utils import to_decimal


_MOAT_DIMS = (
    "network_effect",
    "scale_economy",
    "switching_cost",
    "brand",
    "counter_positioning",
    "cornered_resource",
    "process_power",
)


def analyze_thesis(raw: RawCompanyData) -> InvestmentThesis:
    """构建投资逻辑.

    注意: 当前仅提取结构化数据,真正的 bull/bear 推理交给 LLM 层增强。
    """
    src = raw.itjuzi or raw.crunchbase or {}
    thesis_raw = src.get("thesis") or {}

    market_raw = thesis_raw.get("market") or {}
    market = MarketSize(
        tam_usd=to_decimal(market_raw.get("tam_usd")),
        sam_usd=to_decimal(market_raw.get("sam_usd")),
        som_usd=to_decimal(market_raw.get("som_usd")),
        growth_rate=market_raw.get("growth_rate"),
    )

    ue_raw = thesis_raw.get("unit_economics") or {}
    unit_econ = UnitEconomics(
        cac_usd=to_decimal(ue_raw.get("cac_usd")),
        ltv_usd=to_decimal(ue_raw.get("ltv_usd")),
        ltv_cac_ratio=_ratio(ue_raw.get("ltv_usd"), ue_raw.get("cac_usd")),
        gross_margin=ue_raw.get("gross_margin"),
        payback_months=ue_raw.get("payback_months"),
    )

    growth_raw = thesis_raw.get("growth") or {}
    growth = GrowthMetrics(
        arr_usd=to_decimal(growth_raw.get("arr_usd")),
        yoy_growth=growth_raw.get("yoy_growth"),
        mau=growth_raw.get("mau"),
        dau=growth_raw.get("dau"),
        gmv_usd=to_decimal(growth_raw.get("gmv_usd")),
        retention_m12=growth_raw.get("retention_m12"),
    )

    competitors_detailed = [
        Competitor(
            name=(c.get("name") or "").strip() or "未公开",
            hq=c.get("hq"),
            stage_or_status=c.get("stage_or_status"),
            valuation_usd=to_decimal(c.get("valuation_usd")),
            market_share_pct=c.get("market_share_pct"),
            differentiator=c.get("differentiator"),
            threat_level=c.get("threat_level"),
        )
        for c in (thesis_raw.get("competitors_detailed") or [])
        if (c.get("name") or "").strip()
    ]

    moat_analysis = _parse_moat(thesis_raw.get("moat_analysis"))

    bull_detailed = _parse_thesis_points(thesis_raw.get("bull_detailed"))
    bear_detailed = _parse_thesis_points(thesis_raw.get("bear_detailed"))

    return InvestmentThesis(
        team_score=thesis_raw.get("team_score", 6),
        team_notes=thesis_raw.get("team_notes") or "团队背景待调研",
        team_analysis=thesis_raw.get("team_analysis"),
        market=market,
        market_analysis=thesis_raw.get("market_analysis"),
        moat=thesis_raw.get("moat") or "待识别",
        moat_analysis=moat_analysis,
        unit_economics=unit_econ,
        unit_economics_analysis=thesis_raw.get("unit_economics_analysis"),
        growth=growth,
        growth_analysis=thesis_raw.get("growth_analysis"),
        competitors=thesis_raw.get("competitors") or [],
        competitors_detailed=competitors_detailed,
        key_bull_points=thesis_raw.get("bull") or [],
        key_bull_points_detailed=bull_detailed,
        key_bear_points=thesis_raw.get("bear") or [],
        key_bear_points_detailed=bear_detailed,
    )


def _parse_moat(raw_moat: dict | None) -> MoatAnalysis | None:
    if not raw_moat or not isinstance(raw_moat, dict):
        return None
    kwargs: dict = {}
    any_present = False
    for dim in _MOAT_DIMS:
        entry = raw_moat.get(dim)
        if not entry or not isinstance(entry, dict):
            continue
        score = entry.get("score")
        evidence = entry.get("evidence")
        if score is None and not evidence:
            continue
        try:
            score_int = max(0, min(10, int(score if score is not None else 0)))
        except (TypeError, ValueError):
            score_int = 0
        kwargs[dim] = MoatDimension(
            score=score_int, evidence=str(evidence or "").strip()
        )
        any_present = True
    return MoatAnalysis(**kwargs) if any_present else None


def _parse_thesis_points(raw_list: list | None) -> list[ThesisPoint]:
    if not raw_list:
        return []
    out: list[ThesisPoint] = []
    for p in raw_list:
        if not isinstance(p, dict):
            continue
        headline = (p.get("headline") or "").strip()
        if not headline:
            continue
        out.append(
            ThesisPoint(
                headline=headline,
                analysis=(p.get("analysis") or "").strip(),
                evidence=[str(e) for e in (p.get("evidence") or []) if e],
            )
        )
    return out


def _ratio(num, den) -> float | None:
    try:
        if num is None or den is None or float(den) == 0:
            return None
        return float(num) / float(den)
    except (TypeError, ValueError):
        return None
