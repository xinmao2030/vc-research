"""WebVerifier — 用 Perplexity 实时交叉验证 RawCompanyData 关键事实.

用法:
    verifier = WebVerifier()  # 自动从 registry 获取 perplexity provider
    result = verifier.verify(raw_data)
    print(result.summary())
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class VerifyStatus(str, Enum):
    CONFIRMED = "confirmed"
    DISPUTED = "disputed"
    UNVERIFIABLE = "unverifiable"


@dataclass
class ClaimVerification:
    """单条事实的验证结果."""

    claim: str
    category: str  # founding / funding / executive / product
    status: VerifyStatus
    source_value: str  # fixture 中的值
    web_value: str  # 网上查到的值
    citations: list[str] = field(default_factory=list)
    notes: str = ""


@dataclass
class VerificationReport:
    """整份数据的验证报告."""

    company: str
    claims: list[ClaimVerification] = field(default_factory=list)

    @property
    def confirmed_count(self) -> int:
        return sum(1 for c in self.claims if c.status == VerifyStatus.CONFIRMED)

    @property
    def disputed_count(self) -> int:
        return sum(1 for c in self.claims if c.status == VerifyStatus.DISPUTED)

    @property
    def confidence_pct(self) -> float:
        """可验证条目中确认比例 (0-100)."""
        verifiable = [c for c in self.claims if c.status != VerifyStatus.UNVERIFIABLE]
        if not verifiable:
            return 0.0
        return self.confirmed_count / len(verifiable) * 100

    def summary(self) -> str:
        total = len(self.claims)
        return (
            f"[{self.company}] 验证 {total} 条: "
            f"✓ {self.confirmed_count} confirmed, "
            f"✗ {self.disputed_count} disputed, "
            f"? {total - self.confirmed_count - self.disputed_count} unverifiable "
            f"({self.confidence_pct:.0f}% confidence)"
        )

    def disputed_items(self) -> list[ClaimVerification]:
        return [c for c in self.claims if c.status == VerifyStatus.DISPUTED]


VERIFY_SYSTEM_PROMPT = """你是一位事实核查分析师。用户会给你一组关于某家公司的事实声明,
请你用你的实时搜索能力逐条验证,并以 JSON 数组返回结果。

每条结果格式:
{
  "claim": "原始声明",
  "category": "founding / funding / executive / product",
  "status": "confirmed / disputed / unverifiable",
  "web_value": "你查到的正确值 (若 confirmed 则与 source_value 相同)",
  "notes": "简短说明差异或验证来源"
}

规则:
1. 日期误差 ≤ 1 个月算 confirmed
2. 金额误差 ≤ 10% 算 confirmed
3. 人名 / 职位完全匹配才算 confirmed
4. 找不到可靠来源就标 unverifiable,不要瞎猜
5. 只输出 JSON 数组,不要其他文字
"""


class WebVerifier:
    """用 Perplexity 实时搜索验证 RawCompanyData 中的关键事实."""

    def __init__(self, provider: Any | None = None):
        """初始化.

        Args:
            provider: 带 complete_with_citations 的 provider (通常是 PerplexityProvider).
                      不传则自动从 registry 获取 perplexity.
        """
        self._provider = provider

    def _get_provider(self) -> Any:
        if self._provider is not None:
            return self._provider
        from ..llm.registry import get_provider

        self._provider = get_provider(name="perplexity")
        return self._provider

    def verify(self, raw: Any) -> VerificationReport:
        """验证 RawCompanyData 中的关键事实.

        Args:
            raw: RawCompanyData 实例

        Returns:
            VerificationReport
        """
        claims = self._extract_claims(raw)
        if not claims:
            return VerificationReport(company=raw.name)

        provider = self._get_provider()
        user_msg = self._build_query(raw.name, claims)

        try:
            if hasattr(provider, "complete_with_citations"):
                text, citations = provider.complete_with_citations(
                    VERIFY_SYSTEM_PROMPT, user_msg, max_tokens=4096, temperature=0.1
                )
            else:
                text = provider.complete(
                    VERIFY_SYSTEM_PROMPT, user_msg, max_tokens=4096, temperature=0.1
                )
                citations = []
        except Exception as e:
            logger.warning("WebVerifier 调用失败: %s", e)
            return VerificationReport(
                company=raw.name,
                claims=[
                    ClaimVerification(
                        claim="(验证失败)",
                        category="error",
                        status=VerifyStatus.UNVERIFIABLE,
                        source_value="",
                        web_value="",
                        notes=str(e),
                    )
                ],
            )

        return self._parse_response(raw.name, claims, text, citations)

    def _extract_claims(self, raw: Any) -> list[dict[str, str]]:
        """从 RawCompanyData 提取需要验证的关键事实."""
        claims: list[dict[str, str]] = []

        # 从各个数据源提取
        for source_data in [raw.qichacha, raw.itjuzi, raw.crunchbase]:
            if not source_data:
                continue
            self._extract_from_source(source_data, claims)

        return claims

    def _extract_from_source(
        self, data: dict[str, Any], claims: list[dict[str, str]]
    ) -> None:
        """从单个数据源 dict 提取 claims."""
        # 成立日期
        for key in ("founded_date", "founded", "established"):
            val = data.get(key)
            if val:
                claims.append(
                    {
                        "claim": f"成立日期: {val}",
                        "category": "founding",
                        "source_value": str(val),
                    }
                )
                break

        # 创始人
        founders = data.get("founders", [])
        if isinstance(founders, list):
            for f in founders[:3]:  # 最多验证 3 位
                if isinstance(f, dict):
                    name = f.get("name", "")
                    title = f.get("title", "")
                    if name:
                        claims.append(
                            {
                                "claim": f"创始人: {name}, 职位: {title}",
                                "category": "executive",
                                "source_value": f"{name} ({title})",
                            }
                        )
                elif isinstance(f, str):
                    claims.append(
                        {
                            "claim": f"创始人: {f}",
                            "category": "executive",
                            "source_value": f,
                        }
                    )

        # 融资轮次
        rounds = data.get("funding_rounds", data.get("rounds", []))
        if isinstance(rounds, list):
            for r in rounds[:5]:  # 最多验证 5 轮
                if not isinstance(r, dict):
                    continue
                stage = r.get("stage", r.get("round", ""))
                amount = r.get("amount_usd", r.get("amount", ""))
                lead = r.get("lead_investors", r.get("lead", []))
                if stage and amount:
                    lead_str = ", ".join(lead) if isinstance(lead, list) else str(lead)
                    claims.append(
                        {
                            "claim": f"{stage} 轮融资 ${amount}, 领投: {lead_str}",
                            "category": "funding",
                            "source_value": f"${amount}",
                        }
                    )

        # 总部
        hq = data.get("headquarters", data.get("hq", data.get("location", "")))
        if hq:
            claims.append(
                {
                    "claim": f"总部: {hq}",
                    "category": "founding",
                    "source_value": str(hq),
                }
            )

        # 核心产品
        products = data.get("products", data.get("core_products", []))
        if isinstance(products, list):
            for p in products[:3]:
                if isinstance(p, dict):
                    pname = p.get("name", "")
                    if pname:
                        claims.append(
                            {
                                "claim": f"核心产品: {pname}",
                                "category": "product",
                                "source_value": pname,
                            }
                        )
                elif isinstance(p, str) and p:
                    claims.append(
                        {
                            "claim": f"核心产品: {p}",
                            "category": "product",
                            "source_value": p,
                        }
                    )

    def _build_query(self, company: str, claims: list[dict[str, str]]) -> str:
        lines = [f"公司: {company}", "", "请验证以下事实:"]
        for i, c in enumerate(claims, 1):
            lines.append(f"{i}. [{c['category']}] {c['claim']}")
        return "\n".join(lines)

    def _parse_response(
        self,
        company: str,
        original_claims: list[dict[str, str]],
        text: str,
        citations: list[str],
    ) -> VerificationReport:
        """解析 LLM 返回的 JSON 验证结果."""
        report = VerificationReport(company=company)

        try:
            parsed = _extract_json_array(text)
        except (json.JSONDecodeError, ValueError):
            logger.warning("WebVerifier 返回无法解析: %s", text[:300])
            # 降级: 所有 claims 标记为 unverifiable
            for c in original_claims:
                report.claims.append(
                    ClaimVerification(
                        claim=c["claim"],
                        category=c["category"],
                        status=VerifyStatus.UNVERIFIABLE,
                        source_value=c.get("source_value", ""),
                        web_value="",
                        notes="LLM 返回无法解析",
                    )
                )
            return report

        # 把 LLM 结果映射回来
        for item in parsed:
            if not isinstance(item, dict):
                continue
            status_str = item.get("status", "unverifiable").lower()
            try:
                status = VerifyStatus(status_str)
            except ValueError:
                status = VerifyStatus.UNVERIFIABLE

            report.claims.append(
                ClaimVerification(
                    claim=item.get("claim", ""),
                    category=item.get("category", "unknown"),
                    status=status,
                    source_value=item.get("source_value", ""),
                    web_value=item.get("web_value", ""),
                    citations=citations,
                    notes=item.get("notes", ""),
                )
            )

        return report


def _extract_json_array(text: str) -> list[dict[str, Any]]:
    """从 LLM 返回中提取 JSON 数组."""
    t = text.strip()
    # 剥离 markdown code block
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    # 剥离 <think>
    if "<think>" in t and "</think>" in t:
        t = t.split("</think>", 1)[1].strip()

    try:
        result = json.loads(t)
    except json.JSONDecodeError:
        start = t.find("[")
        end = t.rfind("]")
        if start >= 0 and end > start:
            result = json.loads(t[start : end + 1])
        else:
            raise

    if isinstance(result, list):
        return result
    raise ValueError(f"Expected JSON array, got {type(result)}")
