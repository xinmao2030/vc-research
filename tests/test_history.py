"""Tests for vc_research.history — JSONL append log + query."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from vc_research.history import HistoryEntry, load_history, record_report


@pytest.fixture
def hist_path(tmp_path, monkeypatch) -> Path:
    p = tmp_path / "history.jsonl"
    monkeypatch.setenv("VC_HISTORY_PATH", str(p))
    return p


def test_record_and_load_roundtrip(hist_path: Path) -> None:
    entry = record_report(
        company="影石创新",
        verdict="观望",
        latest_valuation=9_800_000_000,
        fair_value_low=7_000_000_000,
        fair_value_high=12_000_000_000,
        risk_level="high",
        rounds=6,
        report_path="/tmp/ins.md",
        sources_hit=["fixture", "wiki"],
        use_llm=False,
        live=False,
    )
    assert isinstance(entry, HistoryEntry)
    assert hist_path.exists()

    rows = load_history()
    assert len(rows) == 1
    r = rows[0]
    assert r["company"] == "影石创新"
    assert r["verdict"] == "观望"
    assert r["latest_valuation"] == 9_800_000_000
    assert r["sources_hit"] == ["fixture", "wiki"]
    assert r["report_path"].endswith("ins.md")


def test_load_sorted_newest_first(hist_path: Path) -> None:
    # 手动追加 3 条,ts 乱序
    lines = [
        {"ts": "2026-04-10T00:00:00+00:00", "company": "A", "verdict": "推荐"},
        {"ts": "2026-04-16T00:00:00+00:00", "company": "B", "verdict": "观望"},
        {"ts": "2026-04-12T00:00:00+00:00", "company": "C", "verdict": "回避"},
    ]
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    with hist_path.open("w", encoding="utf-8") as f:
        for line in lines:
            f.write(json.dumps(line) + "\n")

    rows = load_history()
    assert [r["company"] for r in rows] == ["B", "C", "A"]


def test_filter_by_company(hist_path: Path) -> None:
    for name in ("影石创新", "澜起科技", "影石创新"):
        record_report(
            company=name,
            verdict="观望",
            latest_valuation=1_000_000_000,
            fair_value_low=800_000_000,
            fair_value_high=1_500_000_000,
            risk_level="high",
            rounds=3,
            report_path=f"/tmp/{name}.md",
            sources_hit=["fixture"],
        )
    rows = load_history(company="影石创新")
    assert len(rows) == 2
    assert all(r["company"] == "影石创新" for r in rows)


def test_limit(hist_path: Path) -> None:
    for i in range(5):
        record_report(
            company=f"C{i}",
            verdict="推荐",
            latest_valuation=1_000_000,
            fair_value_low=800_000,
            fair_value_high=1_500_000,
            risk_level="low",
            rounds=1,
            report_path=f"/tmp/c{i}.md",
            sources_hit=["fixture"],
        )
    rows = load_history(limit=3)
    assert len(rows) == 3


def test_corrupt_line_tolerance(hist_path: Path) -> None:
    hist_path.parent.mkdir(parents=True, exist_ok=True)
    hist_path.write_text(
        '{"ts": "2026-04-16T00:00:00+00:00", "company": "Good"}\n'
        'this is not json\n'
        '{"ts": "2026-04-15T00:00:00+00:00", "company": "Also Good"}\n',
        encoding="utf-8",
    )
    rows = load_history()
    assert len(rows) == 2
    assert {r["company"] for r in rows} == {"Good", "Also Good"}


def test_empty_when_no_file(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("VC_HISTORY_PATH", str(tmp_path / "missing.jsonl"))
    assert load_history() == []


def test_env_var_overrides_arg(tmp_path, monkeypatch) -> None:
    env_path = tmp_path / "env.jsonl"
    arg_path = tmp_path / "arg.jsonl"
    monkeypatch.setenv("VC_HISTORY_PATH", str(env_path))
    record_report(
        company="X",
        verdict="推荐",
        latest_valuation=None,
        fair_value_low=None,
        fair_value_high=None,
        risk_level="low",
        rounds=0,
        report_path="/tmp/x.md",
        sources_hit=[],
        history_path=arg_path,  # 应被 env 覆盖
    )
    assert env_path.exists()
    assert not arg_path.exists()
