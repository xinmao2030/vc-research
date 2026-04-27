"""Crunchbase 数据源 — 海外创投数据 (API v4).

Crunchbase API v4:
    - 需要 CRUNCHBASE_API_KEY (在 .env)
    - GET https://api.crunchbase.com/api/v4/autocompletes?query=...
    - GET https://api.crunchbase.com/api/v4/entities/organizations/{permalink}
    - Rate limit: Basic 200/min, Pro 1000/min
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Any
from urllib import error as urlerror
from urllib import parse as urlparse
from urllib import request as urlrequest

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.crunchbase.com/api/v4"
_TIMEOUT = 30
_RATE_LIMIT_DELAY = 0.5  # 保守: 每次请求间隔 500ms


class CrunchbaseSource:
    """Crunchbase API v4 客户端."""

    name = "crunchbase"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("CRUNCHBASE_API_KEY", "")
        self._last_request_time: float = 0

    def fetch(self, company_name: str) -> dict[str, Any] | None:
        """搜索公司并返回结构化数据.

        返回格式与 fixtures 中的 crunchbase 子对象一致.
        """
        if not self.api_key:
            return None

        # 1. 自动补全搜索
        permalink = self._search(company_name)
        if not permalink:
            return None

        # 2. 获取组织详情 + 融资轮次
        org_data = self._get_organization(permalink)
        if not org_data:
            return None

        # 3. 标准化
        return self._normalize(org_data, company_name)

    def _search(self, query: str) -> str | None:
        """通过自动补全搜索公司, 返回 permalink."""
        params = urlparse.urlencode(
            {
                "query": query,
                "collection_ids": "organizations",
                "limit": 5,
            }
        )
        try:
            data = self._api_get(f"/autocompletes?{params}")
        except CrunchbaseAPIError as e:
            logger.warning("Crunchbase 搜索失败: %s", e)
            return None

        entities = data.get("entities", [])
        if not entities:
            return None

        # 精确匹配优先
        query_lower = query.lower().replace(" ", "")
        for ent in entities:
            ident = ent.get("identifier", {})
            name = (ident.get("value") or "").lower().replace(" ", "")
            if name == query_lower:
                return ident.get("permalink")

        # 取第一个
        return entities[0].get("identifier", {}).get("permalink")

    def _get_organization(self, permalink: str) -> dict[str, Any] | None:
        """获取组织详情."""
        # 请求所有需要的 card
        cards = ",".join(
            [
                "fields",
                "founders",
                "funding_rounds",
                "headquarters_address",
            ]
        )
        try:
            data = self._api_get(
                f"/entities/organizations/{permalink}?card_ids={cards}"
            )
            return data
        except CrunchbaseAPIError as e:
            logger.warning("Crunchbase 组织详情获取失败: %s", e)
            return None

    def _normalize(
        self,
        org_data: dict[str, Any],
        company_name: str,
    ) -> dict[str, Any]:
        """标准化为 fixtures 兼容格式."""
        props = org_data.get("properties", {})
        cards = org_data.get("cards", {})

        result: dict[str, Any] = {
            "name": props.get("name", company_name),
            "founded_date": props.get("founded_on"),
            "industry": _get_first_category(props),
            "business_model": props.get("short_description", ""),
            "employee_count": _parse_employee_count(
                props.get("num_employees_enum")
            ),
            "website": props.get("homepage_url"),
        }

        # 总部
        hq = cards.get("headquarters_address", [])
        if isinstance(hq, list) and hq:
            addr = hq[0] if isinstance(hq[0], dict) else {}
            city = addr.get("city", "")
            country = addr.get("country", "")
            result["headquarters"] = f"{city}, {country}".strip(", ")

        # 创始人
        founders_data = cards.get("founders", [])
        founders = []
        for f in (founders_data if isinstance(founders_data, list) else []):
            f_props = f.get("properties", f) if isinstance(f, dict) else {}
            ident = f.get("identifier", {}) if isinstance(f, dict) else {}
            founders.append(
                {
                    "name": ident.get("value", f_props.get("name", "")),
                    "title": f_props.get("title", "Founder"),
                    "background": f_props.get("description", ""),
                }
            )
        result["founders"] = founders

        # 融资轮次
        funding_data = cards.get("funding_rounds", [])
        rounds = []
        for r in (funding_data if isinstance(funding_data, list) else []):
            r_props = r.get("properties", r) if isinstance(r, dict) else {}
            ident = r.get("identifier", {}) if isinstance(r, dict) else {}

            lead_names = []
            participant_names = []
            investor_details = []
            for inv in r_props.get("investors", []):
                if isinstance(inv, dict):
                    inv_name = inv.get("name", inv.get("value", ""))
                    if inv.get("is_lead_investor"):
                        lead_names.append(inv_name)
                    else:
                        participant_names.append(inv_name)
                    investor_details.append(
                        {
                            "name": inv_name,
                            "type": inv.get("type", "VC"),
                            "is_lead": bool(inv.get("is_lead_investor")),
                        }
                    )
                elif isinstance(inv, str):
                    participant_names.append(inv)

            amount_usd = r_props.get("money_raised", {})
            if isinstance(amount_usd, dict):
                amount_val = amount_usd.get("value_usd")
            else:
                amount_val = r_props.get("money_raised_usd")

            post_val = r_props.get("post_money_valuation", {})
            if isinstance(post_val, dict):
                post_money = post_val.get("value_usd")
            else:
                post_money = r_props.get("post_money_valuation_usd")

            pre_val = r_props.get("pre_money_valuation", {})
            if isinstance(pre_val, dict):
                pre_money = pre_val.get("value_usd")
            else:
                pre_money = r_props.get("pre_money_valuation_usd")

            rounds.append(
                {
                    "stage": _normalize_stage(
                        r_props.get("funding_type")
                        or ident.get("value", "")
                    ),
                    "announce_date": r_props.get("announced_on"),
                    "amount_usd": amount_val,
                    "pre_money_valuation_usd": pre_money,
                    "post_money_valuation_usd": post_money,
                    "lead_investors": lead_names,
                    "participants": participant_names,
                    "investor_details": investor_details,
                }
            )

        result["rounds"] = rounds
        return result

    def _api_get(self, path: str) -> dict[str, Any]:
        """发送 GET 请求 (带 rate limiting)."""
        # 简单 rate limiting
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < _RATE_LIMIT_DELAY:
            time.sleep(_RATE_LIMIT_DELAY - elapsed)

        separator = "&" if "?" in path else "?"
        url = f"{_BASE_URL}{path}{separator}user_key={self.api_key}"
        req = urlrequest.Request(
            url,
            headers={"Accept": "application/json"},
        )

        try:
            self._last_request_time = time.monotonic()
            with urlrequest.urlopen(req, timeout=_TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urlerror.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")[:500]
            except Exception:
                pass
            raise CrunchbaseAPIError(f"HTTP {e.code}: {body_text}") from e
        except (urlerror.URLError, TimeoutError, OSError) as e:
            raise CrunchbaseAPIError(f"连接失败: {e}") from e


class CrunchbaseAPIError(RuntimeError):
    """Crunchbase API 调用错误."""


# ── helpers ──────────────────────────────────────────────

_STAGE_MAP = {
    "seed": "seed",
    "pre_seed": "pre_seed",
    "angel": "seed",
    "series_a": "series_a",
    "series_b": "series_b",
    "series_c": "series_c",
    "series_d": "series_d",
    "series_e": "series_e_plus",
    "series_f": "series_e_plus",
    "series_g": "series_e_plus",
    "series_h": "series_e_plus",
    "private_equity": "series_e_plus",
    "corporate_round": "strategic",
    "initial_coin_offering": "ipo",
    "post_ipo_equity": "secondary",
    "post_ipo_debt": "secondary",
    "secondary_market": "secondary",
    "debt_financing": "strategic",
    "convertible_note": "seed",
    "grant": "seed",
    "undisclosed": "seed",
}


def _normalize_stage(raw: str) -> str:
    """将 Crunchbase funding_type 映射为 schema FundingStage."""
    if not raw:
        return "seed"
    key = raw.lower().replace(" ", "_").replace("-", "_")
    return _STAGE_MAP.get(key, key)


def _get_first_category(props: dict[str, Any]) -> str:
    """提取第一个行业分类."""
    cats = props.get("categories", [])
    if isinstance(cats, list) and cats:
        if isinstance(cats[0], dict):
            return cats[0].get("value", cats[0].get("name", ""))
        return str(cats[0])
    return props.get("category_groups_list", "")


_EMPLOYEE_MAP = {
    "c_00001_00010": 5,
    "c_00011_00050": 30,
    "c_00051_00100": 75,
    "c_00101_00250": 175,
    "c_00251_00500": 375,
    "c_00501_01000": 750,
    "c_01001_05000": 3000,
    "c_05001_10000": 7500,
    "c_10001_max": 15000,
}


def _parse_employee_count(enum_val: str | None) -> int | None:
    """将 Crunchbase 员工枚举值转为近似数字."""
    if not enum_val:
        return None
    return _EMPLOYEE_MAP.get(enum_val)
