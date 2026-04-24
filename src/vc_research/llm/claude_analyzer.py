"""投资逻辑推理增强 — 通过任意 LLMProvider 增强 thesis.

向后兼容: ClaudeAnalyzer 作为 ThesisEnhancer 的别名保留。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

from .base import LLMProvider, LLMProviderError

logger = logging.getLogger(__name__)


class EnhancedThesis(BaseModel):
    """enhance_thesis 返回值的 schema 校验."""

    moat: str = Field(default="", max_length=2000)
    bull: list[str] = Field(default_factory=list, max_length=10)
    bear: list[str] = Field(default_factory=list, max_length=10)
    team_notes: str = Field(default="", max_length=2000)


class LLMEnhancementError(RuntimeError):
    """LLM 增强失败 — 调用方应降级到 base 逻辑."""


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


class ThesisEnhancer:
    """LLM 推理封装. 用于增强 thesis 的 bull/bear 逻辑 + recommendation 的叙事.

    支持任意 LLMProvider (Claude / DeepSeek / GPT-4o / Kimi 等)。
    不指定 provider 时自动从 registry 获取最优可用 provider。
    """

    def __init__(
        self,
        provider: LLMProvider | None = None,
        api_key: str | None = None,
        model: str | None = None,
        industry_knowledge: str | None = None,
    ):
        if provider is not None:
            self.provider = provider
        else:
            # 向后兼容: 无 provider 时自动选择
            from .registry import get_provider
            # 如果传了 api_key，说明是旧调用方式，用 Anthropic
            if api_key:
                from .providers.anthropic_provider import AnthropicProvider
                self.provider = AnthropicProvider(
                    api_key=api_key, model=model or "claude-opus-4-6"
                )
            else:
                self.provider = get_provider(name=None)
        self.industry_knowledge = industry_knowledge or ""

    def enhance_thesis(
        self,
        company_profile: dict[str, Any],
        funding: dict[str, Any],
        growth: dict[str, Any],
    ) -> EnhancedThesis:
        """让 LLM 补充 bull/bear 论点与护城河描述.

        Raises:
            LLMEnhancementError: API 调用 / JSON 解析 / schema 校验失败
        """
        system = SYSTEM_PROMPT
        if self.industry_knowledge:
            system += f"\n\n## 行业知识库\n{self.industry_knowledge}"

        user_msg = (
            f"## 公司画像\n```json\n{json.dumps(company_profile, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
            f"## 融资轨迹\n```json\n{json.dumps(funding, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
            f"## 增长指标\n```json\n{json.dumps(growth, ensure_ascii=False, indent=2, default=str)}\n```\n\n"
            "请输出 JSON:\n"
            '{"moat": "...", "bull": ["..."], "bear": ["..."], "team_notes": "..."}'
        )

        try:
            text = self.provider.complete(system, user_msg, max_tokens=2048)
        except LLMProviderError as e:
            raise LLMEnhancementError(f"LLM API 调用失败: {e}") from e

        try:
            raw = _extract_json(text)
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("LLM 返回无法解析为 JSON: %s", text[:200])
            raise LLMEnhancementError(f"LLM 返回非合法 JSON: {e}") from e

        try:
            return EnhancedThesis.model_validate(raw)
        except ValidationError as e:
            logger.warning("LLM 返回 JSON 不符合 schema: %s", raw)
            raise LLMEnhancementError(f"LLM 返回 schema 不符: {e}") from e

    def narrative_recommendation(self, report_json: dict[str, Any]) -> str:
        """给出一段面向零基础读者的投资逻辑叙事 (800-1200 字)."""
        user_msg = (
            "基于以下结构化数据,为零基础读者写一段 800-1200 字的"
            "投资逻辑叙事,用类比教学,先讲风险再讲机会。\n\n"
            f"```json\n{json.dumps(report_json, ensure_ascii=False, indent=2, default=str)}\n```"
        )
        try:
            return self.provider.complete(SYSTEM_PROMPT, user_msg, max_tokens=2048)
        except LLMProviderError as e:
            raise LLMEnhancementError(f"LLM 叙事生成失败: {e}") from e


# 向后兼容别名
ClaudeAnalyzer = ThesisEnhancer


def _extract_json(text: str) -> dict[str, Any]:
    """从 LLM 返回中提取 JSON (容忍 markdown code block)."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t.rsplit("```", 1)[0]
    # 剥离 <think>...</think>
    if "<think>" in t and "</think>" in t:
        t = t.split("</think>", 1)[1].strip()
    try:
        return json.loads(t)
    except json.JSONDecodeError:
        start = t.find("{")
        end = t.rfind("}")
        if start >= 0 and end > start:
            return json.loads(t[start : end + 1])
        raise
