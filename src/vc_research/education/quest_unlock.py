"""闯关式解锁 — 强化零基础投资者的认知路径.

设计哲学 (参考 project_design_philosophy.md):
- 神经可塑性: 每通过一个模块,大脑建立一次"投资思考"的连接
- 游戏化多巴胺: 解锁机制 + 进度条,激活奖赏回路
- 刻意练习: 按固定顺序 (画像→融资→依据→趋势→估值→风险→建议) 反复训练
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json


MODULES = [
    ("profile", "🏢 企业画像", "先看清这是谁在做什么"),
    ("funding", "💰 融资轨迹", "看钱从哪来,估值怎么变"),
    ("thesis", "🎯 投资依据", "凭什么这家公司值得投"),
    ("industry", "🌊 产业趋势", "大赛道正在往哪走"),
    ("valuation", "💎 估值分析", "现在这个价合理吗"),
    ("risks", "⚠️ 风险矩阵", "会踩什么坑"),
    ("recommendation", "🎯 投资建议", "综合决策 — 投 or 不投"),
]


@dataclass
class QuestProgress:
    """用户在当前案例中的学习进度."""

    company: str
    unlocked: set[str] = field(default_factory=lambda: {"profile"})
    completed: set[str] = field(default_factory=set)
    streak: int = 0

    @classmethod
    def load(cls, company: str, cache_dir: Path | None = None) -> "QuestProgress":
        path = _progress_path(company, cache_dir)
        if path.exists():
            data = json.loads(path.read_text())
            return cls(
                company=data["company"],
                unlocked=set(data.get("unlocked", ["profile"])),
                completed=set(data.get("completed", [])),
                streak=data.get("streak", 0),
            )
        return cls(company=company)

    def save(self, cache_dir: Path | None = None) -> None:
        path = _progress_path(self.company, cache_dir)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(
                {
                    "company": self.company,
                    "unlocked": sorted(self.unlocked),
                    "completed": sorted(self.completed),
                    "streak": self.streak,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    def complete(self, module_key: str) -> str | None:
        """标记一个模块完成,返回下一关提示 (或 None 表示通关)."""
        self.completed.add(module_key)
        self.streak += 1
        keys = [k for k, _, _ in MODULES]
        if module_key in keys:
            idx = keys.index(module_key)
            if idx + 1 < len(keys):
                next_key = keys[idx + 1]
                self.unlocked.add(next_key)
                _, name, hint = MODULES[idx + 1]
                return f"🔓 解锁新模块: {name} — {hint}"
        return None

    def status_bar(self) -> str:
        """进度条文本, e.g. '🏢✅ 💰✅ 🎯⬜ 🌊🔒 💎🔒 ⚠️🔒 🎯🔒 (2/7)'."""
        parts = []
        for key, name, _ in MODULES:
            icon = name.split(" ")[0]
            if key in self.completed:
                parts.append(f"{icon}✅")
            elif key in self.unlocked:
                parts.append(f"{icon}⬜")
            else:
                parts.append(f"{icon}🔒")
        return f"{' '.join(parts)} ({len(self.completed)}/{len(MODULES)})"


def _progress_path(company: str, cache_dir: Path | None) -> Path:
    base = cache_dir or (Path.home() / ".vc-research" / "progress")
    return base / f"{company}.json"
