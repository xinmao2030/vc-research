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


RULES: dict[str, list[VerifyRule]] = {
    "小米": [
        VerifyRule(
            field="itjuzi.founded_date",
            url="https://en.wikipedia.org/wiki/Xiaomi",
            pattern=r"Founded[\s\S]{0,200}?(\d{1,2}\s+April\s+2010|April\s+2010)",
            fixture_getter=_g("itjuzi.founded_date"),
        ),
        VerifyRule(
            field="itjuzi.rounds[ipo].announce_date",
            url="https://en.wikipedia.org/wiki/Xiaomi",
            pattern=r"(9\s+July\s+2018|July\s+2018)",
            fixture_getter=lambda d: next(
                (r["announce_date"] for r in d["itjuzi"]["rounds"] if r["stage"] == "ipo"), ""
            ),
        ),
    ],
    "蔚来": [
        VerifyRule(
            field="itjuzi.rounds[ipo].announce_date",
            url="https://en.wikipedia.org/wiki/Nio_(car_company)",
            pattern=r"(September\s+2018|12\s+September\s+2018)",
            fixture_getter=lambda d: next(
                (r["announce_date"] for r in d["itjuzi"]["rounds"] if r["stage"] == "ipo"), ""
            ),
        ),
    ],
    "百济神州": [
        VerifyRule(
            field="itjuzi.legal_name",
            url="https://en.wikipedia.org/wiki/BeOne_Medicines",
            pattern=r"(BeOne\s+Medicines)",
            fixture_getter=_g("itjuzi.legal_name"),
        ),
    ],
    "商汤科技": [
        VerifyRule(
            field="汤晓鸥_still_active",
            url="https://en.wikipedia.org/wiki/SenseTime",
            pattern=r"(died.{0,100}December\s+2023|Tang Xiao\'?ou.{0,200}died)",
            fixture_getter=lambda d: str(
                next(
                    (f.get("still_active", True) for f in d["itjuzi"]["founders"] if f["name"] == "汤晓鸥"),
                    True,
                )
            ),
        ),
    ],
    "字节跳动": [
        VerifyRule(
            field="张一鸣_still_active",
            url="https://en.wikipedia.org/wiki/Zhang_Yiming",
            pattern=r"(Chairman|chairman)",
            fixture_getter=lambda d: str(
                next(
                    (f.get("still_active", True) for f in d["itjuzi"]["founders"] if f["name"] == "张一鸣"),
                    True,
                )
            ),
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
        level, note = _compare(rule.field, fx_val, src_val)
        results.append(VerifyResult(company, rule.field, fx_val, src_val, rule.url, level, note))
    return results


def _compare(field: str, fx: str, src: str) -> tuple[str, str]:
    """简化比对:子串包含 / 大小写忽略."""
    fx_norm = fx.lower()
    src_norm = src.lower()
    if src_norm in fx_norm or fx_norm in src_norm:
        return "🟢", ""
    # 日期字段:提取数字比对
    if "date" in field:
        fx_digits = re.findall(r"\d+", fx)
        src_digits = re.findall(r"\d+", src)
        if set(fx_digits) & set(src_digits):
            return "🟡", "部分数字一致 (月/年匹配但日不同)"
    return "🔴", f"fixture='{fx[:40]}' vs 源='{src[:40]}'"


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
