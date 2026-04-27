"""模块 8: VC 机构格局分析 — 从融资轮次中提取投资方画像,分析投资方阵容质量."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from ..data_sources import RawCompanyData
from ..schema import (
    FundingHistory,
    PortfolioCompany,
    VCFundProfile,
    VCLandscape,
)
from ..utils import to_decimal


# ── 知名机构标签 (用于打分) ──────────────────────────────
_TIER1_VCS = {
    # 中国
    "红杉中国", "红杉资本中国", "Sequoia China", "红杉",
    "高瓴", "高瓴资本", "Hillhouse", "Hillhouse Capital",
    "IDG资本", "IDG Capital",
    "经纬创投", "经纬中国", "Matrix Partners China",
    "GGV纪源资本", "GGV Capital",
    "真格基金", "ZhenFund",
    "光速中国", "Lightspeed China",
    "云锋基金", "Yunfeng Capital",
    "腾讯投资", "Tencent",
    "阿里巴巴", "Alibaba",
    "字节跳动", "ByteDance",
    "源码资本", "Source Code Capital",
    "五源资本", "5Y Capital",
    "启明创投", "Qiming Venture",
    "北极光创投", "Northern Light VC",
    "晨兴资本", "Morningside",
    "鼎晖投资", "CDH Investments",
    "华平投资", "Warburg Pincus",
    "春华资本", "Primavera Capital",
    "中金资本", "CICC Capital",
    # 美国/全球
    "Sequoia Capital", "a16z", "Andreessen Horowitz",
    "Benchmark", "Accel", "Lightspeed",
    "Tiger Global", "Coatue", "SoftBank", "软银",
    "General Atlantic", "KKR", "TPG",
    "Insight Partners", "Greylock", "NEA",
    "Bessemer", "GGV", "DST Global",
    "Founders Fund", "Y Combinator", "YC",
    "Kleiner Perkins", "IVP",
}

_TIER1_LOWER = {n.lower() for n in _TIER1_VCS}


def analyze_vc_landscape(
    raw: RawCompanyData,
    funding: FundingHistory,
) -> VCLandscape:
    """从融资轮次中提取 VC 画像并分析投资方格局."""
    company_name = raw.name

    # 1. 收集所有投资方
    investor_map: dict[str, VCFundProfile] = {}
    investor_round_count: Counter[str] = Counter()

    for rnd in funding.rounds:
        # 优先用 investor_details (结构化数据)
        if rnd.investor_details:
            for inv in rnd.investor_details:
                name = inv.name.strip()
                if not name or name == "未公开":
                    continue
                investor_round_count[name] += 1
                if name not in investor_map:
                    investor_map[name] = VCFundProfile(
                        name=name,
                        type=inv.type or "VC",
                        hq=inv.hq,
                        aum_usd=inv.aum_usd,
                        founded_year=inv.founded_year,
                        sector_focus=inv.sector_focus,
                        one_liner=inv.deal_thesis or "",
                    )
        # 退化: 只有名字列表
        all_names = set(rnd.lead_investors + rnd.participants)
        for name in all_names:
            name = name.strip()
            if not name or name == "未公开":
                continue
            if name not in investor_map:
                investor_map[name] = VCFundProfile(
                    name=name,
                    type="VC",
                    one_liner="",
                )
            if name not in investor_round_count:
                investor_round_count[name] += 1

    investors = list(investor_map.values())

    # 2. 从 raw data 补充 peer investors (同赛道未参投的知名 VC)
    peer_investors = _extract_peer_investors(raw, investor_map)

    # 3. 投资方质量评分
    score, notes = _score_investor_quality(investors, funding)

    # 4. 投资组合模式
    syndicate = _analyze_syndicate(funding, investor_round_count)

    # 5. 追加投资可能性
    follow_on = _assess_follow_on(investor_round_count, investors)

    return VCLandscape(
        target_company=company_name,
        investors_involved=investors,
        peer_investors=peer_investors,
        investor_quality_score=score,
        investor_quality_notes=notes,
        syndicate_pattern=syndicate,
        follow_on_likelihood=follow_on,
    )


def _extract_peer_investors(
    raw: RawCompanyData,
    existing: dict[str, VCFundProfile],
) -> list[VCFundProfile]:
    """从竞品数据中提取同赛道活跃但未参投的 VC."""
    src = raw.itjuzi or raw.crunchbase or {}
    competitors = src.get("competitors", [])
    peer_names: set[str] = set()

    for comp in competitors:
        if isinstance(comp, dict):
            for inv_name in comp.get("investors", []):
                if isinstance(inv_name, str) and inv_name not in existing:
                    peer_names.add(inv_name.strip())

    return [
        VCFundProfile(name=n, type="VC", one_liner="同赛道活跃投资方")
        for n in sorted(peer_names)[:10]
    ]


def _score_investor_quality(
    investors: list[VCFundProfile],
    funding: FundingHistory,
) -> tuple[float, str]:
    """投资方阵容质量评分 (0-10)."""
    if not investors:
        return 0.0, "无已知投资方信息"

    score = 0.0
    reasons: list[str] = []

    # 维度 1: 知名 VC 数量 (0-4 分)
    tier1_count = sum(
        1 for inv in investors if inv.name.lower() in _TIER1_LOWER
    )
    tier1_names = [inv.name for inv in investors if inv.name.lower() in _TIER1_LOWER]
    dim1 = min(tier1_count * 1.0, 4.0)
    score += dim1
    if tier1_names:
        reasons.append(f"头部机构 ({', '.join(tier1_names[:5])})")
    else:
        reasons.append("无头部 VC 参与")

    # 维度 2: 投资方多样性 (0-2 分)
    types = {inv.type for inv in investors if inv.type}
    dim2 = min(len(types) * 0.5, 2.0)
    score += dim2
    if len(types) >= 3:
        reasons.append(f"投资方类型多元 ({', '.join(sorted(types))})")

    # 维度 3: 总融资规模 (0-2 分)
    total = funding.total_raised_usd or Decimal(0)
    if total >= 500_000_000:
        score += 2.0
        reasons.append("融资总额超 5 亿美元")
    elif total >= 100_000_000:
        score += 1.5
        reasons.append("融资总额超 1 亿美元")
    elif total >= 30_000_000:
        score += 1.0
        reasons.append("融资总额超 3000 万美元")
    elif total > 0:
        score += 0.5

    # 维度 4: 轮次数量 / 成熟度 (0-2 分)
    round_count = len(funding.rounds)
    dim4 = min(round_count * 0.4, 2.0)
    score += dim4
    if round_count >= 4:
        reasons.append(f"经历 {round_count} 轮融资,机构认可度高")

    score = min(score, 10.0)
    notes = "；".join(reasons) if reasons else "数据不足"
    return round(score, 1), notes


def _analyze_syndicate(
    funding: FundingHistory,
    investor_counts: Counter[str],
) -> str:
    """分析投资组合模式."""
    if not funding.rounds:
        return "数据不足"

    # 统计每轮参与方数量
    avg_participants = sum(
        len(r.lead_investors) + len(r.participants) for r in funding.rounds
    ) / len(funding.rounds)

    # 是否有战投主导
    has_strategic = any(
        r for r in funding.rounds
        if any(
            inv.type and "战投" in inv.type
            for inv in (r.investor_details or [])
        )
    )

    # 重复投资方
    repeat_investors = [name for name, cnt in investor_counts.items() if cnt >= 2]

    if has_strategic:
        return "战投主导型 — 产业资本深度参与"
    if avg_participants <= 2:
        return "集中型 — 每轮投资方少,关系紧密"
    if repeat_investors:
        return f"跟投型 — {', '.join(repeat_investors[:3])} 多轮追加"
    return "分散型 — 每轮投资方较多,syndicate 广泛"


def _assess_follow_on(
    investor_counts: Counter[str],
    investors: list[VCFundProfile],
) -> str:
    """评估现有投资方追加投资的可能性."""
    repeat = [name for name, cnt in investor_counts.items() if cnt >= 2]
    tier1_involved = any(inv.name.lower() in _TIER1_LOWER for inv in investors)

    if repeat and tier1_involved:
        return "高 — 头部 VC 已多轮追投,后续跟投意愿强"
    if repeat:
        return "中高 — 已有投资方多轮追投"
    if tier1_involved:
        return "中 — 有头部机构参与,但尚未追投"
    if investors:
        return "中低 — 投资方知名度一般,追投不确定"
    return "低 — 投资方信息不足"
