# Fixture 自动交叉校核 · 2026-04-16

由 `tools/cross_verify.py` 并行 HTTP + 正则匹配生成。

| 级别 | 含义 |
|---|---|
| 🟢 | fixture 与权威源一致 |
| 🟡 | 部分一致 (如年月对但日差) |
| 🔴 | 不一致 — 需要修正 |
| ⚪ | 源抓取失败 / 模式未命中 |

## 百济神州

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🟢 | `itjuzi.legal_name` | BeOne Medicines, Ltd. (原百济神州 B | BeOne Medicines | [BeOne_Medicines](https://en.wikipedia.org/wiki/BeOne_Medicines) |

**小结**: 1 条规则 / 🟢 1 / 🔴 0 / ⚪ 0