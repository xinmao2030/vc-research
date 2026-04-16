"""模块 5: 估值分析 — 4 种估值方法交叉验证."""

from __future__ import annotations

from decimal import Decimal
from statistics import mean

from ..schema import (
    FundingHistory,
    InvestmentThesis,
    Valuation,
    ValuationMethod,
)


def analyze_valuation(
    funding: FundingHistory,
    thesis: InvestmentThesis,
    comparable_multiples: dict[str, float] | None = None,
) -> Valuation:
    """用 4 种方法交叉估值,返回公允价值区间.

    Args:
        comparable_multiples: {"revenue": 15.0, "arr": 20.0, "gmv": 2.5}
                              赛道级同业估值倍数,Phase 2 从数据库拉取
    """
    methods: list[ValuationMethod] = []
    mults = comparable_multiples or _default_multiples(thesis)

    # 方法 1: 可比公司法 (P/Revenue or P/ARR)
    arr = thesis.growth.arr_usd
    if arr:
        low = arr * Decimal(mults["arr"] * 0.7)
        high = arr * Decimal(mults["arr"] * 1.3)
        methods.append(
            ValuationMethod(
                method="可比公司法 (P/ARR)",
                valuation_low_usd=low,
                valuation_high_usd=high,
                assumptions=f"ARR={arr}, 同业 P/ARR 中枢={mults['arr']}x, ±30% 区间",
            )
        )

    # 方法 2: GMV 倍数法 (适合电商/平台)
    gmv = thesis.growth.gmv_usd
    if gmv:
        low = gmv * Decimal(mults["gmv"] * 0.7)
        high = gmv * Decimal(mults["gmv"] * 1.3)
        methods.append(
            ValuationMethod(
                method="GMV 倍数法",
                valuation_low_usd=low,
                valuation_high_usd=high,
                assumptions=f"GMV={gmv}, 同业 P/GMV={mults['gmv']}x",
            )
        )

    # 方法 3: VC 逆推法 (基于 TAM + 市占率预期)
    tam = thesis.market.tam_usd
    if tam:
        target_share_low = Decimal("0.03")
        target_share_high = Decimal("0.10")
        exit_multiple = Decimal("5")  # 5x revenue at exit
        low = tam * target_share_low * exit_multiple * Decimal("0.3")  # VC 折现
        high = tam * target_share_high * exit_multiple * Decimal("0.5")
        methods.append(
            ValuationMethod(
                method="VC 逆推法 (TAM × 市占 × 退出倍数 × 风险折现)",
                valuation_low_usd=low,
                valuation_high_usd=high,
                assumptions=(
                    f"TAM={tam}, 目标市占 3-10%, 退出倍数 5x, "
                    f"风险折现 30-50%"
                ),
            )
        )

    # 方法 4: 最近一轮估值 (锚点)
    if funding.latest_valuation_usd:
        v = funding.latest_valuation_usd
        methods.append(
            ValuationMethod(
                method="最近一轮估值 (锚点)",
                valuation_low_usd=v * Decimal("0.8"),
                valuation_high_usd=v * Decimal("1.2"),
                assumptions="以最新一轮 post-money 为锚, ±20% 反映市场波动",
            )
        )

    # 汇总: 取各方法中点的均值作为公允价值中枢
    if methods:
        mids = [float((m.valuation_low_usd + m.valuation_high_usd) / 2) for m in methods]
        fair_mid = Decimal(mean(mids))
        fair_low = fair_mid * Decimal("0.75")
        fair_high = fair_mid * Decimal("1.25")
    else:
        # 极端 fallback: 无数据
        fair_low = Decimal(0)
        fair_high = Decimal(0)

    current = funding.latest_valuation_usd
    premium = None
    if current and fair_high > 0:
        fair_mid = (fair_low + fair_high) / 2
        if fair_mid > 0:
            premium = float((current - fair_mid) / fair_mid)

    return Valuation(
        methods=methods,
        fair_value_low_usd=fair_low,
        fair_value_high_usd=fair_high,
        current_valuation_usd=current,
        premium_discount=premium,
        sensitivity_notes=(
            "关键敏感性: ①TAM 估算误差 ±30% 可改变估值 50%; "
            "②同业倍数受市场情绪影响大,建议看赛道最近 6 月交易区间; "
            "③VC 逆推法中'目标市占'是最大变量,建议分 Bull/Base/Bear 三档。"
        ),
    )


def _default_multiples(thesis: InvestmentThesis) -> dict[str, float]:
    """根据行业选择默认估值倍数 (粗略,Phase 2 替换为赛道级动态数据)."""
    ind = thesis.competitors  # 用竞争对手作为 proxy
    # 默认 SaaS 倍数
    return {"revenue": 10.0, "arr": 15.0, "gmv": 2.0}
