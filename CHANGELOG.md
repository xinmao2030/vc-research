# Changelog

所有值得记录的改动都会出现在这个文件里。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/);
遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Planned
- Phase 2: IT桔子 / Crunchbase / Tushare API 真实接入(当前仅骨架)
- Phase 3: Claude 推理深度增强 + 向量检索对标
- Phase 4: Next.js Web Dashboard

---

## [0.1.16] - 2026-04-20

### Added
- `Product` / `CustomerCase` schema：产品详情（描述/参数/图片）、客户合作案例（内容/成果）
- `Milestone.impact` 字段：里程碑事件对公司发展的意义
- Dashboard 搜索历史栏：首页展示搜索过的公司卡片，持久化到磁盘
- LLM 数据可信度提示横幅：LLM 生成的报告顶部警告
- 9 个新测试（Product/CustomerCase/Milestone/Verdict/Profile 兼容）→ 81/81

### Changed
- LLM Prompt 大幅增强：创始人完整履历（学历/籍贯/职业经历）、每轮融资全部投资方档案、产品详细规格、客户合作案例、里程碑覆盖至 2025-2026
- 默认模型 `qwen3:32b` → `qwen3:8b`（解决推断超时），超时 180s → 300s
- Verdict 措辞 VC 化：推荐→参投、强烈推荐→强烈参投
- 报告模板渲染新字段：产品章节/客户案例章节/里程碑增加影响列
- Dashboard 错误页优化：明确冷启动超时提示 + 折叠排查清单

## [0.1.15] - 2026-04-16

### Changed
- README 顶部加一级市场定位声明：面向 VC/天使/战投评估未上市企业，不提供二级市场买卖建议
- README 标杆案例表格上方加教学样本注释：标杆企业作为"从 VC 轮到上市"的成功轨迹样本
- CLI help 文案改为"一级市场创投分析系统（评估未上市 / Pre-IPO 企业）"

## [0.1.14] - 2026-04-16

### Changed — 新手友好度升级 (Designer P0)

- **金额人性化**: 研报模板 / CLI 进度行全部从 `$9,800,000,000` 改为 `$98.00 亿` (中文) 或 `$9.80B` (英文),共替换 28 处模板格式串
- `render_markdown` 模板注册 `money_cn` / `money_en` Jinja 过滤器
- CLI `history` 命令的 `_fmt_usd` 改用 `format_money_en` 复用逻辑
- 6 份样例研报 `examples/reports/*.md` 全部用新格式重生成

### Added
- `modules.valuation.InsufficientValuationError` — 无 ARR/GMV/TAM/最新轮次任一估值信号时抛错 (QA 报告 BUG-2),替代此前静默返回 `$0-$0`
- 无财务/市场规模数据但有最新轮次 → 自动降级用"锚点法 ±20%" 单点兜底 (不再依赖 $0)
- `docs/live-mode-setup.md` — Ollama + Qwen3 完整配置指南 (安装 / 拉模型 / 缓存 / FAQ)
- `docs/troubleshooting.md` — 覆盖 10+ 类故障: 安装 / analyze / --llm / --live / PDF / history / SEC / cross_verify

### Fixed
- CLI analyze 命令在估值失败时 `raise typer.Exit(code=3)` (之前静默继续)

---

## [0.1.13] - 2026-04-16

### Security
- **XSS 修复**: `renderer._sanitize_html` 之前允许 `href="javascript:..."` / `data:text/html` / `vbscript:` URL scheme 通过,v0.1.13 新增 `_DANGEROUS_URL_ATTRS` 正则剥离 `href/src/action/formaction/xlink:href/background/poster` 属性里的危险 scheme (7 组新测试覆盖大小写混淆/单双引号/data URI/vbscript)

### Fixed — public repo 首日门面修缮
- `docs/quickstart.md` 死示例:`字节跳动/商汤科技/蔚来` → `影石创新/银诺医药/比贝特医药` (v0.1.11 已替换 fixture,quickstart 未同步,新用户照做会 FileNotFoundError)
- `requirements.lock` L72 版本漂移:`vc-research==0.1.0` → `0.1.13`
- quickstart 新增 `vc-research history` 命令指引 (v0.1.12 已实现但入口文档缺失)

### Added
- `.github/workflows/test.yml` — push/PR 触发 uv + pytest on Python 3.10-3.12 矩阵
- `SECURITY.md` — 安全漏洞披露流程 (GitHub advisory + email)

---

## [0.1.12] - 2026-04-16

### Added — 研报历史记录

- 新增 `src/vc_research/history.py` — 追加式 JSONL 持久化 (`~/.vc-research/history.jsonl`)
- 每次 `vc-research analyze` 自动追加一条记录(裁决/估值/公允区间/风险/轮次/报告路径/数据源/增强标记)
- 新增 `vc-research history` 命令 — Rich 表格渲染,裁决/风险色标,支持 `--limit N` `--full-path` 和公司名过滤
- 环境变量 `VC_HISTORY_PATH` 可覆盖默认路径(便于测试隔离)
- 7 个单测覆盖 record/load 往返、排序、过滤、limit、损坏行容错、env 覆盖

### Changed
- 版本号 0.1.11 → 0.1.12 (pyproject.toml / `__init__.py` / `schema.py` 三处同步)

---

## [0.1.11] - 2026-04-16

### Changed — 标杆案例迁移:2024-2026 IPO 代表 6 家

**替换前**(v0.1.0 - v0.1.10 的 5 家老牌巨头):
小米 / 蔚来 / 百济神州 (BeOne) / 商汤科技 / 字节跳动

**替换后**(覆盖 5 板块 × 3 行业 × 4 裁决档位):

| 公司 | 赛道 | 上市 | 代码 | 裁决 |
|---|---|---|---|---|
| 影石创新 (Insta360) | 消费电子 · 全景相机 | 2025-06 科创板 | 688775.SH | 观望 |
| 澜起科技 (Montage) | 半导体 · 内存接口芯片 | 2019-07 科创板 + 2026-01 A+H | 688008.SH / 2827.HK | 观望 |
| 银诺医药 (Innogen) | 医药 · GLP-1 长效 | 2025-08 港股 18A | 2591.HK | 推荐 |
| 比贝特医药 (BeBetter) | 医药 · HDAC 小分子 | 2025-10 科创板 | 688759.SH | 推荐 |
| 汉朔科技 (Hanshow) | 硬件 · 电子价签 ESL | 2025-03 创业板 | 301275.SZ | 回避 |
| 强一股份 (Maxone) | 半导体 · MEMS 探针卡 | 2025-12 科创板 | 688809.SH | 回避 |

### Added
- 6 份新 fixture JSON,每份由独立 subagent 并行 WebFetch 3-5 权威源交叉验证后生成
- 6 份新 markdown 研报 `examples/reports/*.md` (每份 334-362 行,7 模块完整)
- README 新增「标杆案例」一览表,含行业/上市地/裁决速查
- `tools/cross_verify.py` 规则表重写:16 条新规则(2-4/公司),<3s 出审计报告
- `HkexSource` symbology 补银诺 (02591) / 澜起 H 股 (02827);精简原有不必要别名

### Fixed — 版本号漂移
- `pyproject.toml` / `__init__.py` / `schema.py` 三处 `0.1.0` 同步为 `0.1.11`
  (Release Manager 审查发现:此前 CHANGELOG 已到 0.1.10 而代码仍写 0.1.0)

### Breaking
- 删除 `examples/fixtures/{小米,蔚来,百济神州,字节跳动,商汤科技}.json` 及对应报告
- `test_smoke.CASES` / `test_edge_cases.BENCHMARKS` 迁移至新 6 家
- `cross_verify.RULES` 21 条旧规则全量替换
- 外部调用者若直接 import 这些旧 fixture 文件会 FileNotFoundError — 请改用新 6 家

### Tests
- 64/64 全绿 (+4 vs 0.1.10:BENCHMARKS 从 4→6 家)

### Rationale (多职能综合评估 2026-04-16)
- **CEO**: 原 5 家是"已充分定价的巨头",新 6 家覆盖刚 IPO 的行业 Top 3,对零基础用户"学以致用"的教育价值更高
- **Designer**: 新公司都处于"信息密度适中 + 价值未被市场充分消化"的阶段,适合做"渐进披露 + 闯关"设计的标杆
- **Plan**: 为 Phase 2.2 的新闻聚合源 + cross_verify 规则扩展到 50+ 条铺路

---

## [0.1.10] - 2026-04-16

### Added — Phase 2.1 真实数据源骨架

- **`SecEdgarSource`**: SEC EDGAR 公开 JSON API 接入
  - `data.sec.gov/submissions/CIK{10}.json` → 公司基本信息 + 最近 10-K/20-F/6-K
  - `data.sec.gov/api/xbrl/companyfacts/CIK{10}.json` → XBRL 财务事实
    (Revenues/NetIncomeLoss/Cash/Assets 最新 3 个 FY)
  - User-Agent 通过 `SEC_EDGAR_UA` 环境变量配置(默认
    `vc-research/0.1 xinmao2030@gmail.com`,SEC 要求真实联系方式)
  - CIK 映射覆盖 蔚来 / 百济神州(BeOne Medicines ONC)
  - Live 验证:NIO → ticker NIO@NYSE, HQ Shanghai;
    BeOne → ticker ONC@Nasdaq, HQ Basel(印证 fixture 2025-05 redomicile)
  - 6 单元测试(mocked httpx),`-m live` 跑真实网络

- **`HkexSource`**: 港交所静态 symbology(最简骨架)
  - 覆盖 18 个名称别名 → 10 家港股代码
    (小米/蔚来/百济/商汤/阿里/京东/腾讯/美团/快手)
  - 说明:HKEX 无官方 JSON API(JS 渲染),本 Phase 仅提供
    profile URL + search URL 构造器;Phase 2.2 接 AAStocks/Yahoo HK
  - `lookup_hk_ticker()` 供 `cross_verify.py` 直接校验港股代码

- **`DataAggregator.enable_sec_edgar`**: 显式开关,避免测试默认触网

### Tests
- 60/60 全绿(+11 vs 0.1.9:SEC EDGAR 6 + HKEX 5)

---

## [0.1.9] - 2026-04-16

### Added — 并行交叉验证工具 + 第二轮广度扩展

- **`tools/cross_verify.py`**: httpx.AsyncClient 并行抓 Wikipedia/官网多源,
  按公司定义的规则表正则匹配 fixture 字段,输出
  `docs/data-audit-auto-YYYY-MM-DD.md`,分级 🟢 🟡 🔴 ⚪
  - 单公司验证:`uv run python tools/cross_verify.py --company 小米`
  - 全量:`uv run python tools/cross_verify.py`
  - 6 规则并行 1 秒出报告,支持扩展到 50+ 规则仍 <10s
- **fixture 第二轮深化** (基于并行 WebFetch 15+ 源):
  - 字节跳动:张一鸣 `still_active: false → true`(仍任 Chairman + >50%
    投票权),补 Forbes 2025-05 身价 $65.5B / 2024 中国首富
  - 小米:雷军背景补金山 1992-2007 轨迹 + joyo.com 卖 Amazon 细节 +
    Forbes 2025-05 身价 $42.6B;SU7 补 2024 交付 139,487 辆
  - 百济神州:BRUKINSA 5 项 FDA 适应症时间线 / Tislelizumab FDA 2024-03
    EMA 2023-09 / 2024 全球销售 $13 亿写入 sources_hit

### Memory
- 新增 `feedback_vc_research_always_crossverify.md`:
  vc-research 数据任务默认第一步并行交叉验证,不等用户问

### Tests
- 49/49 全绿

---

## [0.1.8] - 2026-04-16

### Changed — 数据源可信度清理: 替换假占位 + 修正标杆数据

- **sources_hit 真实化**: 所有 5 家 fixture 清除 `itjuzi(模拟)` / `crunchbase(模拟)`
  字样,统一改为 `[类别] 描述 <URL>` 结构化格式(类别含:招股书/年报/IR/工商/
  融资聚合/新闻/监管/合作披露/分析师/官网)。Python-markdown 原生 autolink 把
  `<https://...>` 渲染为可点击链接,模板零改动
- **数据修正**:
  - 百济神州 John V. Oyler 履历由 "Telarus 前 CEO" 更正为
    "BioDuro 创始人 / Genta 前执行副总裁 / 普林斯顿物理 + 麦肯锡背景"(事实核查)
  - 百济神州 rounds 拆分:2020-07-13 PIPE 定增 $2.08B 与 2021-12-15 科创板 IPO
    $3.5B 分成两轮,不再混为一谈
  - 商汤科技 汤晓鸥 founder 补 `still_active: false`(2023-12 辞世)
- **覆盖面**: 字节跳动 9 源 / 小米 8 源 / 蔚来 9 源 / 百济神州 11 源 / 商汤 9 源

### Tests
- 49/49 全绿,零 `(模拟)` 残留

---

## [0.1.7] - 2026-04-16

### Added — 全面图表化: 表格、进度条、Mermaid 图表

- **表格化改造**: 几乎所有 bullet 列表改为 Markdown 表格
  (42 个 HTML 表,较之前翻 4 倍),所有结构化数据对齐扫读
- **Unicode 进度条**: 团队评分 + 7 Powers 护城河评分新增可视化
  `████████░░` 条,不依赖外部资源,终端/网页双通用
- **健康度徽章**: 单位经济学(LTV/CAC、毛利率、回本周期)按阈值自动标注
  ✅ 健康 / 🟡 中等 / ⚠️ 偏低;风险等级 🔴 🟡 🟢 三色编码
- **Mermaid 图表**: 产业链 `flowchart LR` (上游→中游→下游);
  估值成长曲线 `xychart-beta`(基于 post_money 序列自动绘制)
- **Dashboard 支持**: 按需加载 `mermaid@10` ESM 模块,暗色模式自动切主题;
  `_inject_tooltips` 在抽出 mermaid 块之后再做术语注入,避免 `<abbr>`
  破坏图表源码

### Tests
- 49/49 全绿;研报页面 `<table>` 数量 10 → 42

---

## [0.1.6] - 2026-04-15

### Added — 研报深度加厚 (Profile / Funding / Thesis / Industry 四模块)

- **模块 1 · 企业画像**: 新增 `executives` / `products` / `key_customers` /
  `milestones` / `website`;`founders` 加 `still_active` + `current_role`
  (支持"创始人已离任"场景)
- **模块 2 · 融资轨迹**: 每轮新增 `pre_money_valuation_usd` / `share_class` /
  `use_of_proceeds`;`investor_details` 完整投资方档案(机构类型 / AUM / 代表
  案例 / 本轮投资逻辑)渲染为每轮的投资方详情卡片
- **模块 3 · 投资依据**: `team_analysis` / `market_analysis` /
  `unit_economics_analysis` / `growth_analysis` 四段深度叙事字段;
  `moat_analysis` 采用 Hamilton Helmer《7 Powers》框架 7 维度打分;
  `competitors_detailed` 表格化竞品对比;`bull_detailed` / `bear_detailed`
  带论据与证据列表
- **模块 4 · 产业趋势**: `sub_segments`(赛道细分 + 规模/增速)/ `value_chain`
  (上中下游玩家)/ `top_players`(行业头部玩家档案)/ `growth_drivers` /
  `barriers_to_entry` / `industry_key_metrics` 六个深化字段
- **LLM Prompt**: Ollama researcher prompt 重写要求全部新字段,
  `num_predict` 4096 → 8192 支撑更大 JSON 产出
- **标杆 fixture**: `examples/fixtures/字节跳动.json` 扩充示范数据
  (230 → 370+ 行),研报输出从 ~230 行增至 ~370 行
- **文档**: `docs/data-source-spec.md` 补全所有新字段契约与可选性说明

### Tests
- 49/49 全绿;新字段皆可选,既有 benchmark 数据零改动即可通过

---

## [0.1.5] - 2026-04-15

### Added — 本地 LLM 实时研究员 (任意公司名 → 研报)
- `src/vc_research/data_sources/ollama_researcher.py` —
  `OllamaResearcher` DataSource,调本地 Ollama + Qwen3 32B,
  按 `docs/data-source-spec.md` 契约产出结构化 JSON
- 聚合器兜底链:fixtures → Phase 2 API 占位 → **OllamaResearcher**
- 磁盘缓存 `~/.vc-research/llm_cache/{model}__{company}.json`,
  TTL 30 天(可通过 `VC_LLM_CACHE_TTL_DAYS` 改);冷启 ~100s,热启 0ms
- 研报模板自动识别 LLM 数据源,顶部追加 🤖 警告条
  ("LLM 推断,需交叉核实")
- Dashboard 首页加搜索框 + 提交后的黄色"60-120s 推断中"提示
- Dashboard `/clear-cache` 端点清空磁盘 + 进程缓存,首页带入口
- CLI `--live` flag — 未命中 fixtures 时自动走 Qwen3(CLI 也支持任意公司)
- 默认 `enable_llm_research=False` 保证测试确定性,
  仅 dashboard / CLI `--live` 显式开启

### Tests
- 49/49 仍通过(新功能不破现有 benchmark)

---

## [0.1.4] - 2026-04-15

### Added — Dashboard 教育体验升级
- Dashboard 首页改为实时从 fixtures 构建研报卡片,不再依赖
  `examples/reports/` 预生成 md,打开即看 4 家标杆全貌
- 卡片元信息:赛道 badge + 裁决 badge (色)+ 风险等级 badge (色)+
  轮次+最新估值+一句话描述
- **术语 hover 提示** (设计师 P2):TAM/SAM/SOM/LTV/CAC/ARR/CAGR/
  护城河/稀释/跑道/优先清算权 等 24 个核心术语在研报正文中自动
  包 `<abbr title="类比解释">`,鼠标悬停即显示,无需 JS
- `/glossary` 路由渲染完整术语表
- 暗色模式 abbr 下划线+虚线样式优化

---

## [0.1.3] - 2026-04-15

### Added — Phase 2 接入准备完成
- `docs/data-source-spec.md` — fixtures JSON schema 契约,Phase 2 真实 API
  接入的目标格式 + 字段级别的宽容性承诺
- `examples/fixtures/小米.json` — 第 4 家标杆案例 (硬件/消费电子赛道),
  验证架构扩展到多样化赛道无代码改动
- `BENCHMARKS` 测试扩展到 4 家,全量 49/49 通过

---

## [0.1.2] - 2026-04-15

### Added — Milestone 1 教育层落地 + Phase 2 接口准备
- 报告模板自动注入 8 个类比教学(融资=升级 / 稀释=蛋糕 / 跑道=血条 /
  TAM=三层海洋 / 护城河=城堡水沟 / LTV/CAC=渔夫ROI / 估值=房屋评估 /
  优先清算=救生艇)
- CLI 闯关进度条:每完成一个模块点亮并解锁下一关,保存进度到
  `~/.vc-research/progress/{company}.json`
- CLI 首屏免责声明 banner
- `docs/glossary.md` — 50+ 创投术语表,附类比
- `docs/api.md` — 对外 Python/CLI 接口文档
- `docs/quickstart.md` — 零基础用户 10 分钟上手指南
- `docs/architecture.md` — 数据流/扩展点/贡献指南
- `data_sources/base.py` — `DataSource` Protocol,为 Phase 2 统一接口
- `FixturesSource` / `ITJuziSource` / `CrunchbaseSource` 骨架
- `DataAggregator` 重构为多源级联,保留向后兼容

### Tests
- 3 条集成测试:Crunchbase fallback / 稀释累积链 / 无 industry 降级
- 全量 47/47 通过

---

## [0.1.1] - 2026-04-15

### Added
- `LICENSE` (MIT) + `CHANGELOG.md` + `.gitignore`
- `utils.py` 统一 `_to_decimal` / `parse_funding_stage` (消除 4 处重复)
- 按 `industry` 查表的估值倍数字典(SaaS / 电商 / 硬件 / AI / 新能源各不同)
- LLM 返回 Pydantic schema 校验 + 降级到 base 逻辑
- 边界条件测试:空 fixture / 坏 JSON / 极值 / XSS 注入
- 标杆案例数值断言测试
- `requirements.lock` 锁定依赖版本
- `.env.example`
- README 补系统依赖章节(weasyprint 的 pango/cairo 说明)
- `web/dashboard.py` — Phase 4 Web Dashboard 的 MVP 起点

### Fixed
- **BUG-001**: Founder 字段为 null 时 Pydantic 验证崩溃
- **BUG-002**: `--pdf` 在 macOS 默认环境因 libgobject 缺失崩溃 → 优雅降级
- **BUG-003**: 空公司静默产生零估值报告 → 抛出 `InsufficientDataError`
- **BUG-004**: 公司名注入 XSS → Jinja2 autoescape + html.escape

---

## [0.1.0] - 2026-04-15

### Added
- 7 层分析框架骨架(企业画像 / 融资轨迹 / 投资依据 / 产业趋势 / 估值分析 / 风险矩阵 / 投资建议)
- 核心数据模型(Pydantic `VCReport` 及其子模型)
- CLI 入口 `vc-research analyze "企业名"` + `list-examples`
- 3 家标杆案例 fixtures (字节跳动 / 商汤科技 / 蔚来)
- Claude Opus 4.6 推理层封装(支持 prompt caching)
- Markdown / PDF 研报渲染(Jinja2 + weasyprint)
- 闯关式教育层(QuestProgress + 8 个核心概念类比教学)
- 烟雾测试:3 个标杆案例端到端跑通
