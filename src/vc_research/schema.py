"""核心数据模型 — 7 层分析框架对应的 Pydantic schema."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ────────────────────────────────────────────────────────────
# 枚举
# ────────────────────────────────────────────────────────────
class FundingStage(str, Enum):
    PRE_SEED = "pre_seed"
    SEED = "seed"
    SERIES_A = "series_a"
    SERIES_B = "series_b"
    SERIES_C = "series_c"
    SERIES_D = "series_d"
    SERIES_E_PLUS = "series_e_plus"
    PRE_IPO = "pre_ipo"
    IPO = "ipo"
    STRATEGIC = "strategic"


class Region(str, Enum):
    CN = "cn"
    US = "us"
    EU = "eu"
    SEA = "sea"
    OTHER = "other"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# ────────────────────────────────────────────────────────────
# 模块 1: 企业画像
# ────────────────────────────────────────────────────────────
class Founder(BaseModel):
    name: str
    title: str
    background: str = Field(description="学历/履历/过往创业")
    equity_pct: Optional[float] = None


class CompanyProfile(BaseModel):
    name: str
    legal_name: Optional[str] = None
    founded_date: Optional[date] = None
    headquarters: Optional[str] = None
    region: Region
    industry: str = Field(description="一级赛道, e.g. AI/SaaS/新能源")
    sub_industry: Optional[str] = None
    business_model: str = Field(description="怎么赚钱 (B2B SaaS / 电商 / 硬件+订阅)")
    stage: FundingStage
    founders: list[Founder] = []
    employee_count: Optional[int] = None
    one_liner: str = Field(description="一句话讲清楚公司在做什么")


# ────────────────────────────────────────────────────────────
# 模块 2: 融资轨迹
# ────────────────────────────────────────────────────────────
class FundingRound(BaseModel):
    stage: FundingStage
    announce_date: Optional[date] = None
    amount_usd: Optional[Decimal] = None
    post_money_valuation_usd: Optional[Decimal] = None
    lead_investors: list[str] = []
    participants: list[str] = []
    notes: Optional[str] = None


class FundingHistory(BaseModel):
    rounds: list[FundingRound]
    total_raised_usd: Optional[Decimal] = None
    latest_valuation_usd: Optional[Decimal] = None
    valuation_cagr: Optional[float] = Field(None, description="估值复合增长率")
    dilution_estimate: Optional[float] = Field(
        None, description="创始团队累计稀释比例估算"
    )


# ────────────────────────────────────────────────────────────
# 模块 3: 投资依据 (Thesis)
# ────────────────────────────────────────────────────────────
class MarketSize(BaseModel):
    tam_usd: Optional[Decimal] = Field(None, description="Total Addressable Market")
    sam_usd: Optional[Decimal] = Field(None, description="Serviceable Addressable")
    som_usd: Optional[Decimal] = Field(None, description="Serviceable Obtainable")
    growth_rate: Optional[float] = None


class UnitEconomics(BaseModel):
    cac_usd: Optional[Decimal] = Field(None, description="客户获取成本")
    ltv_usd: Optional[Decimal] = Field(None, description="客户生命周期价值")
    ltv_cac_ratio: Optional[float] = None
    gross_margin: Optional[float] = None
    payback_months: Optional[float] = None


class GrowthMetrics(BaseModel):
    arr_usd: Optional[Decimal] = None
    yoy_growth: Optional[float] = None
    mau: Optional[int] = None
    dau: Optional[int] = None
    gmv_usd: Optional[Decimal] = None
    retention_m12: Optional[float] = None


class InvestmentThesis(BaseModel):
    team_score: int = Field(ge=1, le=10, description="团队评分 1-10")
    team_notes: str
    market: MarketSize
    moat: str = Field(description="护城河: 技术/网络效应/数据/品牌/规模")
    unit_economics: UnitEconomics
    growth: GrowthMetrics
    competitors: list[str] = []
    key_bull_points: list[str] = Field(description="看多理由")
    key_bear_points: list[str] = Field(description="看空理由")


# ────────────────────────────────────────────────────────────
# 模块 4: 产业趋势
# ────────────────────────────────────────────────────────────
class IndustryTrend(BaseModel):
    industry: str
    funding_total_12m_usd: Optional[Decimal] = Field(None, description="近12月赛道融资总额")
    deal_count_12m: Optional[int] = None
    gartner_phase: Optional[str] = Field(
        None, description="萌芽期/期望膨胀期/幻灭期/复苏期/成熟期"
    )
    policy_tailwinds: list[str] = []
    policy_headwinds: list[str] = []
    exit_window: str = Field(description="IPO/并购窗口评估")
    hot_keywords: list[str] = []


# ────────────────────────────────────────────────────────────
# 模块 5: 估值分析
# ────────────────────────────────────────────────────────────
class ValuationMethod(BaseModel):
    method: str = Field(description="可比公司/可比交易/DCF/VC逆推")
    valuation_low_usd: Decimal
    valuation_high_usd: Decimal
    assumptions: str


class Valuation(BaseModel):
    methods: list[ValuationMethod]
    fair_value_low_usd: Decimal
    fair_value_high_usd: Decimal
    current_valuation_usd: Optional[Decimal] = None
    premium_discount: Optional[float] = Field(
        None, description="当前估值 vs 公允价值的溢价/折价"
    )
    sensitivity_notes: str = Field(description="关键假设敏感性说明")


# ────────────────────────────────────────────────────────────
# 模块 6: 风险矩阵
# ────────────────────────────────────────────────────────────
class Risk(BaseModel):
    category: str = Field(description="市场/技术/团队/监管/现金流/退出")
    description: str
    level: RiskLevel
    mitigation: Optional[str] = None


class RiskMatrix(BaseModel):
    burn_rate_usd_monthly: Optional[Decimal] = None
    cash_usd: Optional[Decimal] = None
    runway_months: Optional[float] = None
    risks: list[Risk]
    overall_level: RiskLevel


# ────────────────────────────────────────────────────────────
# 模块 7: 投资建议
# ────────────────────────────────────────────────────────────
class Recommendation(BaseModel):
    verdict: str = Field(description="强烈推荐/推荐/观望/回避")
    target_entry_valuation_usd: Optional[Decimal] = None
    suggested_terms: list[str] = Field(
        default_factory=list,
        description="建议条款: 优先清算权/反稀释/对赌/董事会席位",
    )
    investment_logic: str = Field(description="3句话讲清楚为什么投/不投")
    exit_scenarios: list[str] = Field(description="退出情景: IPO/并购/回购")


# ────────────────────────────────────────────────────────────
# 顶层聚合: 完整研报
# ────────────────────────────────────────────────────────────
class VCReport(BaseModel):
    """完整创投研报 — CLI 输出的核心对象."""

    generated_at: date
    analyst: str = "vc-research v0.1"
    profile: CompanyProfile
    funding: FundingHistory
    thesis: InvestmentThesis
    industry: IndustryTrend
    valuation: Valuation
    risks: RiskMatrix
    recommendation: Recommendation
    data_sources: list[str] = Field(description="引用的数据源列表")
    disclaimer: str = (
        "本报告由 vc-research 自动生成,仅供学习研究使用,不构成投资建议。"
        "数据截止 generated_at,之后信息需重新拉取。"
    )
