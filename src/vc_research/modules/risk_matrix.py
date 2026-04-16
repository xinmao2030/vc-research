"""模块 6: 风险矩阵 — 市场/技术/团队/监管/现金流/退出 6 类风险."""

from __future__ import annotations

from decimal import Decimal

from ..data_sources import RawCompanyData
from ..schema import (
    FundingHistory,
    InvestmentThesis,
    Risk,
    RiskLevel,
    RiskMatrix,
)


def analyze_risks(
    raw: RawCompanyData,
    funding: FundingHistory,
    thesis: InvestmentThesis,
) -> RiskMatrix:
    src = raw.itjuzi or raw.crunchbase or {}
    fin = src.get("financials", {})

    burn = _d(fin.get("burn_rate_usd_monthly"))
    cash = _d(fin.get("cash_usd"))
    runway = None
    if burn and cash and burn > 0:
        runway = float(cash / burn)

    risks: list[Risk] = []

    # 现金流风险
    if runway is not None:
        if runway < 6:
            lvl = RiskLevel.CRITICAL
        elif runway < 12:
            lvl = RiskLevel.HIGH
        elif runway < 18:
            lvl = RiskLevel.MEDIUM
        else:
            lvl = RiskLevel.LOW
        risks.append(
            Risk(
                category="现金流",
                description=f"现金跑道约 {runway:.1f} 个月",
                level=lvl,
                mitigation="建议 12 个月内完成下一轮融资或实现盈亏平衡",
            )
        )

    # 团队风险
    if thesis.team_score <= 5:
        risks.append(
            Risk(
                category="团队",
                description=f"团队评分 {thesis.team_score}/10,存在能力或完整性短板",
                level=RiskLevel.HIGH,
                mitigation="补强高管团队,引入行业资深人才",
            )
        )

    # 市场风险 (TAM 过小)
    if thesis.market.tam_usd and thesis.market.tam_usd < Decimal("1e9"):
        risks.append(
            Risk(
                category="市场",
                description="TAM < $1B,天花板可能限制退出估值",
                level=RiskLevel.MEDIUM,
                mitigation="拓展邻近场景或出海寻找增量",
            )
        )

    # 单位经济学风险
    if (
        thesis.unit_economics.ltv_cac_ratio is not None
        and thesis.unit_economics.ltv_cac_ratio < 3
    ):
        risks.append(
            Risk(
                category="商业模式",
                description=f"LTV/CAC = {thesis.unit_economics.ltv_cac_ratio:.1f},低于健康阈值 3.0",
                level=RiskLevel.HIGH,
                mitigation="降低获客成本或提升 LTV (续费/扩展销售)",
            )
        )

    # 稀释风险
    if funding.dilution_estimate and funding.dilution_estimate > 0.7:
        risks.append(
            Risk(
                category="股权结构",
                description=f"创始团队累计稀释约 {funding.dilution_estimate:.0%},激励可能不足",
                level=RiskLevel.MEDIUM,
                mitigation="通过 ESOP 补充或设置 founder top-up",
            )
        )

    # 外部明示的额外风险
    for extra in src.get("extra_risks", []):
        risks.append(
            Risk(
                category=extra.get("category", "其他"),
                description=extra.get("description", ""),
                level=RiskLevel(extra.get("level", "medium")),
                mitigation=extra.get("mitigation"),
            )
        )

    overall = _overall_level(risks)

    return RiskMatrix(
        burn_rate_usd_monthly=burn,
        cash_usd=cash,
        runway_months=runway,
        risks=risks,
        overall_level=overall,
    )


def _d(v) -> Decimal | None:
    if v is None:
        return None
    try:
        return Decimal(str(v))
    except (ValueError, ArithmeticError):
        return None


def _overall_level(risks: list[Risk]) -> RiskLevel:
    order = [RiskLevel.LOW, RiskLevel.MEDIUM, RiskLevel.HIGH, RiskLevel.CRITICAL]
    if not risks:
        return RiskLevel.LOW
    return max(risks, key=lambda r: order.index(r.level)).level
