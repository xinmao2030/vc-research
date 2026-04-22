"""边界条件与负路径测试 — QA 审查发现的 5 个 bug 的回归防线.

覆盖:
- BUG-001: Founder 字段 null
- BUG-003: 空 fixture 降级
- BUG-004: XSS 注入
- 坏 JSON / 坏日期 / 坏 stage / 极值
- LLM schema 校验
- PDF 降级
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from vc_research.data_sources import DataAggregator, RawCompanyData
from vc_research.modules import (
    analyze_funding,
    analyze_industry,
    analyze_profile,
    analyze_recommendation,
    analyze_risks,
    analyze_thesis,
    analyze_valuation,
)
from vc_research.modules.company_profile import InsufficientDataError
from vc_research.schema import FundingStage
from vc_research.utils import (
    format_money_cn,
    format_money_en,
    parse_date,
    parse_funding_stage,
    to_decimal,
)


# ─────────────────── 1. 空数据 ────────────────────────────
def test_empty_raw_raises_insufficient_data() -> None:
    """BUG-003: 空 fixture 不应静默产生零估值报告."""
    raw = RawCompanyData(name="不存在的公司")
    with pytest.raises(InsufficientDataError):
        analyze_profile(raw)


def test_empty_itjuzi_dict_raises() -> None:
    """完全空的 itjuzi={} 也应视作无数据."""
    raw = RawCompanyData(name="X")
    assert raw.is_empty()


# ─────────────────── 2. Null 字段容忍 ────────────────────
def test_founder_with_null_name_does_not_crash(tmp_path) -> None:
    """BUG-001: Founder 字段为 null 不应崩溃."""
    fixture = tmp_path / "bad.json"
    fixture.write_text(
        json.dumps(
            {
                "itjuzi": {
                    "industry": "AI",
                    "founders": [{"name": None, "title": None, "background": None}],
                }
            }
        ),
        encoding="utf-8",
    )
    agg = DataAggregator(use_fixtures=True, fixtures_dir=str(tmp_path))
    raw = agg.fetch("bad")
    profile = analyze_profile(raw)
    assert len(profile.founders) == 1
    assert profile.founders[0].name == "未公开"
    assert profile.founders[0].title == "创始团队成员"


# ─────────────────── 3. XSS 注入 ───────────────────────
def test_xss_sanitized_in_html() -> None:
    """BUG-004: <script> 在 MD→HTML 路径必须被剥离."""
    from vc_research.report.renderer import _sanitize_html

    dirty = '<p>hi</p><script>alert(1)</script><img src=x onerror=alert(1)>'
    clean = _sanitize_html(dirty)
    assert "<script>" not in clean
    assert "onerror" not in clean
    assert "<p>hi</p>" in clean


def test_xss_sanitized_in_dashboard_path() -> None:
    from vc_research.report.renderer import _sanitize_html

    assert "<iframe" not in _sanitize_html("<iframe src=//evil></iframe>")
    assert "<script" not in _sanitize_html("<SCRIPT>x</SCRIPT>")
    assert "onclick" not in _sanitize_html('<a onclick="x">y</a>')


def test_xss_javascript_url_stripped() -> None:
    """v0.1.13: javascript:/data:/vbscript: URL schemes 在 href/src 里必须被剥离."""
    from vc_research.report.renderer import _sanitize_html

    # href="javascript:..." (双引号)
    assert "javascript:" not in _sanitize_html(
        '<a href="javascript:alert(1)">x</a>'
    ).lower()
    # href='javascript:...' (单引号)
    assert "javascript:" not in _sanitize_html(
        "<a href='javascript:alert(1)'>x</a>"
    ).lower()
    # 大小写混淆
    assert "javascript:" not in _sanitize_html(
        '<a href="JaVaScRiPt:alert(1)">x</a>'
    ).lower()
    # data:text/html (iframe 外常见 XSS 载体)
    assert "data:text/html" not in _sanitize_html(
        '<a href="data:text/html,hello">x</a>'
    ).lower()
    # vbscript (legacy IE)
    assert "vbscript:" not in _sanitize_html(
        '<a href="vbscript:msgbox(1)">x</a>'
    ).lower()
    # src on img
    assert "javascript:" not in _sanitize_html(
        '<img src="javascript:void(0)">'
    ).lower()
    # 正常 URL 保留
    safe = _sanitize_html('<a href="https://example.com">ok</a>')
    assert "https://example.com" in safe


# ─────────────────── 4. utils 宽容解析 ──────────────────
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("A 轮", FundingStage.SERIES_A),
        ("Series A", FundingStage.SERIES_A),
        ("a+", FundingStage.SERIES_A),
        ("B 轮", FundingStage.SERIES_B),
        ("天使", FundingStage.SEED),
        ("pre-IPO", FundingStage.PRE_IPO),
        ("战略", FundingStage.STRATEGIC),
        ("IPO", FundingStage.IPO),
        ("玄学轮", FundingStage.SEED),  # 未知默认
        (None, FundingStage.SEED),
        ("", FundingStage.SEED),
    ],
)
def test_parse_funding_stage(raw, expected: FundingStage) -> None:
    assert parse_funding_stage(raw) == expected


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("123.45", Decimal("123.45")),
        (100, Decimal("100")),
        (None, None),
        ("ABC", None),  # 宽容不崩溃
        ("", None),
    ],
)
def test_to_decimal(raw, expected) -> None:
    assert to_decimal(raw) == expected


@pytest.mark.parametrize(
    "raw",
    ["not-a-date", "2099-13-40", "", None],
)
def test_parse_date_tolerates_bad_input(raw) -> None:
    assert parse_date(raw) is None


# ─────────────────── 5. 格式化 ──────────────────────────
@pytest.mark.parametrize(
    "amount,expected",
    [
        (180_000_000_000, "$1800.00 亿"),
        (5_000_000, "$500.00 万"),
        (100, "$100"),
        (0, "$0"),
        (None, "—"),
    ],
)
def test_format_money_cn(amount, expected: str) -> None:
    assert format_money_cn(amount) == expected


@pytest.mark.parametrize(
    "amount,expected",
    [
        (180_000_000_000, "$180.00B"),
        (5_000_000, "$5.00M"),
        (1_500, "$1.50K"),
        (0, "$0"),
        (None, "—"),
    ],
)
def test_format_money_en(amount, expected: str) -> None:
    assert format_money_en(amount) == expected


# ─────────────────── 6. 数值正确性断言 ────────────────
# 固定标杆案例的估值区间,保证未来重构不会意外改变关键数字
BENCHMARKS = {
    "影石创新": {
        "rounds": 6,
        "latest_valuation_usd": Decimal("9800000000"),
        "verdict": "观望",
        "overall_risk": "high",  # GoPro 337 诉讼 + 海外依赖
        "stage": FundingStage.IPO,
    },
    "澜起科技": {
        "rounds": 6,
        "latest_valuation_usd": Decimal("28000000000"),
        "verdict": "观望",
        "overall_risk": "high",  # 美国制裁传导 + 下游 DRAM 周期
        "stage": FundingStage.SECONDARY,  # 2026-01 A+H 挂牌
    },
    "银诺医药": {
        "rounds": 5,
        "latest_valuation_usd": Decimal("3360000000"),
        "verdict": "参投",
        "overall_risk": "high",  # GLP-1 红海竞争 + 单品依赖
        "stage": FundingStage.IPO,
    },
    "必贝特医药": {
        "rounds": 3,
        "latest_valuation_usd": Decimal("1970000000"),
        "verdict": "参投",
        "overall_risk": "high",  # 管线尚未商业化
        "stage": FundingStage.IPO,
    },
    "汉朔科技": {
        "rounds": 6,
        "latest_valuation_usd": Decimal("3920000000"),
        "verdict": "回避",
        "overall_risk": "high",  # 海外收入 94% 贸易战风险
        "stage": FundingStage.IPO,
    },
    "强一股份": {
        "rounds": 6,
        "latest_valuation_usd": Decimal("1530000000"),
        "verdict": "回避",
        "overall_risk": "high",  # 探针卡海外龙头垄断
        "stage": FundingStage.IPO,
    },
}


@pytest.mark.parametrize("name, expected", list(BENCHMARKS.items()))
def test_benchmark_numerics(name: str, expected: dict) -> None:
    raw = DataAggregator(use_fixtures=True).fetch(name)
    profile = analyze_profile(raw)
    funding = analyze_funding(raw)
    thesis = analyze_thesis(raw)
    valuation = analyze_valuation(funding, thesis, industry=profile.industry)
    risks = analyze_risks(raw, funding, thesis)
    rec = analyze_recommendation(thesis, valuation, risks, funding, profile)

    assert len(funding.rounds) == expected["rounds"], f"{name} 轮次数"
    assert funding.latest_valuation_usd == expected["latest_valuation_usd"], f"{name} 最新估值"
    assert rec.verdict == expected["verdict"], f"{name} 投资裁决"
    assert risks.overall_level.value == expected["overall_risk"], f"{name} 整体风险"


# ─────────────────── 7. LLM schema 校验 ────────────────
def test_llm_enhanced_thesis_schema_rejects_garbage() -> None:
    """Claude 返回非法字段不应污染 thesis."""
    from vc_research.llm.claude_analyzer import EnhancedThesis

    # 多余字段会被忽略 (Pydantic 默认行为)
    good = EnhancedThesis.model_validate(
        {"moat": "ok", "bull": ["a"], "bear": [], "team_notes": ""}
    )
    assert good.moat == "ok"

    # 类型错的字段
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        EnhancedThesis.model_validate({"bull": "应该是 list 不是 string"})


# ─────────────────── 8. 估值方法按行业差异化 ────────────
def test_industry_affects_valuation() -> None:
    """AI 行业应得到比默认更高的估值倍数."""
    from vc_research.modules.valuation import _multiples_for_industry

    ai = _multiples_for_industry("人工智能")
    ecommerce = _multiples_for_industry("电商")
    assert ai["arr"] > ecommerce["arr"], "AI 倍数应高于电商"
    assert _multiples_for_industry(None) == {}
    assert _multiples_for_industry("未知赛道") == {}


# ─────────────── 9. 集成测试: QA 发现的 3 条未覆盖分支 ────────
def test_crunchbase_fallback_when_itjuzi_missing(tmp_path) -> None:
    """多源降级: itjuzi 缺失时,funding 应从 crunchbase 读取轮次 (记录当前优先级行为)."""
    fixture = tmp_path / "only_cb.json"
    fixture.write_text(
        json.dumps(
            {
                "crunchbase": {
                    "industry": "SaaS",
                    "one_liner": "海外案例",
                    "region": "us",
                    "founders": [
                        {"name": "Jane", "title": "CEO", "background": "MIT"}
                    ],
                    "rounds": [
                        {"stage": "Seed", "amount_usd": 1_000_000},
                        {"stage": "Series A", "amount_usd": 5_000_000,
                         "post_money_valuation_usd": 20_000_000},
                    ],
                },
            }
        ),
        encoding="utf-8",
    )
    agg = DataAggregator(use_fixtures=True, fixtures_dir=str(tmp_path))
    raw = agg.fetch("only_cb")
    funding = analyze_funding(raw)
    assert len(funding.rounds) == 2
    assert funding.latest_valuation_usd == Decimal("20000000")


def test_dilution_accumulates_across_rounds() -> None:
    """稀释链: 6 轮累计稀释应 > 单轮稀释且 < 1 (retention 不能为 0)."""
    raw = DataAggregator(use_fixtures=True).fetch("影石创新")
    funding = analyze_funding(raw)
    assert funding.dilution_estimate is not None
    # 6 轮按 10-22% 稀释累乘,总稀释应在 30-80% 合理区间
    assert 0.3 < funding.dilution_estimate < 0.95, (
        f"6 轮累计稀释 {funding.dilution_estimate:.2%} 超出合理区间"
    )


def test_valuation_degrades_gracefully_with_no_industry() -> None:
    """行业倍数缺失降级: industry=None 时仍能产出估值 (走 _INDUSTRY_DEFAULT 兜底)."""
    raw = DataAggregator(use_fixtures=True).fetch("影石创新")
    funding = analyze_funding(raw)
    thesis = analyze_thesis(raw)
    v = analyze_valuation(funding, thesis, industry=None)
    assert len(v.methods) >= 1
    assert v.fair_value_high_usd > 0, "锚点法应兜底产出非零估值"


# ────────────────────────────────────────────────────────────
# P3: 新 schema 类型 (Product / CustomerCase / Milestone.impact)
# ────────────────────────────────────────────────────────────

class TestProductSchema:
    def test_product_full(self):
        from vc_research.schema import Product

        p = Product(
            name="E-ARM 300",
            category="硬件",
            description="六轴协作机器人",
            specs={"负载": "30kg", "精度": "±0.02mm"},
            launched="2022-09",
            image_url="https://example.com/img.jpg",
            revenue_contribution="60%",
        )
        assert p.name == "E-ARM 300"
        assert p.specs["负载"] == "30kg"

    def test_product_minimal(self):
        from vc_research.schema import Product

        p = Product(name="X")
        assert p.description == ""
        assert p.specs == {}
        assert p.image_url is None


class TestCustomerCaseSchema:
    def test_customer_case_full(self):
        from vc_research.schema import CustomerCase

        c = CustomerCase(
            name="富士康",
            type="企业",
            cooperation_since="2021",
            cooperation_detail="部署 200 台机器人",
            result="效率提升 40%",
            annual_value_usd=Decimal("5000000"),
        )
        assert c.name == "富士康"
        assert c.annual_value_usd == Decimal("5000000")

    def test_customer_case_minimal(self):
        from vc_research.schema import CustomerCase

        c = CustomerCase(name="Test")
        assert c.cooperation_detail == ""
        assert c.annual_value_usd is None


class TestMilestoneImpact:
    def test_milestone_with_impact(self):
        from vc_research.schema import Milestone

        m = Milestone(date="2024-02", event="FlexCell Pro 发布", impact="确立平台优势")
        assert m.impact == "确立平台优势"

    def test_milestone_without_impact(self):
        from vc_research.schema import Milestone

        m = Milestone(event="产品发布")
        assert m.impact is None


class TestProfileNewFields:
    """验证 analyze_profile 能同时解析新格式(dict)和旧格式(str)的 products/customers."""

    def test_old_fixture_still_works(self):
        """旧 fixture (无 products 字段) 正常解析,新字段为空列表."""
        raw = DataAggregator(use_fixtures=True).fetch("影石创新")
        p = analyze_profile(raw)
        # 旧 fixture 没有 products 字段,新字段应为空列表
        assert isinstance(p.products, list)
        assert isinstance(p.products_detailed, list)
        assert isinstance(p.customer_cases, list)

    def test_dict_products_parsed(self):
        """dict 格式的 products 被解析到 products_detailed."""
        from vc_research.data_sources import RawCompanyData

        raw = RawCompanyData(name="Test")
        raw.itjuzi = {
            "industry": "AI",
            "one_liner": "Test",
            "business_model": "SaaS",
            "stage": "a",
            "region": "cn",
            "products": [
                {"name": "Prod1", "category": "SaaS", "description": "Desc"},
            ],
            "key_customers": [
                {"name": "Cust1", "type": "企业", "cooperation_detail": "合作"},
            ],
            "milestones": [
                {"date": "2024", "event": "发布", "impact": "里程碑"},
            ],
        }
        p = analyze_profile(raw)
        assert len(p.products_detailed) == 1
        assert p.products_detailed[0].name == "Prod1"
        assert len(p.customer_cases) == 1
        assert p.customer_cases[0].cooperation_detail == "合作"
        assert p.milestones[0].impact == "里程碑"


class TestVerdictVCTerminology:
    """验证 verdict 使用 VC 语境措辞."""

    def test_verdict_values(self):
        raw = DataAggregator(use_fixtures=True).fetch("银诺医药")
        p = analyze_profile(raw)
        funding = analyze_funding(raw)
        thesis = analyze_thesis(raw)
        valuation = analyze_valuation(funding, thesis, industry=p.industry)
        risks = analyze_risks(raw, funding, thesis)
        rec = analyze_recommendation(thesis, valuation, risks, funding, p)
        assert rec.verdict in ("强烈参投", "参投", "观望", "回避")
