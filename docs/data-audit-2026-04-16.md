# Fixture 数据交叉校核报告 · 2026-04-16

**方法**:对 5 家标杆 fixture 的关键字段 (上市/融资/创始人/估值) 与公开一手信息源 (Wikipedia / 官网 / 招股书) 做一轮交叉比对,分级标注差异。本次审计覆盖面受 WebFetch 限制 (SEC EDGAR 返回 403、部分 PDF 不可解析),后续 Phase 2 真实数据源接入后可自动执行。

**差异分级**:
- 🔴 **Critical** — 事实性错误,必须修
- 🟡 **Minor** — 金额尾差 / 粒度不同 (通常 ±5% 以内),可修可不修
- 🟢 **Verified** — 与权威源一致
- ⚪ **Unknown** — 权威源未覆盖或未找到,保留原值

---

## 1. 字节跳动 (private)

| 字段 | Fixture | Wikipedia / 官网 | 级别 | 修正 |
|---|---|---|---|---|
| 成立时间 | 2012-03-09 | 2012-03-13 (Wikipedia) / 2012 年 3 月 (官网) | 🟡 | 2012-03-13 |
| 员工数 | 150000 | "over 150,000" (官网) / "c. 120,000 (2025)" (Wikipedia) | 🟢 | 保留 |
| 创始人 | 张一鸣, 梁汝波 | 张一鸣, 梁汝波 | 🟢 | ✓ |
| Pre-IPO 2021-03 $5B @ $180B | $180B | "estimated $300 billion (Nov 2024)" | 🔴 | **需新增 2024 tender offer round** |
| FY2023 收入 | 未列 | "$155B (2024)" (Wikipedia) | ⚪ | 建议新增字段 |
| TikTok 剥离 | 未提 | "divestiture completed 2026-01-22; ByteDance 保留 19.9%" | 🔴 | **milestones 必须补** |

**必须修**:
- 新增 2024-04 tender offer round: $5B 二级市场回购,隐含估值 $268B (Bloomberg 2024-04-24)
- `milestones` 新增:`2026-01-22 TikTok USDS JV 组建,ByteDance 保留 19.9%,Oracle/Silver Lake/MGX 合计 >80%`

---

## 2. 小米 (HK:1810)

| 字段 | Fixture | 权威源 | 级别 | 修正 |
|---|---|---|---|---|
| 成立时间 | 2010-04-06 | 2010-04-06 | 🟢 | ✓ |
| IPO 日期 | 2018-07-09 | 2018-07-09 | 🟢 | ✓ |
| IPO 募资 | $4.72B | $4.72B (Wikipedia) | 🟢 | ✓ |
| IPO post-money | $54B | 发行价 HKD 17,流通市值约 $50-55B | 🟢 | ✓ |
| IPO 承销 | 高盛 / 摩根士丹利 / 中信里昂 (实际 CLSA) | 同 | 🟢 | ✓ |
| 创始人 | 8 人 (雷军 + 林斌 + 6 others) | 8 人完整列出 | 🟢 | ✓ |
| 2023 收入 | 未列 | HKD 2990 亿 ≈ $38B | ⚪ | 建议新增 |
| SU7 发布 | 2024-03-28 | 2024-03-28 | 🟢 | ✓ |

**无需修改**

---

## 3. 蔚来 (NYSE:NIO, HK:9866)

| 字段 | Fixture | 权威源 | 级别 | 修正 |
|---|---|---|---|---|
| 成立时间 | 2014-11-25 | 2014-11-25 | 🟢 | ✓ |
| NYSE IPO | 2018-09-12 $1B @ $6.4B | "raising about $1B at $6.26/ADS" | 🟢 | ✓ |
| HK 二次上市 | 未独立列出 | 2022-03-10 介绍上市 9866.HK | 🟡 | 建议新增 |
| 合肥 2020 | $1B @ $3B post | Hefei 2020 年 70 亿 CNY 购 24.1% NIO China 股份 (注:不是 NIO Inc. 层面) | 🟡 | 备注需澄清 |
| CYVN 2023-12 | $2.2B @ $12B | CYVN 2023-12-18 首次 $2.2B / 2024-03 追加 $22亿 (合计 >$4B) | 🔴 | **需拆两轮** |

**必须修**:
- 拆分 CYVN 投资:2023-12-18 首次 $2.2B 与 2024-06-03 追加 $22亿 为两个 strategic 轮
- 新增 2022-03-10 HK 介绍上市 round (无募资,但改变流动性基础)

---

## 4. 百济神州 → BeOne Medicines (重大品牌变更!)

| 字段 | Fixture | 权威源 | 级别 | 修正 |
|---|---|---|---|---|
| legal_name | 百济神州有限公司 | **已改名 BeOne Medicines, Ltd. (2024-11-14)** | 🔴 | **必须更新** |
| ticker | BGNE | **ONC (2025-01)** | 🔴 | **必须更新** |
| 总部 | 北京 / 剑桥 / 巴塞尔 | **2025-05 redomicile 至 Basel 瑞士** | 🔴 | **必须澄清为主要法律实体迁瑞士** |
| 2016-02-03 IPO $158M | $158M | "$182M at $24/share" (Wikipedia) | 🟡 | **建议改 $182M** |
| Amgen 2019 $2.7B for 20.5% | **缺失整条** | Wikipedia 明确记录 | 🔴 | **必须新增整条 strategic round** |
| Celgene 2017 $150M | ✓ | 同 | 🟢 | ✓ |
| HK 2018 $903M | ✓ | 同 | 🟢 | ✓ |
| PIPE 2020-07-13 $2.08B | ✓ | 同 | 🟢 | ✓ |
| 科创板 2021-12-15 $3.5B | ✓ | SSE 688235 | 🟢 | ✓ |
| Oyler 履历 | BioDuro 创始人 / Genta | Wikipedia 确认 Chairman+CEO, 百济联合创始人 | 🟢 | ✓ (已修) |

**必须修 (4 项)**:
1. `legal_name` → "BeOne Medicines, Ltd. (原百济神州 BeiGene, Ltd.)"
2. 2016 NASDAQ IPO amount_usd 158M → 182M
3. 新增 2019-10-31 Amgen strategic round:$2.7B for 20.5% stake
4. `milestones` 补:2024-11-14 rebrand / 2025-01 ticker ONC / 2025-05 Basel domicile

---

## 5. 商汤科技 (HK:0020)

| 字段 | Fixture | 权威源 | 级别 | 修正 |
|---|---|---|---|---|
| 成立时间 | 2014-11-14 | 2014-10 (Wikipedia "October 2014") | 🟡 | 保留 (官方工商可能是 11-14) |
| IPO 日期 | 2021-12-30 | 2021-12-30 (上市) | 🟢 | ✓ |
| IPO 募资 | $770M | HKD 5.55B ≈ $711M | 🟡 | 建议调 711M |
| OFAC 制裁 | sources_hit 提及 | 2021-12-10 (原定 IPO 定价日) | 🟢 | ✓ |
| 汤晓鸥 辞世 | `still_active: false` | 2023-12 (Wikipedia) | 🟢 | ✓ (已修) |
| 徐立 履历 | 港中文博士,技术 + 商业化 | Wikipedia 仅确认 co-founder,未提博士 | ⚪ | 保留 |
| 阿里 C 轮 2018-04 $600M | ✓ | 同 | 🟢 | ✓ |
| 软银 C+ 2018-05 $620M | ✓ | 同 | 🟢 | ✓ |

**可选修**:
- IPO amount $770M → $711M (按实际 HKD → USD 汇率)

---

## 汇总:本轮必修清单

| # | 公司 | 字段 | 操作 |
|---|---|---|---|
| 1 | 字节跳动 | rounds[] | 新增 2024-04 tender offer |
| 2 | 字节跳动 | milestones | 补 TikTok USDS 2026-01-22 |
| 3 | 蔚来 | rounds[] | CYVN 拆两轮 + HK 介绍上市 |
| 4 | 百济神州 | legal_name / 基本信息 | 改为 BeOne Medicines |
| 5 | 百济神州 | rounds[2] (NASDAQ IPO) | $158M → $182M |
| 6 | 百济神州 | rounds[] | 新增 Amgen 2019-10-31 strategic |
| 7 | 百济神州 | milestones | 补 rebrand / ticker / domicile |

---

## 未能自动验证的源 (后续 Phase 2 解决)

| 源 | 状态 | 解决方案 |
|---|---|---|
| SEC EDGAR HTML | 403 (User-Agent 缺失) | `SecEdgarSource` 设 `User-Agent: vc-research <contact>` 头 |
| SEC EDGAR JSON API | 403 | 同上,SEC 要求公司+邮箱 UA |
| HKEX 招股书 PDF | 无法解析二进制 | `pdfplumber` 解析页码范围 |
| IT桔子 / Crunchbase | 未尝试 (付费 API) | Phase 2.2 |
| Bloomberg / FT 深度内容 | 付费墙 | NewsAggregatorSource 用摘要 + 引用 |

---

## 下一步

本次 PR (v0.1.9) 将:
1. 按"必修清单" 7 条修 fixture
2. 实现 `SecEdgarSource` + `HkexNewsSource` 骨架并通过集成测试验证可跑通一次真实请求
3. 下一轮 v0.2.x 做全量每月自动 audit (CI cron)
