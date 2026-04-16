"""跨模块共享工具 — 消除 funding_rounds / investment_thesis / industry_trends /
risk_matrix / company_profile 里的重复定义.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from .schema import FundingStage


# ────────────────────────────────────────────────────────────
# Stage 解析 — 统一入口 (之前分散在 company_profile._STAGE_MAP 和
# funding_rounds._STAGE_ALIAS,键不一致会产生跨模块 bug)
# ────────────────────────────────────────────────────────────
_STAGE_ALIAS: dict[str, FundingStage] = {
    # 英文/简写
    "pre_seed": FundingStage.PRE_SEED,
    "pre-seed": FundingStage.PRE_SEED,
    "preseed": FundingStage.PRE_SEED,
    "seed": FundingStage.SEED,
    "angel": FundingStage.SEED,
    "pre-a": FundingStage.SEED,
    "pre_a": FundingStage.SEED,
    "a": FundingStage.SERIES_A,
    "a+": FundingStage.SERIES_A,
    "series_a": FundingStage.SERIES_A,
    "series a": FundingStage.SERIES_A,
    "b": FundingStage.SERIES_B,
    "b+": FundingStage.SERIES_B,
    "series_b": FundingStage.SERIES_B,
    "c": FundingStage.SERIES_C,
    "series_c": FundingStage.SERIES_C,
    "d": FundingStage.SERIES_D,
    "series_d": FundingStage.SERIES_D,
    "e": FundingStage.SERIES_E_PLUS,
    "e+": FundingStage.SERIES_E_PLUS,
    "f": FundingStage.SERIES_E_PLUS,
    "series_e_plus": FundingStage.SERIES_E_PLUS,
    "pre-ipo": FundingStage.PRE_IPO,
    "pre_ipo": FundingStage.PRE_IPO,
    "preipo": FundingStage.PRE_IPO,
    "ipo": FundingStage.IPO,
    "strategic": FundingStage.STRATEGIC,
    # 中文
    "种子": FundingStage.SEED,
    "天使": FundingStage.SEED,
    "战略": FundingStage.STRATEGIC,
    "战略投资": FundingStage.STRATEGIC,
    "上市": FundingStage.IPO,
}


def parse_funding_stage(raw: Any, default: FundingStage = FundingStage.SEED) -> FundingStage:
    """把各种形式的融资轮次字符串解析为 FundingStage.

    宽容处理:
        - 'A 轮' / 'Series A' / 'a+' / '天使' 等常见表述
        - 大小写 / 前后空格 / 全角空格
        - 未识别时返回 default (不抛异常,避免阻塞流程)
    """
    if raw is None:
        return default
    if isinstance(raw, FundingStage):
        return raw
    key = str(raw).strip().lower().replace("　", "").replace(" ", " ")
    key = key.replace("轮", "").replace("series ", "series_").strip()
    return _STAGE_ALIAS.get(key, default)


# ────────────────────────────────────────────────────────────
# 类型转换 — 宽容 Decimal
# ────────────────────────────────────────────────────────────
def to_decimal(value: Any) -> Decimal | None:
    """宽容转 Decimal.

    接受: int / float / str / Decimal / None
    拒绝: 其他类型返回 None (不崩溃)
    """
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except (ValueError, ArithmeticError, TypeError):
        return None


# ────────────────────────────────────────────────────────────
# 日期解析 — 宽容
# ────────────────────────────────────────────────────────────
def parse_date(value: Any) -> date | None:
    """宽容转 date.

    接受 ISO 格式 'YYYY-MM-DD' / date 对象 / None
    """
    if not value:
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(str(value))
    except (ValueError, TypeError):
        return None


# ────────────────────────────────────────────────────────────
# 金额人性化 (设计师 P0 需求)
# ────────────────────────────────────────────────────────────
def format_money_cn(amount: Decimal | int | float | None) -> str:
    """美元金额中文人性化显示: 150000000 → '$1.5 亿'."""
    if amount is None:
        return "—"
    try:
        a = float(amount)
    except (TypeError, ValueError):
        return str(amount)
    if a == 0:
        return "$0"
    sign = "-" if a < 0 else ""
    a = abs(a)
    if a >= 1e12:
        return f"{sign}${a / 1e12:.2f} 万亿"
    if a >= 1e8:
        return f"{sign}${a / 1e8:.2f} 亿"
    if a >= 1e4:
        return f"{sign}${a / 1e4:.2f} 万"
    return f"{sign}${a:,.0f}"


def format_money_en(amount: Decimal | int | float | None) -> str:
    """英文金额人性化: 150000000000 → '$150.0B'."""
    if amount is None:
        return "—"
    try:
        a = float(amount)
    except (TypeError, ValueError):
        return str(amount)
    if a == 0:
        return "$0"
    sign = "-" if a < 0 else ""
    a = abs(a)
    if a >= 1e12:
        return f"{sign}${a / 1e12:.2f}T"
    if a >= 1e9:
        return f"{sign}${a / 1e9:.2f}B"
    if a >= 1e6:
        return f"{sign}${a / 1e6:.2f}M"
    if a >= 1e3:
        return f"{sign}${a / 1e3:.2f}K"
    return f"{sign}${a:,.0f}"


def format_money(amount: Decimal | int | float | None, locale: str = "cn") -> str:
    return format_money_cn(amount) if locale == "cn" else format_money_en(amount)
