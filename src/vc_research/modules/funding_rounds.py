"""模块 2: 融资轨迹 — 解析历史融资 + 估值曲线 + 稀释估算."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from ..data_sources import RawCompanyData
from ..schema import FundingHistory, FundingRound, FundingStage


_STAGE_ALIAS = {
    "天使": FundingStage.SEED,
    "种子": FundingStage.SEED,
    "pre-a": FundingStage.SEED,
    "a": FundingStage.SERIES_A,
    "a+": FundingStage.SERIES_A,
    "b": FundingStage.SERIES_B,
    "b+": FundingStage.SERIES_B,
    "c": FundingStage.SERIES_C,
    "d": FundingStage.SERIES_D,
    "e": FundingStage.SERIES_E_PLUS,
    "f": FundingStage.SERIES_E_PLUS,
    "pre-ipo": FundingStage.PRE_IPO,
    "ipo": FundingStage.IPO,
    "战略": FundingStage.STRATEGIC,
    "strategic": FundingStage.STRATEGIC,
}


def analyze_funding(raw: RawCompanyData) -> FundingHistory:
    """聚合融资数据.

    数据源优先级:
        IT桔子 (国内最全) > Crunchbase (海外) > 企查查 (工商变更推断)
    """
    src = raw.itjuzi or raw.crunchbase or {}
    rounds_raw = src.get("rounds", [])

    rounds: list[FundingRound] = []
    for r in rounds_raw:
        stage = _parse_stage(r.get("stage", ""))
        announce = _parse_date(r.get("announce_date"))
        rounds.append(
            FundingRound(
                stage=stage,
                announce_date=announce,
                amount_usd=_to_decimal(r.get("amount_usd")),
                post_money_valuation_usd=_to_decimal(r.get("post_money_valuation_usd")),
                lead_investors=r.get("lead_investors", []),
                participants=r.get("participants", []),
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


def _parse_stage(raw_stage: str) -> FundingStage:
    key = raw_stage.strip().lower().replace("轮", "").replace("series ", "")
    return _STAGE_ALIAS.get(key, FundingStage.SEED)


def _parse_date(val) -> date | None:
    if not val:
        return None
    if isinstance(val, date):
        return val
    try:
        return date.fromisoformat(str(val))
    except (ValueError, TypeError):
        return None


def _to_decimal(val) -> Decimal | None:
    if val is None:
        return None
    try:
        return Decimal(str(val))
    except (ValueError, ArithmeticError):
        return None


def _compute_cagr(rounds: list[FundingRound]) -> float | None:
    dated = [
        r for r in rounds if r.post_money_valuation_usd and r.announce_date
    ]
    if len(dated) < 2:
        return None
    first, last = dated[0], dated[-1]
    years = (last.announce_date - first.announce_date).days / 365.25
    if years <= 0:
        return None
    ratio = float(last.post_money_valuation_usd / first.post_money_valuation_usd)
    return ratio ** (1 / years) - 1


def _estimate_dilution(rounds: list[FundingRound]) -> float | None:
    """粗略估算: 假设每轮稀释 15-25%,按轮次数累乘."""
    if not rounds:
        return None
    retention = 1.0
    for r in rounds:
        retention *= 1 - _dilution_per_round(r.stage)
    return 1 - retention


def _dilution_per_round(stage: FundingStage) -> float:
    table = {
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
    }
    return table.get(stage, 0.15)
