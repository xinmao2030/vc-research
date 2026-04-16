"""SEC EDGAR 数据源 — 免费公开,覆盖在美国上市的中概股.

API 参考: https://www.sec.gov/os/accessing-edgar-data

要点:
    - SEC 要求请求头 User-Agent 为真实联系方式,否则 403
    - submissions API: https://data.sec.gov/submissions/CIK{10位}.json
      返回公司基本信息 + 最近 10-K / 20-F 等披露文件索引
    - companyfacts API: https://data.sec.gov/api/xbrl/companyfacts/CIK{10位}.json
      返回 XBRL 结构化财务数据 (Revenues / Assets / NetIncome 等)
    - 速率限制: 10 req/sec per IP

只实现 Phase 2.1 骨架:基本信息 + 最新 10-K/20-F 文件名。
估值 / 融资轮次由其他源 (itjuzi/crunchbase) 提供,SEC 不直接覆盖。
"""

from __future__ import annotations

import os
from typing import Any

import httpx

# 中概股公司名 → SEC CIK 映射 (手工维护小表;后续可用 ticker 搜索 API)
#
# 当前 6 家标杆(影石/澜起/银诺/比贝特/汉朔/强一)全在 A/H 股,无美股上市,
# 本映射仅为未来接入美股中概股(蔚来/理想/小鹏/阿里/京东/拼多多)时保留基础设施。
_COMPANY_TO_CIK: dict[str, str] = {
    # 旧标杆(保留样例以便回归测试 sec_edgar_source 本身)
    "蔚来": "0001736541",
    "NIO Inc.": "0001736541",
    "NIO": "0001736541",
    "百济神州": "0001651308",
    "BeiGene": "0001651308",
    "BeOne Medicines": "0001651308",
    "BeOne": "0001651308",
}


class SecEdgarSource:
    """SEC EDGAR 公开 JSON API."""

    name = "sec_edgar"
    provenance = "SEC EDGAR · submissions + companyfacts"

    BASE_SUBMISSIONS = "https://data.sec.gov/submissions/CIK{cik}.json"
    BASE_FACTS = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"

    def __init__(self, user_agent: str | None = None, timeout: float = 10.0):
        # SEC 要求真实 UA:"Name email"
        self.user_agent = user_agent or os.getenv(
            "SEC_EDGAR_UA", "vc-research/0.1 xinmao2030@gmail.com"
        )
        self.timeout = timeout

    def _get(self, url: str) -> dict[str, Any] | None:
        try:
            with httpx.Client(headers={"User-Agent": self.user_agent}) as c:
                r = c.get(url, timeout=self.timeout)
                if r.status_code == 404:
                    return None
                r.raise_for_status()
                return r.json()
        except httpx.HTTPError:
            return None

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        cik = _COMPANY_TO_CIK.get(company_name)
        if not cik:
            return None

        sub = self._get(self.BASE_SUBMISSIONS.format(cik=cik))
        if not sub:
            return None

        # 提取基本信息
        payload: dict[str, Any] = {
            "legal_name": sub.get("name"),
            "ticker": ",".join(sub.get("tickers") or []),
            "exchanges": ",".join(sub.get("exchanges") or []),
            "sic_description": sub.get("sicDescription"),
            "headquarters": _format_addr(sub.get("addresses", {}).get("business", {})),
            "cik": cik,
            "state_of_incorp": sub.get("stateOfIncorporation"),
            "filings_recent": _format_recent_filings(sub.get("filings", {}).get("recent", {})),
        }

        # 财务事实 (可选,XBRL 结构大,只取几个关键指标)
        facts = self._get(self.BASE_FACTS.format(cik=cik))
        if facts:
            payload["xbrl_facts"] = _extract_key_facts(facts)

        return {k: v for k, v in payload.items() if v}


def _format_addr(addr: dict[str, Any]) -> str:
    parts = [addr.get(k) for k in ("city", "stateOrCountry", "zipCode")]
    return " · ".join(p for p in parts if p)


def _format_recent_filings(recent: dict[str, Any]) -> list[dict[str, str]]:
    """从 parallel arrays 结构中取前 5 条 10-K / 20-F / 10-Q."""
    forms = recent.get("form") or []
    dates = recent.get("filingDate") or []
    accs = recent.get("accessionNumber") or []
    urls = recent.get("primaryDocument") or []
    wanted = {"10-K", "20-F", "10-Q", "6-K", "8-K"}
    out: list[dict[str, str]] = []
    for i, form in enumerate(forms):
        if form in wanted and len(out) < 10:
            out.append(
                {
                    "form": form,
                    "filed": dates[i] if i < len(dates) else "",
                    "accession": accs[i] if i < len(accs) else "",
                    "doc": urls[i] if i < len(urls) else "",
                }
            )
    return out


def _extract_key_facts(facts: dict[str, Any]) -> dict[str, Any]:
    """从 XBRL facts 抽取收入/现金/净亏损几个 US-GAAP tag.

    返回 {tag: [(end_date, value, fy), ...]} 只留最新 3 年.
    """
    us_gaap = (facts.get("facts") or {}).get("us-gaap") or {}
    want_tags = [
        "Revenues",
        "Revenue",
        "NetIncomeLoss",
        "CashAndCashEquivalentsAtCarryingValue",
        "Assets",
    ]
    out: dict[str, Any] = {}
    for tag in want_tags:
        node = us_gaap.get(tag)
        if not node:
            continue
        # units 通常是 "USD" / "CNY"
        for unit, rows in (node.get("units") or {}).items():
            # 取 FY (全年) 的最新 3 个
            fy_rows = [r for r in rows if r.get("fp") == "FY"]
            fy_rows.sort(key=lambda r: r.get("end", ""), reverse=True)
            picked = fy_rows[:3]
            if picked:
                out[f"{tag}_{unit}"] = [
                    {"end": r.get("end"), "val": r.get("val"), "fy": r.get("fy")}
                    for r in picked
                ]
                break
    return out
