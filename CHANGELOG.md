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
