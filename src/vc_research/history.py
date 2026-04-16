"""已生成研报历史记录 — 持久化到 ~/.vc-research/history.jsonl.

设计:
    - 追加式 JSONL (每行一条记录),便于增量写入和 tail
    - 记录元数据不含完整研报正文 (正文在 report_path 指向的文件里)
    - CLI `vc-research history` 读取并渲染为 Rich 表格

字段:
    ts                 ISO 8601 生成时间 (含时区)
    company            公司名
    verdict            投资裁决 (推荐/观望/回避)
    latest_valuation   最近估值 (USD, int)
    fair_value_low     估值区间下沿 (USD, int)
    fair_value_high    估值区间上沿 (USD, int)
    risk_level         整体风险 (low/medium/high/critical)
    rounds             融资轮次数
    report_path        markdown 研报绝对路径
    sources_hit        数据源 provenance 列表
    use_llm            是否启用 Claude 增强
    live               是否用 Ollama 实时推断
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_HISTORY_DIR = Path.home() / ".vc-research"
DEFAULT_HISTORY_FILE = DEFAULT_HISTORY_DIR / "history.jsonl"


def _resolve_history_path(path: Path | str | None = None) -> Path:
    """Env VC_HISTORY_PATH > 参数 > 默认."""
    env = os.getenv("VC_HISTORY_PATH")
    if env:
        return Path(env)
    if path:
        return Path(path)
    return DEFAULT_HISTORY_FILE


@dataclass
class HistoryEntry:
    """一条历史记录."""

    ts: str
    company: str
    verdict: str
    latest_valuation: int | None
    fair_value_low: int | None
    fair_value_high: int | None
    risk_level: str
    rounds: int
    report_path: str
    sources_hit: list[str] = field(default_factory=list)
    use_llm: bool = False
    live: bool = False


def record_report(
    company: str,
    verdict: str,
    latest_valuation: int | None,
    fair_value_low: int | None,
    fair_value_high: int | None,
    risk_level: str,
    rounds: int,
    report_path: Path | str,
    sources_hit: list[str],
    use_llm: bool = False,
    live: bool = False,
    history_path: Path | str | None = None,
) -> HistoryEntry:
    """追加一条研报生成记录."""
    entry = HistoryEntry(
        ts=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        company=company,
        verdict=verdict,
        latest_valuation=latest_valuation,
        fair_value_low=fair_value_low,
        fair_value_high=fair_value_high,
        risk_level=risk_level,
        rounds=rounds,
        report_path=str(Path(report_path).resolve()),
        sources_hit=list(sources_hit),
        use_llm=use_llm,
        live=live,
    )
    p = _resolve_history_path(history_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    return entry


def load_history(
    history_path: Path | str | None = None,
    limit: int | None = None,
    company: str | None = None,
) -> list[dict[str, Any]]:
    """读取历史记录,最新在前.

    Args:
        limit: 最多返回多少条
        company: 只返回指定公司的记录
    """
    p = _resolve_history_path(history_path)
    if not p.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            # 损坏行跳过,不打断查询
            continue
    if company:
        rows = [r for r in rows if r.get("company") == company]
    rows.sort(key=lambda r: r.get("ts", ""), reverse=True)
    if limit:
        rows = rows[:limit]
    return rows
