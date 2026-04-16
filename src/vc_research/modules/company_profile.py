"""模块 1: 企业画像 — 从原始数据构建 CompanyProfile."""

from __future__ import annotations

from datetime import date

from ..data_sources import RawCompanyData
from ..schema import CompanyProfile, Founder, FundingStage, Region


_STAGE_MAP = {
    "pre_seed": FundingStage.PRE_SEED,
    "seed": FundingStage.SEED,
    "angel": FundingStage.SEED,
    "a": FundingStage.SERIES_A,
    "b": FundingStage.SERIES_B,
    "c": FundingStage.SERIES_C,
    "d": FundingStage.SERIES_D,
    "pre_ipo": FundingStage.PRE_IPO,
    "ipo": FundingStage.IPO,
}


def analyze_profile(raw: RawCompanyData) -> CompanyProfile:
    """从多源原始数据聚合为 CompanyProfile.

    优先级: itjuzi > qichacha > crunchbase (国内数据覆盖更全)
    """
    src = raw.itjuzi or raw.qichacha or raw.crunchbase or {}

    founders = [
        Founder(
            name=f.get("name", "未知"),
            title=f.get("title", "创始人"),
            background=f.get("background", ""),
            equity_pct=f.get("equity_pct"),
        )
        for f in src.get("founders", [])
    ]

    region = _infer_region(src.get("region") or src.get("country"))
    stage = _STAGE_MAP.get(str(src.get("stage", "")).lower(), FundingStage.SEED)

    founded = src.get("founded_date")
    if founded and isinstance(founded, str):
        try:
            founded = date.fromisoformat(founded)
        except ValueError:
            founded = None

    return CompanyProfile(
        name=raw.name,
        legal_name=src.get("legal_name"),
        founded_date=founded,
        headquarters=src.get("headquarters"),
        region=region,
        industry=src.get("industry", "未分类"),
        sub_industry=src.get("sub_industry"),
        business_model=src.get("business_model", "待补充"),
        stage=stage,
        founders=founders,
        employee_count=src.get("employee_count"),
        one_liner=src.get("one_liner", f"{raw.name} — 商业模式待研究"),
    )


def _infer_region(value: str | None) -> Region:
    if not value:
        return Region.OTHER
    v = str(value).lower()
    if "中国" in value or "cn" in v or "china" in v:
        return Region.CN
    if "us" in v or "美国" in value or "united states" in v:
        return Region.US
    if "eu" in v or "europe" in v:
        return Region.EU
    if "sea" in v or "southeast" in v:
        return Region.SEA
    return Region.OTHER
