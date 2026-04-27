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
    SECONDARY = "secondary"  # 二级市场 tender offer / 员工回购 / 介绍上市等无募资事件


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
    still_active: bool = Field(
        default=True, description="是否仍在公司担任核心岗位"
    )
    current_role: Optional[str] = Field(
        default=None, description="若已离开或换角色,现任什么"
    )


class Executive(BaseModel):
    """现任核心高管(可能是创始人,也可能是后来加入的高管)。"""

    name: str
    title: str = Field(description="如 CEO / CTO / COO / CFO / 总裁 / 首席科学家")
    joined: Optional[str] = Field(
        default=None, description="加入时间或加入该岗位时间 (如 2022 或 2022-05)"
    )
    background: str = Field(default="", description="学历 / 过往履历 / 关键成就")


class Product(BaseModel):
    """核心产品/业务线详情."""

    name: str
    category: Optional[str] = Field(default=None, description="硬件/软件/SaaS/平台")
    description: str = Field(default="", description="3-5 句详细介绍")
    specs: dict[str, str] = Field(default_factory=dict, description="关键技术参数")
    launched: Optional[str] = Field(default=None, description="上线时间 YYYY-MM")
    image_url: Optional[str] = None
    revenue_contribution: Optional[str] = Field(
        default=None, description="占总收入比例估算"
    )


class CustomerCase(BaseModel):
    """标志性客户/用户群案例."""

    name: str
    type: Optional[str] = Field(default=None, description="企业/政府/消费者")
    cooperation_since: Optional[str] = Field(default=None, description="合作起始年")
    cooperation_detail: str = Field(
        default="", description="合作背景、项目内容、规模"
    )
    result: str = Field(default="", description="合作成果与进展")
    annual_value_usd: Optional[Decimal] = None


class Milestone(BaseModel):
    """关键里程碑 — 产品发布/融资外的事件、认证、出海、重大客户等。"""

    date: Optional[str] = Field(default=None, description="YYYY-MM 或 YYYY")
    event: str = Field(description="事件详述")
    impact: Optional[str] = Field(default=None, description="对公司发展的意义")


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
    executives: list[Executive] = Field(
        default_factory=list, description="现任核心高管团队(与 founders 可重叠)"
    )
    employee_count: Optional[int] = None
    one_liner: str = Field(description="一句话讲清楚公司在做什么")
    products_detailed: list[Product] = Field(
        default_factory=list, description="核心产品/业务线详情"
    )
    products: list[str] = Field(
        default_factory=list, description="核心产品名称列表(向后兼容)"
    )
    customer_cases: list[CustomerCase] = Field(
        default_factory=list, description="标志性客户合作案例"
    )
    key_customers: list[str] = Field(
        default_factory=list, description="标志性客户名称列表(向后兼容)"
    )
    milestones: list[Milestone] = Field(
        default_factory=list, description="关键非融资里程碑"
    )
    website: Optional[str] = None


# ────────────────────────────────────────────────────────────
# 模块 2: 融资轨迹
# ────────────────────────────────────────────────────────────
class Investor(BaseModel):
    """投资方档案 — 便于评估资方质量与协同。"""

    name: str
    type: Optional[str] = Field(
        default=None,
        description="VC / PE / 战投 / 产业基金 / 政府引导基金 / 主权基金 / "
        "家族办公室 / 天使 / Accelerator",
    )
    hq: Optional[str] = Field(default=None, description="机构总部")
    aum_usd: Optional[Decimal] = Field(default=None, description="管理规模")
    founded_year: Optional[int] = None
    sector_focus: list[str] = Field(
        default_factory=list, description="擅长赛道"
    )
    notable_portfolio: list[str] = Field(
        default_factory=list, description="代表投过的明星项目"
    )
    deal_thesis: Optional[str] = Field(
        default=None, description="本轮为什么投(投资逻辑一句话)"
    )
    is_lead: bool = Field(default=False, description="是否本轮领投")


class FundingRound(BaseModel):
    stage: FundingStage
    announce_date: Optional[date] = None
    amount_usd: Optional[Decimal] = None
    pre_money_valuation_usd: Optional[Decimal] = None
    post_money_valuation_usd: Optional[Decimal] = None
    lead_investors: list[str] = []
    participants: list[str] = []
    investor_details: list[Investor] = Field(
        default_factory=list,
        description="投资方完整档案(若有则在模板中展开渲染)",
    )
    share_class: Optional[str] = Field(
        default=None, description="如 Series A Preferred / 可转债 / 普通股"
    )
    use_of_proceeds: Optional[str] = Field(
        default=None, description="融资用途(产品研发/出海/营销/基础设施等)"
    )
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


class Competitor(BaseModel):
    """竞品全方位档案。"""

    name: str
    hq: Optional[str] = None
    stage_or_status: Optional[str] = Field(
        default=None, description="如 '已上市'/'D 轮'/'独角兽'/'被收购'"
    )
    valuation_usd: Optional[Decimal] = None
    market_share_pct: Optional[float] = Field(
        default=None, description="0-1 小数"
    )
    differentiator: Optional[str] = Field(
        default=None, description="与本公司的核心差异 — 产品/定价/客群/技术"
    )
    threat_level: Optional[str] = Field(
        default=None, description="low / medium / high"
    )


class MoatDimension(BaseModel):
    """护城河单维度评估。"""

    score: int = Field(ge=0, le=10, description="0-10,0 表示无此维度优势")
    evidence: str = Field(description="具体证据 / 数据支撑")


class MoatAnalysis(BaseModel):
    """7 维度护城河评分(来自 Michael Porter + Hamilton Helmer 《7 Powers》框架)。"""

    network_effect: Optional[MoatDimension] = Field(
        default=None, description="网络效应 — 用户越多价值越大"
    )
    scale_economy: Optional[MoatDimension] = Field(
        default=None, description="规模经济 — 单位成本随规模下降"
    )
    switching_cost: Optional[MoatDimension] = Field(
        default=None, description="切换成本 — 用户迁走代价高"
    )
    brand: Optional[MoatDimension] = Field(
        default=None, description="品牌 — 定价权 / 信任溢价"
    )
    counter_positioning: Optional[MoatDimension] = Field(
        default=None, description="反定位 — 对手学不来的商业模式"
    )
    cornered_resource: Optional[MoatDimension] = Field(
        default=None, description="独家资源 — 专利/许可证/关键人才/数据"
    )
    process_power: Optional[MoatDimension] = Field(
        default=None, description="流程势能 — 组织能力/供应链/执行力"
    )


class ThesisPoint(BaseModel):
    """一个投资论点 — 带具体论据的 bull/bear 单元。"""

    headline: str = Field(description="一句话论点")
    analysis: str = Field(
        description="2-4 句展开 — 数据/逻辑/行业背景"
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="可引用的事实、数字、新闻链接或财报条目",
    )


class InvestmentThesis(BaseModel):
    team_score: int = Field(ge=1, le=10, description="团队评分 1-10")
    team_notes: str
    team_analysis: Optional[str] = Field(
        default=None,
        description="团队综合深度分析 — 创始人执行力/高管互补性/文化/过往胜率",
    )
    market: MarketSize
    market_analysis: Optional[str] = Field(
        default=None,
        description="市场规模数字的推导过程 + 增长驱动 + 渗透率曲线",
    )
    moat: str = Field(description="护城河: 技术/网络效应/数据/品牌/规模 (headline)")
    moat_analysis: Optional[MoatAnalysis] = None
    unit_economics: UnitEconomics
    unit_economics_analysis: Optional[str] = Field(
        default=None,
        description="LTV/CAC/毛利相对行业中位数的位置 + 趋势",
    )
    growth: GrowthMetrics
    growth_analysis: Optional[str] = Field(
        default=None,
        description="增长质量:自然增长占比/净收入留存/负留存率/S 曲线阶段",
    )
    competitors: list[str] = []
    competitors_detailed: list[Competitor] = Field(
        default_factory=list, description="有则渲染竞品对比卡片,否则退化为名字列表"
    )
    key_bull_points: list[str] = Field(description="看多理由 (headline-only fallback)")
    key_bull_points_detailed: list[ThesisPoint] = Field(
        default_factory=list, description="有则渲染带论据的看多"
    )
    key_bear_points: list[str] = Field(description="看空理由 (headline-only fallback)")
    key_bear_points_detailed: list[ThesisPoint] = Field(
        default_factory=list, description="有则渲染带论据的看空"
    )


# ────────────────────────────────────────────────────────────
# 模块 4: 产业趋势
# ────────────────────────────────────────────────────────────
class SubSegment(BaseModel):
    """产业子赛道 — 把大赛道切成可投资的细分。"""

    name: str
    size_usd: Optional[Decimal] = Field(default=None, description="该细分 TAM")
    growth_rate: Optional[float] = Field(default=None, description="年增速,0-1")
    notes: Optional[str] = Field(
        default=None, description="为什么这个细分有/没有机会"
    )


class ValueChain(BaseModel):
    """产业链上下游玩家分布。"""

    upstream: list[str] = Field(
        default_factory=list, description="原材料/元器件/工具供应商"
    )
    midstream: list[str] = Field(
        default_factory=list, description="本公司所处环节的玩家"
    )
    downstream: list[str] = Field(
        default_factory=list, description="渠道/分销/终端客户"
    )


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
    # ─── 深化字段 ───
    sub_segments: list[SubSegment] = Field(
        default_factory=list, description="赛道细分 + 每块规模/增速"
    )
    value_chain: Optional[ValueChain] = None
    top_players: list[Competitor] = Field(
        default_factory=list,
        description="行业头部玩家(与本公司 competitors 可重叠,但视角更宏观)",
    )
    growth_drivers: list[str] = Field(
        default_factory=list,
        description="赛道增长的底层驱动力 — 技术/需求/政策/人口",
    )
    barriers_to_entry: list[str] = Field(
        default_factory=list,
        description="新进入者面临的门槛 — 资本/技术/牌照/网络效应",
    )
    industry_key_metrics: dict[str, str] = Field(
        default_factory=dict,
        description="行业常用 KPI 及当前水平 (如 SaaS NRR / 电商 GMV 占比)",
    )


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
# 模块 8: VC 机构画像 (竞品 VC 分析)
# ────────────────────────────────────────────────────────────
class FundStats(BaseModel):
    """基金关键统计."""

    vintage_year: Optional[int] = Field(default=None, description="基金成立年份")
    fund_size_usd: Optional[Decimal] = Field(default=None, description="基金规模 (USD)")
    deployed_pct: Optional[float] = Field(
        default=None, description="已投比例 0-1"
    )
    irr_net: Optional[float] = Field(default=None, description="净 IRR")
    tvpi: Optional[float] = Field(default=None, description="Total Value to Paid-In")
    dpi: Optional[float] = Field(default=None, description="Distributions to Paid-In")


class PortfolioCompany(BaseModel):
    """被投企业摘要."""

    name: str
    industry: Optional[str] = None
    stage_at_entry: Optional[str] = Field(default=None, description="进入时轮次")
    entry_year: Optional[int] = None
    status: Optional[str] = Field(
        default=None, description="active / exited_ipo / exited_ma / written_off"
    )
    valuation_at_entry_usd: Optional[Decimal] = None
    current_valuation_usd: Optional[Decimal] = None
    moic: Optional[float] = Field(default=None, description="Multiple on Invested Capital")


class VCFundProfile(BaseModel):
    """单个 VC 机构的完整画像."""

    name: str
    legal_name: Optional[str] = None
    hq: Optional[str] = Field(default=None, description="总部城市")
    founded_year: Optional[int] = None
    website: Optional[str] = None
    type: str = Field(
        default="VC",
        description="VC / PE / CVC / 政府引导基金 / 家族办公室 / 主权基金",
    )
    aum_usd: Optional[Decimal] = Field(default=None, description="总管理规模")
    team_size: Optional[int] = None
    key_partners: list[str] = Field(default_factory=list, description="核心合伙人")
    sector_focus: list[str] = Field(default_factory=list, description="重点赛道")
    stage_focus: list[str] = Field(
        default_factory=list, description="偏好轮次: seed / A / B / growth"
    )
    geo_focus: list[str] = Field(
        default_factory=list, description="地域偏好: 中国 / 美国 / 东南亚"
    )
    funds: list[FundStats] = Field(default_factory=list, description="旗下基金")
    portfolio: list[PortfolioCompany] = Field(
        default_factory=list, description="代表被投企业"
    )
    notable_exits: list[str] = Field(
        default_factory=list, description="标志性退出案例"
    )
    investment_style: Optional[str] = Field(
        default=None,
        description="投资风格: 领投型 / 跟投型 / 孵化型 / 产业协同型",
    )
    co_invest_frequent: list[str] = Field(
        default_factory=list, description="经常联合投资的机构"
    )
    one_liner: str = Field(default="", description="一句话介绍")


class VCLandscape(BaseModel):
    """目标公司相关的 VC 格局分析 — 从融资轮次中提取投资方画像并做竞品分析."""

    target_company: str = Field(description="被分析的目标公司名")
    investors_involved: list[VCFundProfile] = Field(
        default_factory=list, description="参与投资的 VC 机构画像"
    )
    peer_investors: list[VCFundProfile] = Field(
        default_factory=list,
        description="同赛道活跃但未参投的竞品 VC (便于 BD)",
    )
    investor_quality_score: Optional[float] = Field(
        default=None,
        description="0-10 投资方阵容质量综合评分",
    )
    investor_quality_notes: str = Field(
        default="", description="投资方阵容质量分析叙述"
    )
    syndicate_pattern: Optional[str] = Field(
        default=None,
        description="投资组合模式: 分散型 / 集中型 / 战投主导 / VC 主导",
    )
    follow_on_likelihood: Optional[str] = Field(
        default=None,
        description="现有投资方追加投资的可能性评估",
    )


# ────────────────────────────────────────────────────────────
# 顶层聚合: 完整研报
# ────────────────────────────────────────────────────────────
class VCReport(BaseModel):
    """完整创投研报 — CLI 输出的核心对象."""

    generated_at: date
    analyst: str = "vc-research v0.1.17"
    profile: CompanyProfile
    funding: FundingHistory
    thesis: InvestmentThesis
    industry: IndustryTrend
    valuation: Valuation
    risks: RiskMatrix
    recommendation: Recommendation
    vc_landscape: Optional[VCLandscape] = Field(
        default=None, description="VC 机构格局分析 (--vc-analysis 启用时填充)"
    )
    data_sources: list[str] = Field(description="引用的数据源列表")
    disclaimer: str = (
        "本报告由 vc-research 自动生成,仅供学习研究使用,不构成投资建议。"
        "数据截止 generated_at,之后信息需重新拉取。"
    )
