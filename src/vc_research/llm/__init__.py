"""LLM 推理层 — 多 Provider 支持 (Claude / DeepSeek / GPT-4o / Kimi / Perplexity / Ollama)."""

from .base import LLMProvider, LLMProviderError
from .claude_analyzer import (
    ClaudeAnalyzer,
    EnhancedThesis,
    LLMEnhancementError,
    ThesisEnhancer,
)
from .registry import get_provider, list_providers

__all__ = [
    "LLMProvider",
    "LLMProviderError",
    "ThesisEnhancer",
    "ClaudeAnalyzer",  # 向后兼容
    "EnhancedThesis",
    "LLMEnhancementError",
    "get_provider",
    "list_providers",
]
