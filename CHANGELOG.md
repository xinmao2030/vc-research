# Changelog

所有值得记录的改动都会出现在这个文件里。
格式参考 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/);
遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Planned
- Phase 2: IT桔子 / Crunchbase API 真实接入(当前仅骨架)
- Phase 3: Claude 推理深度增强 + 向量检索对标
- Phase 4: Next.js Web Dashboard

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
