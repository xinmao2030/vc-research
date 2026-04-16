# Fixture 自动交叉校核 · 2026-04-16

由 `tools/cross_verify.py` 并行 HTTP + 正则匹配生成。

| 级别 | 含义 |
|---|---|
| 🟢 | fixture 与权威源一致 |
| 🟡 | 部分一致 (如年月对但日差) |
| 🔴 | 不一致 — 需要修正 |
| ⚪ | 源抓取失败 / 模式未命中 |

## 商汤科技

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| ⚪ | `汤晓鸥_still_active` | False | 源中未找到匹配片段 (pattern 可能过严) | [SenseTime](https://en.wikipedia.org/wiki/SenseTime) |
| 🟢 | `itjuzi.rounds[ipo].announce_date_2021-12-30` | 2021-12-30 | December 2021 | [SenseTime](https://en.wikipedia.org/wiki/SenseTime) |
| 🟢 | `OFAC_sanctions_2021-12` | 2021-12-10 OFAC | December 2021 | [SenseTime](https://en.wikipedia.org/wiki/SenseTime) |

## 字节跳动

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🟢 | `张一鸣_still_active` | True | Chairman | [Zhang_Yiming](https://en.wikipedia.org/wiki/Zhang_Yiming) |
| 🟡 | `founded_2012` | 2012-03-09 | 2012 | [ByteDance](https://en.wikipedia.org/wiki/ByteDance) |
| 🟡 | `TikTok_Musical.ly_acq_2017-11` | 2017-11 | 2017 | [TikTok](https://en.wikipedia.org/wiki/TikTok) |
| 🟡 | `Douyin_launch_2016-09` | 2016-09 | September 2016 | [Douyin](https://en.wikipedia.org/wiki/Douyin) |

## 小米

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🟡 | `itjuzi.founded_date` | 2010-04-06 | April 2010 | [Xiaomi](https://en.wikipedia.org/wiki/Xiaomi) |
| 🟡 | `itjuzi.rounds[ipo].announce_date` | 2018-07-09 | July 2018 | [Xiaomi](https://en.wikipedia.org/wiki/Xiaomi) |
| 🟢 | `itjuzi.headquarters(北京)` | 北京 | Beijing | [Xiaomi](https://en.wikipedia.org/wiki/Xiaomi) |
| 🟡 | `SU7_launch_2024-03-28` | 2024-03-28 | March 2024 | [Xiaomi_SU7](https://en.wikipedia.org/wiki/Xiaomi_SU7) |
| 🟢 | `雷军_Kingsoft_background` | 武汉大学计算机系,金山软件 1992 加入 / 1998 任 | Kingsoft | [Lei_Jun](https://en.wikipedia.org/wiki/Lei_Jun) |

## 百济神州

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🟢 | `itjuzi.legal_name→BeOne` | BeOne Medicines, Ltd. (原百济神州 B | BeOne Medicines | [BeOne_Medicines](https://en.wikipedia.org/wiki/BeOne_Medicines) |
| 🟢 | `rebrand_2024-11-14` | 2024-11-14 | 14 November 2024 | [BeOne_Medicines](https://en.wikipedia.org/wiki/BeOne_Medicines) |
| 🟢 | `ticker_ONC_2025-01` | 2025-01 ONC | OnC | [BeOne_Medicines](https://en.wikipedia.org/wiki/BeOne_Medicines) |
| 🟢 | `Amgen_2019_stake_20.5%` | 20.5% / $2.7B | 20.5% | [BeOne_Medicines](https://en.wikipedia.org/wiki/BeOne_Medicines) |
| 🟢 | `BRUKINSA_FDA_2019-11` | 2019-11 | November 2019 | [Zanubrutinib](https://en.wikipedia.org/wiki/Zanubrutinib) |
| 🟡 | `Tislelizumab_FDA_2024-03` | 2024-03 | March 2024 | [Tislelizumab](https://en.wikipedia.org/wiki/Tislelizumab) |

## 蔚来

| 级别 | 字段 | fixture | 权威源 | 源 URL |
|---|---|---|---|---|
| 🟡 | `itjuzi.rounds[ipo].announce_date` | 2018-09-12 | September 2018 | [Nio_(car_company)](https://en.wikipedia.org/wiki/Nio_(car_company)) |
| 🟡 | `itjuzi.founded_date` | 2014-11-25 | 2014 | [Nio_(car_company)](https://en.wikipedia.org/wiki/Nio_(car_company)) |
| 🔴 | `换电站数量_2250_level` | 换电网络护城河 (2500+ 换电站) + 高端品牌定位 + | 2250 battery swap stations | [Battery_swapping](https://en.wikipedia.org/wiki/Battery_swapping) |

**小结**: 21 条规则 / 🟢 10 / 🔴 1 / ⚪ 1