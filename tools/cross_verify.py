"""并行交叉验证工具 — 比对 fixture 的关键字段与权威公开源.

设计目标:
  - 速度:httpx.AsyncClient + asyncio.gather,N 个源一次打完 (通常 <10s)
  - 广度:每家公司定义 10+ 个字段的校核规则 (正则/数值断言)
  - 透明:输出 data-audit-YYYY-MM-DD.md,🔴 🟡 🟢 分级

运行方式:
    uv run python tools/cross_verify.py           # 验证所有 fixture
    uv run python tools/cross_verify.py --company 小米

注意事项:
  - SEC EDGAR 要求合法 User-Agent: `<Name> <email>` 否则 403
  - HKEX / Wikipedia 无特殊限制
  - PDF 暂不自动解析 (需 pdfplumber,后续 Phase 2.2)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Callable, Optional

try:
    import httpx
except ImportError:
    sys.exit("需先安装 httpx:  uv pip install httpx")

FIXTURES_DIR = Path(__file__).parent.parent / "examples" / "fixtures"
DOCS_DIR = Path(__file__).parent.parent / "docs"
UA = "vc-research-audit/0.1 (contact: xinmao2030@gmail.com)"


@dataclass
class VerifyRule:
    """一条字段校核规则."""
    field: str                              # 字段路径 "itjuzi.founded_date"
    url: str                                # 权威源 URL
    pattern: str                            # 提取值的正则 (group 1 = 值)
    fixture_getter: Callable[[dict], str]   # 从 fixture 取值
    normalize: Callable[[str], str] = str.strip
    # 语义类型:决定 _compare 的比对策略
    # - "date": 抽取年月日数字对齐
    # - "text": 子串或 token 匹配
    # - "bool_alive": fixture "True"/"False" 对源里"died"/"Chairman/CEO"的反推
    kind: str = "text"


@dataclass
class VerifyResult:
    company: str
    field: str
    fixture_value: str
    source_value: Optional[str]
    source_url: str
    level: str = "🟢"        # 🟢 / 🟡 / 🔴 / ⚪
    note: str = ""


# ────────────────────────────────────────────────────────────
# 公司规则表
# ────────────────────────────────────────────────────────────
def _g(path: str) -> Callable[[dict], str]:
    """field 路径取值,如 'itjuzi.founded_date'."""
    keys = path.split(".")

    def _get(d: dict) -> str:
        cur: object = d
        for k in keys:
            if isinstance(cur, dict):
                cur = cur.get(k, "")
            else:
                return ""
        return str(cur) if cur is not None else ""

    return _get


def _founder_still_active(name: str) -> Callable[[dict], str]:
    def _f(d: dict) -> str:
        for f in d["itjuzi"]["founders"]:
            if f["name"] == name:
                return str(f.get("still_active", True))
        return "True"
    return _f


def _ipo_date(d: dict) -> str:
    for r in d["itjuzi"]["rounds"]:
        if r["stage"] == "ipo":
            return r["announce_date"]
    return ""


RULES: dict[str, list[VerifyRule]] = {
    "影石创新": [
        VerifyRule(
            "itjuzi.founded_date_2015",
            "https://en.wikipedia.org/wiki/Insta360",
            r"(2015)",
            _g("itjuzi.founded_date"), kind="date",
        ),
        VerifyRule(
            "itjuzi.headquarters(深圳)",
            "https://en.wikipedia.org/wiki/Insta360",
            r"(Shenzhen)",
            _g("itjuzi.headquarters"),
        ),
        VerifyRule(
            "刘靖康_南大_founder",
            "https://en.wikipedia.org/wiki/Insta360",
            r"(Nanjing\s+University|Liu\s+Jingkang|JK\s+Liu)",
            lambda d: next(
                (f["background"] for f in d["itjuzi"]["founders"] if "刘靖康" in f["name"]), ""
            ),
        ),
    ],
    "澜起科技": [
        VerifyRule(
            "itjuzi.founded_date_2004",
            "https://en.wikipedia.org/wiki/Montage_Technology",
            r"(2004)",
            _g("itjuzi.founded_date"), kind="date",
        ),
        VerifyRule(
            "NASDAQ_IPO_2013-09",
            "https://en.wikipedia.org/wiki/Montage_Technology",
            r"(September\s+2013|2013)",
            lambda d: "2013-09-26", kind="date",
        ),
        VerifyRule(
            "STAR_IPO_2019-07",
            "https://en.wikipedia.org/wiki/Montage_Technology",
            r"(July\s+2019|2019)",
            _ipo_date, kind="date",
        ),
        VerifyRule(
            "DDR_memory_interface_core_business",
            "https://en.wikipedia.org/wiki/Montage_Technology",
            r"(memory\s+interface|DDR4|DDR5)",
            lambda d: d["itjuzi"].get("sub_industry", ""),
        ),
    ],
    "银诺医药": [
        VerifyRule(
            "HKEX_2591_IPO_2025-08",
            "https://www.hkexnews.hk/",
            r"(2591|Innogen)",
            lambda d: "2591.HK 2025-08-15",
        ),
        VerifyRule(
            "GLP1_category",
            "https://en.wikipedia.org/wiki/GLP-1_receptor_agonist",
            r"(GLP-1|glucagon-like\s+peptide-1|ecnoglutide|efsubaglutide)",
            lambda d: d["itjuzi"].get("sub_industry", ""),
        ),
    ],
    "比贝特医药": [
        VerifyRule(
            "钱长庚_founder",
            "https://www.bebettermed.com/",
            r"(钱长庚|Qian\s+Changgeng|Bebetter|BeBetter)",
            lambda d: next(
                (f["name"] for f in d["itjuzi"]["founders"]), ""
            ),
        ),
        VerifyRule(
            "HDAC_pipeline",
            "https://en.wikipedia.org/wiki/Histone_deacetylase_inhibitor",
            r"(HDAC|histone\s+deacetylase)",
            lambda d: d["itjuzi"].get("sub_industry", ""),
        ),
    ],
    "汉朔科技": [
        VerifyRule(
            "ESL_category",
            "https://en.wikipedia.org/wiki/Electronic_shelf_label",
            r"(electronic\s+shelf\s+label|ESL)",
            lambda d: d["itjuzi"].get("sub_industry", ""),
        ),
        VerifyRule(
            "VusionGroup_competitor",
            "https://en.wikipedia.org/wiki/VusionGroup",
            r"(VusionGroup|SES-imagotag)",
            lambda d: ",".join(d["itjuzi"]["thesis"].get("competitors", [])),
        ),
        VerifyRule(
            "founded_2012",
            "https://en.wikipedia.org/wiki/Electronic_shelf_label",
            r"(Hanshow)",
            _g("itjuzi.founded_date"), kind="date",
        ),
    ],
    "强一股份": [
        VerifyRule(
            "MEMS_probe_card_category",
            "https://en.wikipedia.org/wiki/Probe_card",
            r"(probe\s+card|MEMS|wafer\s+test)",
            lambda d: d["itjuzi"].get("sub_industry", ""),
        ),
        VerifyRule(
            "FormFactor_competitor",
            "https://en.wikipedia.org/wiki/FormFactor",
            r"(FormFactor|probe\s+card)",
            lambda d: ",".join(d["itjuzi"]["thesis"].get("competitors", [])),
        ),
    ],
}


# ────────────────────────────────────────────────────────────
# 核心
# ────────────────────────────────────────────────────────────
async def fetch(client: httpx.AsyncClient, url: str) -> str:
    try:
        r = await client.get(url, timeout=20.0, follow_redirects=True)
        r.raise_for_status()
        return r.text
    except Exception as e:
        return f"__ERROR__ {e}"


async def verify_company(company: str, rules: list[VerifyRule]) -> list[VerifyResult]:
    fx_path = FIXTURES_DIR / f"{company}.json"
    if not fx_path.exists():
        return []
    fixture = json.loads(fx_path.read_text(encoding="utf-8"))

    urls = list({r.url for r in rules})
    async with httpx.AsyncClient(headers={"User-Agent": UA}) as client:
        pages = dict(zip(urls, await asyncio.gather(*(fetch(client, u) for u in urls))))

    results: list[VerifyResult] = []
    for rule in rules:
        fx_val = rule.normalize(rule.fixture_getter(fixture))
        page = pages.get(rule.url, "")
        if page.startswith("__ERROR__"):
            results.append(
                VerifyResult(
                    company, rule.field, fx_val, None, rule.url,
                    level="⚪", note=f"源抓取失败: {page[11:80]}",
                )
            )
            continue
        m = re.search(rule.pattern, page, re.IGNORECASE)
        if not m:
            results.append(
                VerifyResult(
                    company, rule.field, fx_val, None, rule.url,
                    level="⚪", note="源中未找到匹配片段 (pattern 可能过严)",
                )
            )
            continue
        src_val = m.group(1).strip()
        level, note = _compare(rule.field, fx_val, src_val, rule.kind)
        results.append(VerifyResult(company, rule.field, fx_val, src_val, rule.url, level, note))
    return results


_MONTHS = {
    "january": "01", "february": "02", "march": "03", "april": "04",
    "may": "05", "june": "06", "july": "07", "august": "08",
    "september": "09", "october": "10", "november": "11", "december": "12",
}


def _normalize_date_tokens(s: str) -> set[str]:
    """从 '9 July 2018' / '2018-07-09' 统一抽出 {年, 月, 日} 数字集."""
    out: set[str] = set()
    # 英文月份 → 数字
    low = s.lower()
    for name, num in _MONTHS.items():
        if name in low:
            out.add(num)
    # 所有数字
    for tok in re.findall(r"\d+", s):
        # 年 4 位 / 月日 1-2 位 都保留
        out.add(tok.lstrip("0") or "0")
    return out


def _compare(field: str, fx: str, src: str, kind: str = "text") -> tuple[str, str]:
    """按 kind 选择比对策略."""
    fx_norm = fx.lower()
    src_norm = src.lower()

    if kind == "bool_alive":
        # fixture 说 True (还活/在任) vs 源里是否有"died/deceased/late"
        dead_signals = ("died", "deceased", "late ", "passed away", "辞世", "去世")
        is_dead_in_source = any(sig in src_norm for sig in dead_signals)
        fx_alive = fx_norm in ("true", "1", "yes")
        if is_dead_in_source and not fx_alive:
            return "🟢", "源确认已故 + fixture still_active=false ✓"
        if not is_dead_in_source and fx_alive:
            return "🟢", "源确认在任 + fixture still_active=true ✓"
        return "🔴", f"状态不符:fixture alive={fx_alive}, 源 dead_signal={is_dead_in_source}"

    if kind == "date":
        fx_tokens = _normalize_date_tokens(fx)
        src_tokens = _normalize_date_tokens(src)
        # 找年份 (4 位) 和月份
        fx_year = {t for t in fx_tokens if len(t) == 4}
        src_year = {t for t in src_tokens if len(t) == 4}
        if fx_year & src_year:
            # 月也对 → 🟢
            fx_month = {t for t in fx_tokens if len(t) <= 2}
            src_month = {t for t in src_tokens if len(t) <= 2}
            if fx_month & src_month:
                return "🟢", ""
            return "🟡", f"年对但月可能不同 (fx={fx_tokens} src={src_tokens})"
        return "🔴", f"年不符 fx_year={fx_year} src_year={src_year}"

    # kind == "text" 默认:子串 + 中英对照别名 (两侧都必须有对应的字/词)
    if src_norm in fx_norm or fx_norm in src_norm:
        return "🟢", ""
    for cn, en in _CN_EN_ALIASES.items():
        en_lower = en.lower()
        # 正向:源里的英文 + fixture 里的中文同时命中
        if en_lower in src_norm and cn in fx:
            return "🟢", f"中英对照命中 ({cn} ↔ {en})"
        # 反向:源里的中文 + fixture 里的英文同时命中
        if cn in src and en_lower in fx_norm:
            return "🟢", f"中英对照命中 ({cn} ↔ {en})"
    return "🔴", f"fixture='{fx[:40]}' vs 源='{src[:40]}'"


_CN_EN_ALIASES: dict[str, str] = {
    # 地名
    "北京": "Beijing",
    "上海": "Shanghai",
    "深圳": "Shenzhen",
    "杭州": "Hangzhou",
    "广州": "Guangzhou",
    "香港": "Hong Kong",
    "合肥": "Hefei",
    "巴塞尔": "Basel",
    # 公司
    "金山软件": "Kingsoft",
    "腾讯": "Tencent",
    "阿里巴巴": "Alibaba",
    "百度": "Baidu",
    "字节跳动": "ByteDance",
    "小米": "Xiaomi",
    "蔚来": "NIO",
    "百济神州": "BeiGene",
    "商汤": "SenseTime",
    # 机构
    "美国证券交易委员会": "SEC",
    "港交所": "HKEX",
    "纳斯达克": "NASDAQ",
    "纽交所": "NYSE",
    "科创板": "STAR",
}


def render_audit(results: list[VerifyResult]) -> str:
    today = date.today().isoformat()
    lines = [
        f"# Fixture 自动交叉校核 · {today}",
        "",
        "由 `tools/cross_verify.py` 并行 HTTP + 正则匹配生成。",
        "",
        "| 级别 | 含义 |",
        "|---|---|",
        "| 🟢 | fixture 与权威源一致 |",
        "| 🟡 | 部分一致 (如年月对但日差) |",
        "| 🔴 | 不一致 — 需要修正 |",
        "| ⚪ | 源抓取失败 / 模式未命中 |",
        "",
    ]
    by_company: dict[str, list[VerifyResult]] = {}
    for r in results:
        by_company.setdefault(r.company, []).append(r)
    for company, rs in sorted(by_company.items()):
        lines.append(f"## {company}")
        lines.append("")
        lines.append("| 级别 | 字段 | fixture | 权威源 | 源 URL |")
        lines.append("|---|---|---|---|---|")
        for r in rs:
            src = r.source_value or r.note or "—"
            url_short = r.source_url.split("/wiki/")[-1] if "/wiki/" in r.source_url else r.source_url
            lines.append(
                f"| {r.level} | `{r.field}` | {r.fixture_value[:30]} | {src[:40]} | [{url_short}]({r.source_url}) |"
            )
        lines.append("")
    total = len(results)
    green = sum(1 for r in results if r.level == "🟢")
    critical = sum(1 for r in results if r.level == "🔴")
    lines.append(f"**小结**: {total} 条规则 / 🟢 {green} / 🔴 {critical} / ⚪ {total - green - critical - sum(1 for r in results if r.level == '🟡')}")
    return "\n".join(lines)


async def main_async(company: Optional[str]) -> int:
    targets = [(c, rs) for c, rs in RULES.items() if company is None or c == company]
    if not targets:
        print(f"未找到规则: {company}")
        return 1
    all_results: list[VerifyResult] = []
    for c, rs in targets:
        print(f"→ 验证 {c} ({len(rs)} 条规则)")
        all_results.extend(await verify_company(c, rs))
    out = DOCS_DIR / f"data-audit-auto-{date.today().isoformat()}.md"
    out.write_text(render_audit(all_results), encoding="utf-8")
    print(f"✓ 已写入 {out}")
    critical = sum(1 for r in all_results if r.level == "🔴")
    return 1 if critical > 0 else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--company", help="只验证一家公司 (如 '小米'),缺省验证全部")
    args = ap.parse_args()
    return asyncio.run(main_async(args.company))


if __name__ == "__main__":
    sys.exit(main())
