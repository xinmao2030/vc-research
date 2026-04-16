"""教育层 — 闯关解锁 + 类比教学 (延续 portfolio-manager 教育哲学)."""

from .analogy_teacher import explain_with_analogy
from .quest_unlock import QuestProgress

__all__ = ["QuestProgress", "explain_with_analogy"]
