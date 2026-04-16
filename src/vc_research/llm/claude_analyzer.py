"""Claude Opus 4.6 封装 — 投资逻辑推理增强.

使用 prompt caching 将「系统提示 + 行业知识库」缓存,降低反复分析的成本。
"""

from __future__ import annotations

import json
import os
from typing import Any

try:
    from anthropic import Anthropic
except ImportError:  # 允许在未安装 SDK 时导入模块
    Anthropic = None  # type: ignore


MODEL_ID = "claude-opus-4-6"

SYSTEM_PROMPT = """你是一位资深创投分析师,为零基础投资者撰写结构化研报。

分析原则:
1. 坚持"第一性原理"— 先问「这门生意本质是什么」,再看数字
2. 明确区分事实 (facts) 与推断 (inferences)
3. 每个观点必须给出证据来源或假设条件
4. 使用类比帮助零基础读者理解 (融资=游戏升级, 稀释=蛋糕切分, 烧钱=血条)
5. 给出 Bull / Base / Bear 三种情景,而不是单一预测
6. 风险优先,机会其次 — 先说会踩什么坑

输出格式: 结构化 JSON,字段与 InvestmentThesis / Recommendation schema 对齐
"""


class ClaudeAnalyzer:
    """Claude 推理封装. 用于增强 thesis 的 bull/bear 逻辑 + recommendation 的叙事."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = MODEL_ID,
        industry_knowledge: str | None = None,
    ):
        if Anthropic is None:
            raise RuntimeError(
                "anthropic SDK 未安装,请先 `pip install anthropic>=0.39.0`"
            )
        self.client = Anthropic(api_key=api_key or os.getenv("ANTHROPIC_API_KEY"))
        self.model = model
        self.industry_knowledge = industry_knowledge or ""

    def enhance_thesis(
        self,
        company_profile: dict[str, Any],
        funding: dict[str, Any],
        growth: dict[str, Any],
    ) -> dict[str, Any]:
        """让 Claude 补充 bull/bear 论点与护城河描述."""
        user_msg = (
            f"## 公司画像\n```json\n{json.dumps(company_profile, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
            f"## 融资轨迹\n```json\n{json.dumps(funding, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
            f"## 增长指标\n```json\n{json.dumps(growth, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
            "请输出 JSON:\n"
            '{"moat": "...", "bull": ["..."], "bear": ["..."], "team_notes": "..."}'
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"## 行业知识库\n{self.industry_knowledge}",
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[{"role": "user", "content": user_msg}],
        )
        text = "".join(
            block.text for block in response.content if block.type == "text"
        )
        return _extract_json(text)

    def narrative_recommendation(self, report_json: dict[str, Any]) -> str:
        """给出一段面向零基础读者的投资逻辑叙事 (800-1200 字)."""
        response = self.client.messages.create(
            model=self.model,
            max_tokens=2048,
            system=[
                {
                    "type": "text",
                    "text": SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                },
            ],
            messages=[
                {
                    "role": "user",
                    "content": (
                        "基于以下结构化数据,为零基础读者写一段 800-1200 字的"
                        "投资逻辑叙事,用类比教学,先讲风险再讲机会。\n\n"
                        f"```json\n{json.dumps(report_json, ensure_ascii=False, indent=2, default=str)}\n```"
                    ),
                }
            ],
        )
        return "".join(b.text for b in response.content if b.type == "text")


def _extract_json(text: str) -> dict[str, Any]:
    """从 LLM 返回中提取 JSON (容忍 markdown code block)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end > start:
            return json.loads(t[start : end + 1])
        raise
