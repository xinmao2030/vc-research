"""IT桔子数据源 — 国内创投数据 (通过 API 或 LLM 研究兜底).

IT桔子 API:
    - 需要 ITJUZI_API_KEY (在 .env)
    - POST https://api.itjuzi.com/api/investevent
    - 按公司名搜索, 返回融资事件和企业基本信息

若无 API key, 可选用 LLM 研究模式从公开数据源推断 (需设置 enable_llm_fallback=True).
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.itjuzi.com/api"
_TIMEOUT = 30


class ITJuziSource:
    """IT桔子 API 客户端."""

    name = "itjuzi"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("ITJUZI_API_KEY", "")

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        """搜索公司并返回结构化数据.

        返回格式与 fixtures 中的 itjuzi 子对象一致,方便 aggregator 直接 merge.
        """
        if not self.api_key:
            return None

        # 1. 搜索公司获取 ID
        company_id = self._search_company(company_name)
        if not company_id:
            return None

        # 2. 获取公司详情
        detail = self._get_company_detail(company_id)
        if not detail:
            return None

        # 3. 获取融资事件
        rounds = self._get_invest_events(company_id)

        # 4. 标准化为 fixtures 兼容格式
        return self._normalize(detail, rounds, company_name)

    def _search_company(self, name: str) -> str | None:
        """搜索公司, 返回 ID."""
        try:
            data = self._api_post(
                "/search",
                {"keyword": name, "type": "company", "page": 1, "per_page": 5},
            )
        except ITJuziAPIError as e:
            logger.warning("IT桔子搜索失败: %s", e)
            return None

        companies = data.get("data", {}).get("company", {}).get("data", [])
        if not companies:
            return None

        # 精确匹配优先
        for c in companies:
            c_name = c.get("com_name", "")
            if c_name == name or c_name.replace(" ", "") == name.replace(" ", ""):
                return str(c.get("com_id", ""))

        # 取第一个结果
        return str(companies[0].get("com_id", ""))

    def _get_company_detail(self, company_id: str) -> dict[str, Any] | None:
        """获取公司详情."""
        try:
            data = self._api_post(f"/company/{company_id}")
            return data.get("data", {})
        except ITJuziAPIError as e:
            logger.warning("IT桔子公司详情获取失败: %s", e)
            return None

    def _get_invest_events(self, company_id: str) -> list[dict[str, Any]]:
        """获取融资事件列表."""
        try:
            data = self._api_post(
                "/investevent",
                {"com_id": company_id, "page": 1, "per_page": 50},
            )
            return data.get("data", {}).get("data", [])
        except ITJuziAPIError as e:
            logger.warning("IT桔子融资事件获取失败: %s", e)
            return []

    def _normalize(
        self,
        detail: dict[str, Any],
        rounds_raw: list[dict[str, Any]],
        company_name: str,
    ) -> dict[str, Any]:
        """标准化为 fixtures 兼容格式."""
        # 基本信息
        result: dict[str, Any] = {
            "name": detail.get("com_name", company_name),
            "founded_date": detail.get("com_born_date"),
            "headquarters": detail.get("com_addr"),
            "industry": detail.get("com_sec_cat_name", ""),
            "sub_industry": detail.get("com_sub_cat_name"),
            "business_model": detail.get("com_des", ""),
            "employee_count": detail.get("com_employee_count"),
            "website": detail.get("com_url"),
        }

        # 创始人 / 团队
        members = detail.get("member", [])
        founders = []
        for m in (members if isinstance(members, list) else []):
            founders.append(
                {
                    "name": m.get("per_name", ""),
                    "title": m.get("per_title", ""),
                    "background": m.get("per_des", ""),
                }
            )
        result["founders"] = founders

        # 融资轮次
        rounds = []
        for r in rounds_raw:
            investors = []
            inv_list = r.get("investor", [])
            lead_names = []
            participant_names = []

            for inv in (inv_list if isinstance(inv_list, list) else []):
                inv_name = inv.get("inv_name", "")
                if inv.get("is_lead"):
                    lead_names.append(inv_name)
                else:
                    participant_names.append(inv_name)
                investors.append(
                    {
                        "name": inv_name,
                        "type": inv.get("inv_type", "VC"),
                        "is_lead": bool(inv.get("is_lead")),
                    }
                )

            amount_str = r.get("money", "")
            amount_usd = _parse_money(amount_str, r.get("currency", "USD"))

            rounds.append(
                {
                    "stage": _normalize_stage(r.get("round", "")),
                    "announce_date": r.get("date"),
                    "amount_usd": amount_usd,
                    "post_money_valuation_usd": _parse_money(
                        r.get("valuation", ""), r.get("currency", "USD")
                    ),
                    "lead_investors": lead_names,
                    "participants": participant_names,
                    "investor_details": investors,
                }
            )

        result["rounds"] = rounds
        return result

    def _api_post(
        self,
        endpoint: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """发送 API 请求."""
        url = f"{_BASE_URL}{endpoint}"
        body = json.dumps(payload or {}).encode("utf-8")
        req = urlrequest.Request(
            url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urlrequest.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urlerror.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise ITJuziAPIError(f"HTTP {e.code}: {body_text}") from e
        except (urlerror.URLError, TimeoutError, OSError) as e:
            raise ITJuziAPIError(f"连接失败: {e}") from e


class ITJuziAPIError(RuntimeError):
    """IT桔子 API 调用错误."""


# ── helpers ──────────────────────────────────────────────


_STAGE_MAP = {
    "天使轮": "seed",
    "Pre-A轮": "series_a",
    "A轮": "series_a",
    "A+轮": "series_a",
    "Pre-B轮": "series_b",
    "B轮": "series_b",
    "B+轮": "series_b",
    "C轮": "series_c",
    "C+轮": "series_c",
    "D轮": "series_d",
    "D+轮": "series_d",
    "E轮": "series_e_plus",
    "F轮": "series_e_plus",
    "G轮": "series_e_plus",
    "Pre-IPO": "pre_ipo",
    "IPO": "ipo",
    "战略融资": "strategic",
    "股权转让": "secondary",
}


def _normalize_stage(raw: str) -> str:
    """将 IT桔子轮次名映射为 schema FundingStage."""
    return _STAGE_MAP.get(raw, raw.lower().replace(" ", "_") if raw else "seed")


def _parse_money(raw: str | None, currency: str = "USD") -> float | None:
    """解析金额字符串 (如 '1000万美元' / '5亿人民币')."""
    if not raw:
        return None
    raw = str(raw).strip()
    if not raw or raw == "未透露":
        return None

    # 提取数字
    import re

    nums = re.findall(r"[\d.]+", raw)
    if not nums:
        return None

    value = float(nums[0])

    # 单位乘数
    if "亿" in raw:
        value *= 1e8
    elif "千万" in raw:
        value *= 1e7
    elif "百万" in raw:
        value *= 1e6
    elif "万" in raw:
        value *= 1e4

    # 货币转换 (粗略)
    if "人民币" in raw or "RMB" in raw or currency == "CNY":
        value /= 7.2  # 粗略汇率
    elif "€" in raw or "EUR" in currency:
        value *= 1.08

    return round(value, 2) if value > 0 else None
