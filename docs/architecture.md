# 系统架构 · vc-research

> 面向贡献者和二次开发。如何加新数据源、新分析模块、新渲染器。

---

## 1. 架构全景

```
            ┌─────────────────────────────────────────────┐
   用户输入  │  CLI (cli.py) / Python API / Web Dashboard  │
  (公司名)   └───────────────────┬─────────────────────────┘
                                 │
                                 ▼
            ┌─────────────────────────────────────────────┐
   数据采集  │  DataAggregator (data_sources/aggregator.py)│
             │  Phase 1: fixtures (JSON)                   │
             │  Phase 2: IT桔子 + Crunchbase + 企查查      │
             └───────────────────┬─────────────────────────┘
                                 │
                                 ▼
                    RawCompanyData (原始 payload)
                                 │
         ┌───────────────────────┼──────────────────────┐
         ▼                       ▼                      ▼
  ┌────────────┐         ┌────────────┐         ┌────────────┐
  │ Module 1-7 │         │ LLM Layer  │◀────────│  env var   │
  │ (modules/) │◀────────│ (llm/)     │         │ CLAUDE key │
  └─────┬──────┘         └─────┬──────┘         └────────────┘
        │                       │
        │  Pydantic 模型(VCReport)
        └──────────┬────────────┘
                   ▼
        ┌────────────────────────┐
        │ Renderer (report/)     │
        │ • Markdown  (J2 模板)  │
        │ • HTML      (+ sanitize)│
        │ • PDF       (weasyprint)│
        └──────────┬─────────────┘
                   ▼
               .md / .html / .pdf
```

---

## 2. 数据流

1. **输入**: `vc-research analyze "字节跳动"` → `DataAggregator.fetch(name)`
2. **聚合**: 从 `examples/fixtures/字节跳动.json` 读出 itjuzi/crunchbase/qichacha 原始字段,装进 `RawCompanyData`
3. **7 个模块串行调用**,每个模块签名 `(raw, ...) → Pydantic 模型`:
   - `analyze_profile`: 公司基本面,若 `raw.is_empty()` 抛 `InsufficientDataError`
   - `analyze_funding`: 融资轨迹 + 稀释估算(按 stage 典型值累乘)
   - `analyze_thesis`: 团队/市场/护城河/单位经济学(其中 LLM 增强可选)
   - `analyze_industry`: 赛道趋势、Gartner 周期、政策风向
   - `analyze_valuation`: 4 方法交叉(需要 `profile.industry` 查倍数表)
   - `analyze_risks`: 汇总 market/tech/team/regulatory/cash/exit 六类风险
   - `analyze_recommendation`: 综合产出投资建议裁决
4. **LLM 增强(可选)**: 若 `--llm`,`ClaudeAnalyzer.enhance_thesis` 返回 `EnhancedThesis`,合并到 base thesis
5. **渲染**: `render_markdown(report)` → Jinja2 模板填充 + 注入 `analogies` 教育类比
6. **输出**: `.md` 写到 `-o` 指定路径;`--pdf` 再走 weasyprint

---

## 3. 核心目录

```
src/vc_research/
├── cli.py                  # Typer 入口,串联 7 模块 + 闯关进度条
├── schema.py               # 所有 Pydantic 模型 (VCReport + 7 个子模型)
├── utils.py                # 共享解析器(stage / decimal / date / money)
├── data_sources/
│   ├── aggregator.py       # DataAggregator + RawCompanyData
│   └── __init__.py
├── modules/                # 7 个分析模块,每个一个文件
│   ├── company_profile.py
│   ├── funding_rounds.py
│   ├── investment_thesis.py
│   ├── industry_trends.py
│   ├── valuation.py
│   ├── risk_matrix.py
│   └── recommendation.py
├── llm/
│   └── claude_analyzer.py  # Claude Opus 4.6 调用 + EnhancedThesis schema
├── report/
│   ├── renderer.py         # render_markdown / render_html / render_pdf
│   └── template.md.j2      # 唯一的报告模板
└── education/
    ├── analogy_teacher.py  # 8 个类比:融资=升级/稀释=蛋糕/...
    └── quest_unlock.py     # 闯关解锁进度
```

---

## 4. 扩展点

### 4.1 新增一家 fixture 公司

```bash
# 最小 JSON (itjuzi 源):
cat > examples/fixtures/小米.json <<'JSON'
{
  "sources_hit": ["fixtures"],
  "itjuzi": {
    "industry": "硬件",
    "one_liner": "智能手机+IoT 生态",
    "region": "cn",
    "founders": [{"name": "雷军", "title": "创始人/CEO", "background": "..."}],
    "rounds": [...]
  }
}
JSON

vc-research analyze "小米" -o 小米.md
```

### 4.2 新增分析模块

1. 在 `schema.py` 定义输出 Pydantic 模型(例如 `ESGScore`)
2. 在 `modules/esg.py` 写 `analyze_esg(raw) -> ESGScore`
3. 在 `modules/__init__.py` 导出
4. 在 `schema.VCReport` 加字段
5. 在 `cli.py` 串到调用链
6. 在 `template.md.j2` 加一段渲染
7. 在 `tests/test_smoke.py` 加断言

### 4.3 接入新数据源(Phase 2)

在 `data_sources/` 下新建 `itjuzi_client.py`,实现:

```python
class ITJuziClient:
    def __init__(self, api_key: str): ...
    def search(self, company_name: str) -> dict | None: ...
```

在 `DataAggregator.fetch` 的 `use_fixtures=False` 分支里调用它,把返回值赋给 `raw.itjuzi`。

关键: 返回的 dict 结构需要匹配 fixtures 的格式,否则 7 个模块要改。建议先把 fixtures 的 JSON schema 固定下来再接 API。

### 4.4 新增类比教学

编辑 `education/analogy_teacher.py` 的 `_ANALOGIES` dict,新增一个 key。然后在 `report/template.md.j2` 相应章节 `{{ analogies.新key }}` 即可。

---

## 5. 测试策略

```
tests/
├── test_smoke.py        # 3 家标杆案例 end-to-end 烟雾测试 + 教育层自检
└── test_edge_cases.py   # 边界/负路径/数值回归(当前 40+ 条)
```

**新改动必测**:
- 新增模块:写一条 smoke 断言(verdict/overall_level/关键金额)
- 修复 bug:写一条回归测试,命名 `test_xxx_does_not_crash`
- 改变估值/风险逻辑:更新 `BENCHMARKS` dict,确认 3 家标杆裁决不漂移

---

## 6. 依赖与版本策略

- `requirements.lock`: 76 个依赖固定版本,用于 CI/alpha 复现
- `pyproject.toml` 只写 `>=` 下限,便于开发迭代
- 锁定版本 6 个月更新一次(看 CHANGELOG 决定主版本跳跃)

---

## 7. 未完工清单(技术债)

见 `CHANGELOG.md`。最主要的三条:

1. **数据源抽象**: Phase 2 前先抽一个 `DataSource` Protocol,统一 fixtures / ITJuzi / Crunchbase 接口
2. **bleach 替代正则 XSS**: 当前 `_sanitize_html` 简单正则,Phase 2 换 `bleach` 白名单库
3. **全模块 logging**: 当前只有 `llm/claude_analyzer.py` 有 logger,其他 6 模块静默
