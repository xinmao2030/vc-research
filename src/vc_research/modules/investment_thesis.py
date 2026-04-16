"""模块 3: 投资依据 — 团队/市场/护城河/单位经济学/增长指标."""

from __future__ import annotations

from decimal import Decimal

from ..data_sources import RawCompanyData
from ..schema import (
    GrowthMetrics,
    InvestmentThesis,
    MarketSize,
    UnitEconomics,
)


def analyze_thesis(raw: RawCompanyData) -> InvestmentThesis:
    """构建投资逻辑.

    注意: 当前仅提取结构化数据,真正的 bull/bear 推理交给 LLM 层增强。
    """
    src = raw.itjuzi or raw.crunchbase or {}
    thesis_raw = src.get("thesis", {})

    market_raw = thesis_raw.get("market", {})
    market = MarketSize(
        tam_usd=_d(market_raw.get("tam_usd")),
        sam_usd=_d(market_raw.get("sam_usd")),
        som_usd=_d(market_raw.get("som_usd")),
        growth_rate=market_raw.get("growth_rate"),
    )

    ue_raw = thesis_raw.get("unit_economics", {})
    unit_econ = UnitEconomics(
        cac_usd=_d(ue_raw.get("cac_usd")),
        ltv_usd=_d(ue_raw.get("ltv_usd")),
        ltv_cac_ratio=_ratio(ue_raw.get("ltv_usd"), ue_raw.get("cac_usd")),
        gross_margin=ue_raw.get("gross_margin"),
        payback_months=ue_raw.get("payback_months"),
    )

    growth_raw = thesis_raw.get("growth", {})
    growth = GrowthMetrics(
        arr_usd=_d(growth_raw.get("arr_usd")),
        yoy_growth=growth_raw.get("yoy_growth"),
        mau=growth_raw.get("mau"),
        dau=growth_raw.get("dau"),
        gmv_usd=_d(growth_raw.get("gmv_usd")),
        retention_m12=growth_raw.get("retention_m12"),
    )

    return InvestmentThesis(
        team_score=thesis_raw.get("team_score", 6),
        team_notes=thesis_raw.get("team_notes", "团队背景待调研"),
        market=market,
        moat=thesis_raw.get("moat", "待识别"),
        unit_economics=unit_econ,
        growth=growth,
        competitors=thesis_raw.get("competitors", []),
        key_bull_points=thesis_raw.get("bull", []),
        key_bear_points=thesis_raw.get("bear", []),
    )


def _d(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (ValueError, ArithmeticError):
        return None


def _ratio(num, den) -> float | None:
    try:
        if num is None or den is None or float(den) == 0:
            return None
        return float(num) / float(den)
    except (TypeError, ValueError):
        return None
