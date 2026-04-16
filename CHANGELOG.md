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
