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

### 2.2 创始人 / 高管 / 产品 / 客户 / 里程碑

```jsonc
"website": "https://www.bytedance.com",
"founders": [
  {
    "name": "张一鸣",
    "title": "创始人",
    "background": "南开大学...",
    "equity_pct": 0.22,
    "still_active": false,          // 是否仍在岗
    "current_role": "2021 卸任 CEO, 现任技术顾问"  // 离任/换岗后的现状
  }
],
"executives": [                    // 现任核心高管(与 founders 可重叠)
  {
    "name": "梁汝波",
    "title": "CEO",
    "joined": "2012",              // 加入年份或 YYYY-MM
    "background": "南开大学..."
  }
],
"products": ["抖音", "TikTok", "飞书"],        // 核心产品/业务线
"key_customers": ["15 亿+ 月活消费者", "品牌广告主"], // 标志性客户或用户群体
"milestones": [                    // 关键非融资里程碑
  {"date": "2017-11", "event": "10 亿美元收购 Musical.ly"}
]
```

### 2.3 融资轮次(数组)

```jsonc
"rounds": [
  {
    "stage": "a",                                 // 必填,支持多种别名
    "announce_date": "2012-07-01",                // 可为 null / 坏格式 → 自动忽略
    "amount_usd": 5000000,                        // 数字,None 允许
    "pre_money_valuation_usd": 45000000,          // 投前估值,可选
    "post_money_valuation_usd": 50000000,         // 投后估值,可选
    "lead_investors": ["SIG 海纳亚洲"],
    "participants": ["其他跟投方"],
    "share_class": "A 轮优先股",                  // 可选
    "use_of_proceeds": "产品研发 + 市场扩张",    // 可选
    "notes": "天使/A 轮...",                      // 可选
    "investor_details": [                         // 可选:每个投资方的完整档案
      {
        "name": "SIG 海纳亚洲",
        "type": "VC",                             // VC / PE / 战投 / 主权 / 天使 等
        "hq": "香港",
        "aum_usd": null,                          // 管理规模
        "founded_year": 2005,
        "sector_focus": ["TMT", "早期互联网"],
        "notable_portfolio": ["字节跳动", "小红书"],
        "deal_thesis": "看好推荐算法在信息分发的颠覆性",  // 本轮投资逻辑
        "is_lead": true
      }
    ]
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
  "team_score": 9,
  "team_notes": "headline 点评",
  "team_analysis": "3-5 句深度分析: 创始人执行力/高管互补/过往胜率/文化",  // 可选
  "market": {
    "tam_usd": 1500000000000,
    "sam_usd": 500000000000,
    "som_usd": 80000000000,
    "growth_rate": 0.15
  },
  "market_analysis": "3-5 句: TAM/SAM/SOM 推导 + 渗透率曲线",              // 可选
  "moat": "headline",
  "moat_analysis": {                                                      // 可选: 7 Powers
    "network_effect":     {"score": 9, "evidence": "..."},
    "scale_economy":      {"score": 8, "evidence": "..."},
    "switching_cost":     {"score": 6, "evidence": "..."},
    "brand":              {"score": 7, "evidence": "..."},
    "counter_positioning":{"score": 8, "evidence": "..."},
    "cornered_resource":  {"score": 7, "evidence": "..."},
    "process_power":      {"score": 9, "evidence": "..."}
  },
  "unit_economics": {
    "ltv_cac_ratio": 4.5,
    "gross_margin": 0.62,
    "payback_months": 8
  },
  "unit_economics_analysis": "LTV/CAC/毛利相对行业中位数位置 + 趋势",      // 可选
  "growth": {
    "arr_usd": 120000000000,
    "yoy_growth": 0.30,
    "mau": 1800000000,
    "dau": 750000000,
    "gmv_usd": 500000000000,
    "retention_m12": 0.70
  },
  "growth_analysis": "增长质量 / 自然增长占比 / S 曲线阶段",             // 可选
  "competitors": ["Meta", "YouTube"],                                     // headline fallback
  "competitors_detailed": [                                               // 可选: 竞品卡片
    {
      "name": "Meta",
      "hq": "Menlo Park",
      "stage_or_status": "已上市",
      "valuation_usd": 1500000000000,
      "market_share_pct": 0.32,
      "differentiator": "社交图谱 + Instagram 生态",
      "threat_level": "high"
    }
  ],
  "bull": ["看多 headline 1", "..."],
  "bull_detailed": [                                                      // 可选: 带论据看多
    {
      "headline": "全球内容消费平台的唯一挑战者",
      "analysis": "2-4 句展开",
      "evidence": ["数据点 1", "数据点 2"]
    }
  ],
  "bear": ["看空 headline 1", "..."],
  "bear_detailed": [ /* 结构同 bull_detailed */ ]
}
```

**缺失时**: `analyze_thesis` 用保守默认(`team_score=6`, `moat="待识别"`),模块不崩溃。
`moat_analysis` 中任一维度缺失 / score 为 null → 该维度跳过,不会误算为 0。

### 2.5 Industry 数据(可选)

```jsonc
"industry_data": {
  "funding_total_12m_usd": 12000000000,
  "deal_count_12m": 180,
  "gartner_phase": "成熟期",
  "policy_tailwinds": ["..."],
  "policy_headwinds": ["..."],
  "exit_window": "港股 IPO 窗口收紧,美股受地缘影响",
  "hot_keywords": ["短视频", "AIGC"],

  // ─── 深化字段 (Phase 1.5) ───
  "sub_segments": [                              // 赛道细分
    {
      "name": "内容电商",
      "size_usd": 650000000000,
      "growth_rate": 0.35,
      "notes": "本土已验证,海外快速复制"
    }
  ],
  "value_chain": {                               // 产业链上下游
    "upstream":   ["芯片", "CDN/带宽"],
    "midstream":  ["字节跳动", "Meta", "快手"],
    "downstream": ["广告主", "电商商家", "终端消费者"]
  },
  "top_players": [                               // 行业头部(Competitor 结构)
    {
      "name": "Meta",
      "hq": "Menlo Park",
      "stage_or_status": "已上市",
      "valuation_usd": 1500000000000,
      "market_share_pct": 0.32,
      "differentiator": "社交图谱生态"
    }
  ],
  "growth_drivers": ["移动端时长继续增长", "AIGC 降本 10x"],  // 3-5 条
  "barriers_to_entry": ["算法研发门槛", "全球合规能力"],      // 3-5 条
  "industry_key_metrics": {                     // 行业 KPI 字典
    "用户日均时长": "短视频 > 95 分钟",
    "广告加载率": "抖音 12% / Reels 15%"
  }
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
