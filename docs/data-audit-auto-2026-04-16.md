# Fixture 自动交叉校核 · 2026-04-16

由 `tools/cross_verify.py` 并行 HTTP + 正则匹配生成。

| 级别 | 含义 |
|---|---|
| 🟢 | fixture 与权威源一致 |
| 🟡 | 部分一致 (如年月对但日差) |
| 🔴 | 不一致 — 需要修正 |
| ⚪ | 源抓取失败 / 模式未命中 |

## 强一股份

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🔴 | `MEMS_probe_card_category` | 晶圆测试 - MEMS 探针卡 | Probe card | [Probe_card](https://en.wikipedia.org/wiki/Probe_card) |
| ⚪ | `FormFactor_competitor` | FormFactor (美),Technoprobe (意) | 源抓取失败: lient error '404 Not Found' for u | [FormFactor](https://en.wikipedia.org/wiki/FormFactor) |

## 影石创新

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🟡 | `itjuzi.founded_date_2015` | 2015-07-01 | 2015 | [Insta360](https://en.wikipedia.org/wiki/Insta360) |
| 🟢 | `itjuzi.headquarters(深圳)` | 深圳 | Shenzhen | [Insta360](https://en.wikipedia.org/wiki/Insta360) |
| 🔴 | `刘靖康_南大_founder` | 1991 年生,广东中山人,南京大学软件学院 2014 届; | JK Liu | [Insta360](https://en.wikipedia.org/wiki/Insta360) |

## 比贝特医药

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| ⚪ | `钱长庚_founder` | 钱长庚 | 源抓取失败: SSL: CERTIFICATE_VERIFY_FAILED] c | [https://www.bebettermed.com/](https://www.bebettermed.com/) |
| 🔴 | `HDAC_pipeline` | 小分子创新药 (肿瘤/自免/代谢, HDAC+PI3K/CD | Histone deacetylase | [Histone_deacetylase_inhibitor](https://en.wikipedia.org/wiki/Histone_deacetylase_inhibitor) |

## 汉朔科技

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🔴 | `ESL_category` | 电子价签 ESL | Electronic shelf label | [Electronic_shelf_label](https://en.wikipedia.org/wiki/Electronic_shelf_label) |
| 🟢 | `VusionGroup_competitor` | VusionGroup (SES-imagotag,法国,全 | VusionGroup | [VusionGroup](https://en.wikipedia.org/wiki/VusionGroup) |
| ⚪ | `founded_2012` | 2012-07-01 | 源中未找到匹配片段 (pattern 可能过严) | [Electronic_shelf_label](https://en.wikipedia.org/wiki/Electronic_shelf_label) |

## 澜起科技

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🟡 | `itjuzi.founded_date_2004` | 2004-05-27 | 2004 | [Montage_Technology](https://en.wikipedia.org/wiki/Montage_Technology) |
| 🟡 | `NASDAQ_IPO_2013-09` | 2013-09-26 | 2013 | [Montage_Technology](https://en.wikipedia.org/wiki/Montage_Technology) |
| 🔴 | `STAR_IPO_2019-07` | 2013-09-26 | 2019 | [Montage_Technology](https://en.wikipedia.org/wiki/Montage_Technology) |
| 🔴 | `DDR_memory_interface_core_business` | 内存接口芯片 + 高速互连芯片 (DDR4/DDR5 RCD | Memory Interface | [Montage_Technology](https://en.wikipedia.org/wiki/Montage_Technology) |

## 银诺医药

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| ⚪ | `HKEX_2591_IPO_2025-08` | 2591.HK 2025-08-15 | 源中未找到匹配片段 (pattern 可能过严) | [https://www.hkexnews.hk/](https://www.hkexnews.hk/) |
| 🟢 | `GLP1_category` | GLP-1 创新药 | GLP-1 | [GLP-1_receptor_agonist](https://en.wikipedia.org/wiki/GLP-1_receptor_agonist) |

**小结**: 16 条规则 / 🟢 3 / 🔴 6 / ⚪ 4