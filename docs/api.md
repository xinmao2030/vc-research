# API 文档 · vc-research

> 面向二次开发者和集成方。CLI 使用请读 [quickstart.md](./quickstart.md);架构全貌读 [architecture.md](./architecture.md)。

---

## 1. 顶层入口

### `DataAggregator.fetch(company: str) -> RawCompanyData`

从 fixtures 或真实数据源聚合原始数据。

```python
from vc_research.data_sources import DataAggregator

agg = DataAggregator(use_fixtures=True, fixtures_dir=None)
raw = agg.fetch("字节跳动")

assert raw.sources_hit          # 命中的数据源列表
assert not raw.is_empty()        # 至少一个源非空
```

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `use_fixtures` | `bool` | `True` | Phase 1 模式;Phase 2 传 False 走真实 API |
| `fixtures_dir` | `str \| None` | None | 覆盖默认 `examples/fixtures/` |

**异常**: `use_fixtures=False` 在 Phase 1 抛 `NotImplementedError`。

---

## 2. 7 大分析模块

所有模块位于 `vc_research.modules` 下,纯函数接口,输入 `RawCompanyData`/其他模块输出,返回 Pydantic 模型。

### 2.1 `analyze_profile(raw) -> CompanyProfile`
企业画像。**异常**: `raw.is_empty()` 时抛 `InsufficientDataError`(exit code 2)。

### 2.2 `analyze_funding(raw) -> FundingHistory`
融资轨迹。自动计算 `valuation_cagr`(估值复合增速)和 `dilution_estimate`(创始团队累计稀释)。

数据源优先级: `itjuzi > crunchbase > qichacha`(首个非空源生效,不做字段级合并)。

### 2.3 `analyze_thesis(raw) -> InvestmentThesis`
投资依据。产出 10 分制团队评分、护城河描述、TAM/SAM/SOM、LTV/CAC、看多看空要点。

### 2.4 `analyze_industry(raw, industry: str) -> IndustryTrend`
产业趋势。需要显式传入赛道(通常取 `profile.industry`)。

### 2.5 `analyze_valuation(funding, thesis, industry=None, comparable_multiples=None) -> Valuation`
4 种估值方法交叉验证:可比公司(P/ARR)/ GMV 倍数 / VC 逆推 / 最近一轮锚点。

- `industry` 为 None → 走 `_INDUSTRY_DEFAULT` 兜底(早期 SaaS 倍数)
- `comparable_multiples` 非空 → 覆盖查表结果
- 所有方法都无数据时,`fair_value_low/high = 0`,不会崩溃

### 2.6 `analyze_risks(raw, funding, thesis) -> RiskMatrix`
风险矩阵。`overall_level` 取所有 risk 项的最高等级。

### 2.7 `analyze_recommendation(thesis, valuation, risks, funding) -> Recommendation`
综合裁决:`强烈推荐` / `推荐` / `观望` / `回避`。

---

## 3. LLM 增强(可选)

```python
from vc_research.llm import ClaudeAnalyzer, LLMEnhancementError, EnhancedThesis

analyzer = ClaudeAnalyzer()  # 需 ANTHROPIC_API_KEY
try:
    enhanced: EnhancedThesis = analyzer.enhance_thesis(
        profile.model_dump(mode="python"),
        funding.model_dump(mode="python"),
        thesis.growth.model_dump(mode="python"),
    )
except LLMEnhancementError:
    # API 失败/JSON 解析失败/schema 校验失败 → 优雅降级
    pass
```

`EnhancedThesis` 字段(Pydantic 校验):

| 字段 | 类型 | 约束 |
|------|------|------|
| `moat` | str | 0-500 字 |
| `bull` | list[str] | 0-5 条,每条 ≤200 字 |
| `bear` | list[str] | 0-5 条,每条 ≤200 字 |
| `team_notes` | str | 0-500 字 |

---

## 4. 渲染器

```python
from vc_research.report import render_markdown
from vc_research.report.renderer import render_html, render_pdf

md: str  = render_markdown(report)             # 总入口,Markdown 字符串
html: str = render_html(report)                 # 暗色样式独立 HTML
render_pdf(report, Path("out.pdf"))             # PDF (降级到 .html)
```

**安全**: HTML 路径经过 `_sanitize_html` 剥离 `<script>/<iframe>/<style>/on*` 事件属性(BUG-004)。PDF 依赖 `weasyprint + pango/cairo`,缺失时抛 `RuntimeError` 并降级输出 HTML。

---

## 5. 核心 Schema(Pydantic)

全部定义在 `vc_research.schema`。

| 枚举 | 取值 |
|------|------|
| `FundingStage` | pre_seed / seed / series_a / series_b / series_c / series_d / series_e_plus / pre_ipo / ipo / strategic |
| `Region` | cn / us / eu / sea / other |
| `RiskLevel` | low / medium / high / critical |

| 顶层模型 | 说明 |
|----------|------|
| `CompanyProfile` | 模块 1 输出 |
| `FundingHistory` | 模块 2 输出 |
| `InvestmentThesis` | 模块 3 输出 |
| `IndustryTrend` | 模块 4 输出 |
| `Valuation` | 模块 5 输出 |
| `RiskMatrix` | 模块 6 输出 |
| `Recommendation` | 模块 7 输出 |
| `VCReport` | 全部聚合 → 渲染器输入 |

**所有金额字段使用 `Decimal`,不要传 `float`**(精度要求,valuation 计算链路依赖)。

---

## 6. 错误码(CLI)

| 退出码 | 场景 |
|--------|------|
| `0` | 正常生成研报 |
| `1` | 公司未在 fixtures / 未找到数据 |
| `2` | `InsufficientDataError`:数据存在但画像无法构建 |

## 7. utils 工具函数

`vc_research.utils` 提供共享解析器:

| 函数 | 行为 |
|------|------|
| `parse_funding_stage(raw) → FundingStage` | 中英混合别名 → 枚举,未知默认 seed |
| `to_decimal(raw) → Decimal \| None` | 宽容:非法字符串/None 返回 None,不抛异常 |
| `parse_date(raw) → date \| None` | 同上,坏日期返回 None |
| `format_money_cn / format_money_en / format_money` | 自动单位($100 亿 / $180B) |
