"""模块 7: 投资建议 — 汇总前 6 个模块,给出投资逻辑/定价/条款/退出."""

from __future__ import annotations

from decimal import Decimal

from ..schema import (
    FundingHistory,
    InvestmentThesis,
    Recommendation,
    RiskLevel,
    RiskMatrix,
    Valuation,
)


def analyze_recommendation(
    thesis: InvestmentThesis,
    valuation: Valuation,
    risks: RiskMatrix,
    funding: FundingHistory,
) -> Recommendation:
    """综合评分 → 投资裁决.

    评分规则 (Phase 1 简化版,Phase 3 让 LLM 增强):
        team (1-10) + market + moat + unit_econ + risk_penalty
    """
    score = 0

    # 团队 (权重 25%)
    score += thesis.team_score * 2.5

    # 市场 (权重 20%) — TAM 规模
    if thesis.market.tam_usd:
        tam = float(thesis.market.tam_usd)
        if tam >= 1e11:
            score += 20
        elif tam >= 1e10:
            score += 15
        elif tam >= 1e9:
            score += 10
        else:
            score += 5

    # 护城河 (权重 15%)
    moat_score = 8 if len(thesis.moat) > 20 else 5
    score += moat_score * 1.5

    # 单位经济学 (权重 15%)
    ratio = thesis.unit_economics.ltv_cac_ratio or 0
    if ratio >= 3:
        score += 15
    elif ratio >= 1:
        score += 8
    else:
        score += 3

    # 估值性价比 (权重 15%)
    if valuation.premium_discount is not None:
        pd = valuation.premium_discount
        if pd <= -0.2:
            score += 15
        elif pd <= 0.2:
            score += 10
        elif pd <= 0.5:
            score += 5

    # 风险扣分 (权重 -10%)
    penalty = {
        RiskLevel.LOW: 0,
        RiskLevel.MEDIUM: 3,
        RiskLevel.HIGH: 7,
        RiskLevel.CRITICAL: 12,
    }[risks.overall_level]
    score -= penalty

    verdict = _verdict_from_score(score)

    # 目标入场估值: 公允中枢的 70% (留安全边际)
    mid = (valuation.fair_value_low_usd + valuation.fair_value_high_usd) / 2
    target = mid * Decimal("0.7") if mid > 0 else None

    terms = _suggest_terms(risks, funding)

    logic = _compose_logic(thesis, valuation, risks, verdict)

    exits = [
        "IPO: 若 ARR > $100M 且毛利率 > 70%,3-5 年内可冲刺美股/港股",
        "战略并购: 同业龙头或跨界巨头(腾讯/字节/阿里)出手收购",
        "回购/老股转让: 下一轮投资人或 SPV 接盘,保证流动性",
    ]

    return Recommendation(
        verdict=verdict,
        target_entry_valuation_usd=target,
        suggested_terms=terms,
        investment_logic=logic,
        exit_scenarios=exits,
    )


def _verdict_from_score(score: float) -> str:
    if score >= 70:
        return "强烈推荐"
    if score >= 55:
        return "推荐"
    if score >= 40:
        return "观望"
    return "回避"


def _suggest_terms(risks: RiskMatrix, funding: FundingHistory) -> list[str]:
    terms = [
        "优先清算权 1x non-participating",
        "基于业绩的反稀释保护 (broad-based weighted average)",
    ]
    if risks.overall_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        terms.append("对赌条款: 约定关键里程碑,未达则触发估值调整")
    if funding.dilution_estimate and funding.dilution_estimate > 0.6:
        terms.append("要求预留 ESOP 不低于 10%,激励创始团队")
    terms.append("董事会观察员席位(A 轮) / 董事席位(B 轮起)")
    terms.append("信息权: 季度财报 + 年度审计 + 关键事项知情权")
    return terms


def _compose_logic(
    thesis: InvestmentThesis,
    valuation: Valuation,
    risks: RiskMatrix,
    verdict: str,
) -> str:
    bull = "、".join(thesis.key_bull_points[:3]) or "待 LLM 层生成"
    bear = "、".join(thesis.key_bear_points[:2]) or "待 LLM 层生成"
    return (
        f"【投资裁决: {verdict}】"
        f"核心看多: {bull}。"
        f"主要风险: {bear},整体风险等级 {risks.overall_level.value}。"
        f"估值判断: 公允区间 ${valuation.fair_value_low_usd:,.0f} - "
        f"${valuation.fair_value_high_usd:,.0f}。"
    )
