"""模块 7: 投资建议 — 汇总前 6 个模块,给出投资逻辑/定价/条款/退出."""

from __future__ import annotations

from decimal import Decimal

from ..schema import (
    CompanyProfile,
    FundingHistory,
    FundingStage,
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
    profile: CompanyProfile | None = None,
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

    terms = _suggest_terms(risks, funding, profile, thesis)
    logic = _compose_logic(thesis, valuation, risks, verdict)
    exits = _suggest_exits(profile, funding, valuation, thesis)

    return Recommendation(
        verdict=verdict,
        target_entry_valuation_usd=target,
        suggested_terms=terms,
        investment_logic=logic,
        exit_scenarios=exits,
    )


def _verdict_from_score(score: float) -> str:
    if score >= 70:
        return "强烈参投"
    if score >= 55:
        return "参投"
    if score >= 40:
        return "观望"
    return "回避"


# ────────────────────────────────────────────────────────────
# 建议条款 — 根据企业真实情况定制
# ────────────────────────────────────────────────────────────
def _suggest_terms(
    risks: RiskMatrix,
    funding: FundingHistory,
    profile: CompanyProfile | None,
    thesis: InvestmentThesis,
) -> list[str]:
    name = profile.name if profile else "标的公司"
    industry = (profile.industry or "") if profile else ""
    stage = profile.stage if profile else None
    biz = (profile.business_model or "") if profile else ""

    terms: list[str] = []

    # --- 1) 清算权: 根据行业和阶段调整 ---
    if stage in (FundingStage.IPO, FundingStage.SECONDARY):
        terms.append(
            f"优先清算权 1x non-participating（{name}已上市,"
            "清算保护条款可适当简化,重点关注锁定期安排和减持节奏）"
        )
    elif stage in (FundingStage.SERIES_D, FundingStage.SERIES_E_PLUS, FundingStage.PRE_IPO):
        terms.append(
            f"优先清算权 1x non-participating（{name}处于后期轮次,"
            "建议搭配 pay-to-play 条款防止已有投资人弃轮稀释）"
        )
    else:
        terms.append("优先清算权 1x non-participating（早期轮次标准保护）")

    # --- 2) 反稀释: 根据估值溢价调整 ---
    if valuation_is_aggressive(thesis, funding):
        terms.append(
            f"全棘轮反稀释保护 (full ratchet)（{name}本轮估值较高,"
            "下行场景需强保护;可设日落条款:IPO 或下一轮上估值自动失效）"
        )
    else:
        terms.append(
            "加权平均反稀释保护 (broad-based weighted average)"
            "（估值区间合理,标准条款即可）"
        )

    # --- 3) 对赌/里程碑: 根据风险因子定制 ---
    risk_names = [r.category for r in risks.risks] if risks.risks else []
    if "regulatory" in risk_names or "政策" in str(risk_names):
        terms.append(
            f"监管里程碑对赌:约定{name}须在 [X] 个月内取得关键资质/牌照/批件,"
            "未达则触发估值回调或追加股权补偿"
        )
    if "技术" in str(risk_names) or "product" in str(risk_names):
        terms.append(
            f"产品里程碑对赌:约定{name}核心产品/管线须在 [X] 个月内达到"
            "指定阶段（如临床 III 期入组/量产/GMV 目标），未达触发估值调整"
        )
    if risks.overall_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
        if not any("对赌" in t for t in terms):
            terms.append(
                f"综合业绩对赌:约定{name}未来 12-18 个月关键 KPI"
                "（如收入/用户/毛利率），未达触发估值回调"
            )

    # --- 4) 行业特定条款 ---
    ind_lower = industry.lower()
    if "医药" in ind_lower or "biotech" in ind_lower or "pharma" in ind_lower:
        terms.append(
            f"临床失败保护条款:若{name}核心管线关键临床试验未达主要终点,"
            "投资人有权要求按约定估值回购或追加补偿股权"
        )
    elif "半导体" in ind_lower or "芯片" in ind_lower:
        terms.append(
            f"技术授权与 IP 保护:确认{name}核心 IP 归属清晰,"
            "无重大专利诉讼风险;约定关键技术人员竞业禁止及 IP 转让限制"
        )
    elif "硬件" in ind_lower or "iot" in ind_lower:
        terms.append(
            f"供应链集中度条款:要求{name}关键零部件不得单一供应商依赖度超过 50%,"
            "或提供替代供应商切换方案"
        )

    # --- 5) 稀释保护 ---
    if funding.dilution_estimate and funding.dilution_estimate > 0.6:
        terms.append(
            f"要求{name}预留 ESOP 不低于 10%,"
            "绑定核心团队（创始人 + 关键技术/业务负责人），"
            "离职加速归属条款须经投资人同意"
        )

    # --- 6) 治理条款: 根据阶段 ---
    if stage in (FundingStage.SEED, FundingStage.SERIES_A):
        terms.append(f"董事会观察员席位 + 重大事项一票否决权（{name}早期阶段,加强治理参与）")
    elif stage in (FundingStage.SERIES_B, FundingStage.SERIES_C, FundingStage.SERIES_D):
        terms.append(f"董事席位 + 关键事项（融资/并购/关联交易）需投资人多数同意")
    else:
        terms.append(f"信息权:季度经审财务报表 + 年度审计 + 关键事项实时知情（{name}已上市可依赖公开披露补充）")

    # --- 7) 跟投/优先认购权 ---
    terms.append(
        f"后续轮次优先认购权 (pro-rata right):确保在{name}后续融资中"
        "有权按比例跟投,防止被动稀释"
    )

    return terms


def valuation_is_aggressive(thesis: InvestmentThesis, funding: FundingHistory) -> bool:
    """判断当前估值是否偏高 — 用于决定反稀释条款强度."""
    if funding.rounds:
        last = funding.rounds[-1]
        prev = funding.rounds[-2] if len(funding.rounds) >= 2 else None
        if prev and last.post_money_valuation_usd and prev.post_money_valuation_usd:
            step_up = float(last.post_money_valuation_usd) / float(prev.post_money_valuation_usd)
            if step_up > 5:
                return True
    if thesis.market.tam_usd and thesis.market.som_usd:
        if float(thesis.market.som_usd) / float(thesis.market.tam_usd) < 0.01:
            return True
    return False


# ────────────────────────────────────────────────────────────
# 退出情景 — 根据企业真实情况定制
# ────────────────────────────────────────────────────────────
def _suggest_exits(
    profile: CompanyProfile | None,
    funding: FundingHistory,
    valuation: Valuation,
    thesis: InvestmentThesis,
) -> list[str]:
    name = profile.name if profile else "标的公司"
    industry = (profile.industry or "") if profile else ""
    stage = profile.stage if profile else None
    biz = (profile.business_model or "") if profile else ""
    products = [p.name for p in (profile.products_detailed or [])] if profile else []
    product_str = "、".join(products[:3]) if products else "核心产品"
    competitors = thesis.competitors[:3] if thesis.competitors else []
    comp_str = "、".join(competitors) if competitors else "同业龙头"

    exits: list[str] = []
    ind_lower = industry.lower()

    # --- IPO 退出 ---
    if stage == FundingStage.IPO:
        # 已经上市 → 退出方式是二级市场减持
        latest = funding.rounds[-1] if funding.rounds else None
        exchange = _infer_exchange(name, funding)
        exits.append(
            f"二级市场退出:{name}已在{exchange}上市,"
            f"建议锁定期满后分批减持（单日不超过日均成交量 15%），"
            f"预计退出周期 6-18 个月"
        )
    elif stage in (FundingStage.PRE_IPO, FundingStage.SERIES_D, FundingStage.SERIES_E_PLUS):
        exits.append(
            f"IPO 退出:{name}已进入 Pre-IPO 阶段,"
            f"预计 12-24 个月内可申报上市（科创板/港交所 18A/纳斯达克）,"
            f"以{product_str}的商业化进展为上市核心卖点"
        )
    else:
        exits.append(
            f"IPO 退出:{name}尚处早期，"
            f"若未来 3-5 年{product_str}验证 PMF 且收入规模达标，"
            f"可冲刺 A 股科创板或港股 18A/18C"
        )

    # --- 战略并购退出 ---
    if "医药" in ind_lower or "biotech" in ind_lower:
        exits.append(
            f"战略并购/License-out:{name}核心管线可授权给跨国药企"
            f"（如辉瑞/罗氏/阿斯利康/百济神州）获得 upfront + milestone + royalty,"
            f"或被{comp_str}等整体收购"
        )
    elif "半导体" in ind_lower or "芯片" in ind_lower:
        exits.append(
            f"产业并购:{name}在{product_str}领域的技术积累对"
            f"{comp_str}等巨头具有战略价值，"
            f"可能触发产业整合型收购（参考近年半导体并购潮）"
        )
    elif "硬件" in ind_lower or "iot" in ind_lower or "消费" in ind_lower:
        exits.append(
            f"战略收购:{name}的{product_str}产品线及全球渠道"
            f"对{comp_str}等行业玩家有整合价值，"
            f"或吸引科技巨头（苹果/谷歌/华为）进行品类扩张收购"
        )
    else:
        exits.append(
            f"战略并购:同业龙头或跨界巨头可能基于{product_str}"
            f"的技术/渠道/客户资产发起收购"
        )

    # --- 老股转让/回购退出 ---
    if stage == FundingStage.IPO:
        exits.append(
            f"大宗交易/协议转让:对{name}股权的机构投资人可通过"
            f"大宗交易平台或协议转让方式退出,避免冲击二级市场价格"
        )
    else:
        if funding.rounds and len(funding.rounds) >= 3:
            exits.append(
                f"老股转让 (Secondary):{name}已完成 {len(funding.rounds)} 轮融资,"
                f"早期投资人可在后续轮次中向新进投资人转让部分老股，"
                f"实现部分退出和流动性管理"
            )
        else:
            exits.append(
                f"回购/老股转让:在{name}后续融资中，"
                f"新投资人或管理层可回购早期股权提供流动性"
            )

    # --- 行业特定补充退出 ---
    if "saas" in biz.lower() or "订阅" in biz:
        exits.append(
            f"PE 接盘:若{name}ARR 增速放缓但现金流稳健,"
            f"可引入 PE 基金（如 Thoma Bravo/Vista Equity 或国内同类）"
            f"进行杠杆收购,投资人通过 PE recap 退出"
        )

    return exits


def _infer_exchange(name: str, funding: FundingHistory) -> str:
    """从融资轮次备注中推断上市交易所."""
    # 汇总所有轮次的备注 + 投资方名称
    parts: list[str] = []
    for r in (funding.rounds or []):
        if r.notes:
            parts.append(r.notes)
        parts.extend(r.lead_investors)
        parts.extend(r.participants)
    combined = " ".join(parts).lower()

    if "科创板" in combined or "上交所" in combined or ".sh" in combined or "688" in combined:
        return "上交所科创板"
    if "创业板" in combined or "深交所" in combined or ".sz" in combined:
        return "深交所创业板"
    if "港交所" in combined or "hkex" in combined or "18a" in combined or ".hk" in combined:
        return "港交所"
    if "纳斯达克" in combined or "nasdaq" in combined:
        return "纳斯达克"
    if "nyse" in combined or "纽交所" in combined:
        return "纽交所"
    return "资本市场"


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
