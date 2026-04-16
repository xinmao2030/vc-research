# 数据源 JSON Schema 契约 · data-source-spec

> Phase 2 接入 IT桔子 / Crunchbase 真实 API 时,**必须**把返回值映射成本文档描述的
> 结构。modules/ 下的 7 个分析模块只认这个结构。

---

## 1. 总入口

fixtures JSON 文件放在 `examples/fixtures/{company}.json`,顶层结构:

```jsonc
{
  "sources_hit": ["itjuzi(模拟)", "crunchbase(模拟)"],  // 数据源命中清单
  "itjuzi":      { ... },   // 国内源聚合 (见第 2 节)
  "crunchbase":  { ... },   // 海外源 (与 itjuzi 同构,可选)
  "qichacha":    { ... },   // 工商/股权变更 (可选,当前未使用)
  "news_items":  [ ... ]    // 近期新闻 (可选)
}
```

**源优先级**: `itjuzi > crunchbase > qichacha`。首个非空源生效,不做字段级合并。

**扩展**: Phase 2 `DataSource.fetch()` 的返回值直接对应一个子源
(例如 `ITJuziSource.fetch()` → 对应 `raw.itjuzi` 的内容)。

---

## 2. 子源结构(与 fixtures 的 `itjuzi` key 同构)

### 2.1 核心字段

| 字段 | 类型 | 必填 | 说明 | 映射模块 |
|------|------|:---:|------|--------|
| `legal_name` | str | 否 | 法定名称 | Profile |
| `founded_date` | str `YYYY-MM-DD` | 否 | 成立日期 | Profile |
| `headquarters` | str | 否 | 总部所在 | Profile |
| `region` | str | 否 | cn/us/eu/sea/other 的中英皆可 | Profile |
| `industry` | str | **是** | 一级赛道(用于估值倍数查表) | Profile, Valuation |
| `sub_industry` | str | 否 | 二级赛道 | Profile |
| `business_model` | str | 否 | 商业模式一句话 | Profile |
| `stage` | str | 否 | 当前阶段,同 FundingStage 别名表 | Profile |
| `employee_count` | int | 否 | 员工规模 | Profile |
| `one_liner` | str | **是** | 一句话描述 | Profile |

### 2.2 创始人(数组)

```jsonc
"founders": [
  {
    "name": "张一鸣",            // 可为 null → 降级为 "未公开"
    "title": "创始人",             // 可为 null → 降级为 "创始团队成员"
    "background": "南开大学...",
    "equity_pct": 0.22             // 0-1 之间,可为 null
  }
]
```

### 2.3 融资轮次(数组)

```jsonc
"rounds": [
  {
    "stage": "a",                                 // 必填,支持多种别名
    "announce_date": "2012-07-01",                // 可为 null / 坏格式 → 自动忽略
    "amount_usd": 5000000,                        // 数字,None 允许
    "post_money_valuation_usd": 50000000,         // 数字,None 允许
    "lead_investors": ["SIG 海纳亚洲"],
    "participants": ["其他跟投方"],
    "notes": "天使/A 轮..."                       // 可选
  }
]
```

**stage 别名对照**(完整表见 `utils._STAGE_ALIAS`):

| 输入 | 映射 |
|------|------|
| `seed` / `天使` / `angel` | SEED |
| `a` / `A 轮` / `Series A` / `a+` | SERIES_A |
| `b` / `B 轮` | SERIES_B |
| `c`, `d`, `e` 类推 | SERIES_C/D/E_PLUS |
| `pre-ipo` / `pre ipo` | PRE_IPO |
| `ipo` | IPO |
| `strategic` / `战略` | STRATEGIC |
| 未知值 | SEED(不崩溃,打 warning) |

### 2.4 Thesis 子结构(可选,有则增强)

```jsonc
"thesis": {
  "team_score": 9,                                 // 1-10
  "team_notes": "...",
  "market": {
    "tam_usd": 1500000000000,
    "sam_usd": 500000000000,
    "som_usd": 80000000000,
    "growth_rate": 0.15                            // 0-1 小数
  },
  "moat": "推荐算法 + 数据飞轮...",
  "unit_economics": {
    "cac_usd": null,
    "ltv_usd": null,
    "ltv_cac_ratio": 4.5,                          // 健康 >= 3
    "gross_margin": 0.62,
    "payback_months": 8
  },
  "growth": {
    "arr_usd": 120000000000,
    "yoy_growth": 0.30,
    "mau": 1800000000,
    "dau": 750000000,
    "gmv_usd": 500000000000,
    "retention_m12": 0.70
  },
  "competitors": ["Meta", "YouTube"],
  "bull": ["看多理由 1", "..."],
  "bear": ["看空理由 1", "..."]
}
```

**缺失时**: `analyze_thesis` 用保守默认(`team_score=5`, `moat="数据不足"`),模块不崩溃。

### 2.5 Industry 数据(可选)

```jsonc
"industry_data": {
  "funding_total_12m_usd": 12000000000,
  "deal_count_12m": 180,
  "gartner_phase": "成熟期",
  "policy_tailwinds": ["..."],
  "policy_headwinds": ["..."],
  "exit_window": "港股 IPO 窗口收紧,美股受地缘影响",
  "hot_keywords": ["短视频", "AIGC"]
}
```

### 2.6 Financials(可选,影响 Risk.runway)

```jsonc
"financials": {
  "burn_rate_usd_monthly": 50000000,   // 月烧钱
  "cash_usd": 30000000000              // 现金储备
}
```

跑道 = `cash_usd / burn_rate_usd_monthly`(月)。

### 2.7 Extra Risks(可选,合并到 RiskMatrix)

```jsonc
"extra_risks": [
  {
    "category": "监管",
    "description": "...",
    "level": "high",                   // low / medium / high / critical
    "mitigation": "缓释方案"
  }
]
```

---

## 3. 宽容性承诺

所有字段都走 `utils.*` 宽容解析:

| 坏输入 | 行为 |
|--------|------|
| `"amount_usd": "ABC"` | → `None`,不崩溃 |
| `"announce_date": "2099-13-40"` | → `None` |
| `"stage": "玄学轮"` | → `SEED`,打 warning |
| `"founders": [{"name": null}]` | → `name="未公开"` |
| 整个 source 为 `{}` | → `is_empty()` 为 true,CLI 抛 `InsufficientDataError`(exit 2) |

---

## 4. Phase 2 API 映射建议

### IT桔子 API
- `company.basic_info` → `itjuzi` 的第 2.1 节核心字段
- `company.funding` → `rounds` 数组
- `company.founders` → `founders` 数组
- Phase 2 需自行推断/填补:`industry` 一级赛道、`business_model`、`thesis.*`

### Crunchbase API
- `organization.properties` → 对应 `crunchbase` 子源(与 itjuzi 同构)
- `funding_rounds` endpoint → `rounds`
- Founder 在 `people` 里,需要 join

### 字段缺失策略
- 核心字段(`industry` / `one_liner`)缺失 → `analyze_profile` 兜底默认值
- Thesis 部分缺失 → 对应 metric 设 None,模板自动跳过该行
- 整个 source 返回 None → aggregator 继续尝试下一个源

---

## 5. 测试你的接入

新数据源接入后,跑:

```bash
# 1. 用 FixturesSource 把真实 API 结果 dump 为 JSON (对照结构)
# 2. 跑全量测试
.venv/bin/pytest tests/ -v

# 3. 用 3 家标杆案例验证无回归
#    test_benchmark_numerics 的 verdict/risk/rounds 不应漂移
```

**黄金规则**: 新增字段只加,不改;删字段必须更新全部 modules + template.md.j2 + tests。
