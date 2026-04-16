"""模块 1: 企业画像 — 从原始数据构建 CompanyProfile."""

from __future__ import annotations

from ..data_sources import RawCompanyData
from ..schema import CompanyProfile, Executive, Founder, Milestone, Region
from ..utils import parse_date, parse_funding_stage


class InsufficientDataError(ValueError):
    """原始数据为空,无法构建有效画像."""


def analyze_profile(raw: RawCompanyData) -> CompanyProfile:
    """从多源原始数据聚合为 CompanyProfile.

    优先级: itjuzi > qichacha > crunchbase (国内数据覆盖更全)

    Raises:
        InsufficientDataError: raw 为空或关键数据全缺,不应继续向下游传递空数据
    """
    if raw.is_empty():
        raise InsufficientDataError(
            f"未获取到 {raw.name} 的任何数据源,请提供 fixtures 或等待 Phase 2 接入真实 API"
        )

    src = raw.itjuzi or raw.qichacha or raw.crunchbase or {}

    founders = [
        Founder(
            name=(f.get("name") or "未公开").strip() or "未公开",
            title=(f.get("title") or "创始团队成员").strip() or "创始团队成员",
            background=(f.get("background") or "").strip(),
            equity_pct=f.get("equity_pct"),
            still_active=f.get("still_active", True),
            current_role=f.get("current_role"),
        )
        for f in (src.get("founders") or [])
    ]

    executives = [
        Executive(
            name=(e.get("name") or "未公开").strip() or "未公开",
            title=(e.get("title") or "高管").strip() or "高管",
            joined=e.get("joined"),
            background=(e.get("background") or "").strip(),
        )
        for e in (src.get("executives") or [])
    ]

    milestones = [
        Milestone(
            date=m.get("date"),
            event=(m.get("event") or "").strip(),
        )
        for m in (src.get("milestones") or [])
        if (m.get("event") or "").strip()
    ]

    region = _infer_region(src.get("region") or src.get("country"))
    stage = parse_funding_stage(src.get("stage"))

    return CompanyProfile(
        name=raw.name,
        legal_name=src.get("legal_name"),
        founded_date=parse_date(src.get("founded_date")),
        headquarters=src.get("headquarters"),
        region=region,
        industry=src.get("industry") or "未分类",
        sub_industry=src.get("sub_industry"),
        business_model=src.get("business_model") or "待补充",
        stage=stage,
        founders=founders,
        executives=executives,
        employee_count=src.get("employee_count"),
        one_liner=src.get("one_liner") or f"{raw.name} — 商业模式待研究",
        products=[p for p in (src.get("products") or []) if p],
        key_customers=[c for c in (src.get("key_customers") or []) if c],
        milestones=milestones,
        website=src.get("website"),
    )


def _infer_region(value: str | None) -> Region:
    if not value:
        return Region.OTHER
    v = str(value).lower()
    if "中国" in str(value) or "cn" in v or "china" in v:
        return Region.CN
    if "us" in v or "美国" in str(value) or "united states" in v:
        return Region.US
    if "eu" in v or "europe" in v:
        return Region.EU
    if "sea" in v or "southeast" in v:
        return Region.SEA
    return Region.OTHER
