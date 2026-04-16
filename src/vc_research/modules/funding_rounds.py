"""模块 2: 融资轨迹 — 解析历史融资 + 估值曲线 + 稀释估算."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..data_sources import RawCompanyData
from ..schema import FundingHistory, FundingRound, FundingStage, Investor
from ..utils import parse_date, parse_funding_stage, to_decimal


# 稀释假设 (参考 AngelList / CB Insights 公开数据)
_DILUTION_PER_ROUND: dict[FundingStage, float] = {
    FundingStage.PRE_SEED: 0.10,
    FundingStage.SEED: 0.18,
    FundingStage.SERIES_A: 0.22,
    FundingStage.SERIES_B: 0.18,
    FundingStage.SERIES_C: 0.12,
    FundingStage.SERIES_D: 0.10,
    FundingStage.SERIES_E_PLUS: 0.08,
    FundingStage.PRE_IPO: 0.05,
    FundingStage.IPO: 0.15,
    FundingStage.STRATEGIC: 0.05,
    FundingStage.SECONDARY: 0.00,  # 二级/回购/介绍上市:股权转让,不稀释
}


def analyze_funding(raw: RawCompanyData) -> FundingHistory:
    """聚合融资数据.

    数据源优先级:
        IT桔子 (国内最全) > Crunchbase (海外) > 企查查 (工商变更推断)
    """
    src = raw.itjuzi or raw.crunchbase or {}
    rounds_raw = src.get("rounds") or []

    rounds: list[FundingRound] = []
    for r in rounds_raw:
        investor_details = [
            Investor(
                name=(i.get("name") or "").strip() or "未公开",
                type=i.get("type"),
                hq=i.get("hq"),
                aum_usd=to_decimal(i.get("aum_usd")),
                founded_year=i.get("founded_year"),
                sector_focus=i.get("sector_focus") or [],
                notable_portfolio=i.get("notable_portfolio") or [],
                deal_thesis=i.get("deal_thesis"),
                is_lead=bool(i.get("is_lead", False)),
            )
            for i in (r.get("investor_details") or [])
            if (i.get("name") or "").strip()
        ]
        rounds.append(
            FundingRound(
                stage=parse_funding_stage(r.get("stage")),
                announce_date=parse_date(r.get("announce_date")),
                amount_usd=to_decimal(r.get("amount_usd")),
                pre_money_valuation_usd=to_decimal(r.get("pre_money_valuation_usd")),
                post_money_valuation_usd=to_decimal(r.get("post_money_valuation_usd")),
                lead_investors=r.get("lead_investors") or [],
                participants=r.get("participants") or [],
                investor_details=investor_details,
                share_class=r.get("share_class"),
                use_of_proceeds=r.get("use_of_proceeds"),
                notes=r.get("notes"),
            )
        )

    rounds.sort(key=lambda r: r.announce_date or date.min)

    total = sum(
        (r.amount_usd for r in rounds if r.amount_usd is not None),
        start=Decimal(0),
    )
    latest = next(
        (
            r.post_money_valuation_usd
            for r in reversed(rounds)
            if r.post_money_valuation_usd
        ),
        None,
    )

    return FundingHistory(
        rounds=rounds,
        total_raised_usd=total if total else None,
        latest_valuation_usd=latest,
        valuation_cagr=_compute_cagr(rounds),
        dilution_estimate=_estimate_dilution(rounds),
    )


def _compute_cagr(rounds: list[FundingRound]) -> float | None:
    dated = [r for r in rounds if r.post_money_valuation_usd and r.announce_date]
    if len(dated) < 2:
        return None
    first, last = dated[0], dated[-1]
    years = (last.announce_date - first.announce_date).days / 365.25
    if years <= 0:
        return None
    try:
        ratio = float(last.post_money_valuation_usd / first.post_money_valuation_usd)
        return ratio ** (1 / years) - 1
    except (ZeroDivisionError, ArithmeticError):
        return None


def _estimate_dilution(rounds: list[FundingRound]) -> float | None:
    """粗略估算: 按轮次阶段的典型稀释比例累乘."""
    if not rounds:
        return None
    retention = 1.0
    for r in rounds:
        retention *= 1 - _DILUTION_PER_ROUND.get(r.stage, 0.15)
    return 1 - retention
