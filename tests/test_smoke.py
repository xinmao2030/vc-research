"""烟雾测试 — 确保 6 个标杆案例都能跑通."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from vc_research.data_sources import DataAggregator
from vc_research.modules import (
    analyze_funding,
    analyze_industry,
    analyze_profile,
    analyze_recommendation,
    analyze_risks,
    analyze_thesis,
    analyze_valuation,
)
from vc_research.report import render_markdown
from vc_research.schema import VCReport


CASES = ["影石创新", "澜起科技", "银诺医药", "必贝特医药", "汉朔科技", "强一股份"]


@pytest.mark.parametrize("company", CASES)
def test_pipeline(company: str) -> None:
    raw = DataAggregator(use_fixtures=True).fetch(company)
    assert not raw.is_empty(), f"{company} fixture missing"

    profile = analyze_profile(raw)
    assert profile.name == company

    funding = analyze_funding(raw)
    assert len(funding.rounds) > 0

    thesis = analyze_thesis(raw)
    assert thesis.team_score >= 1

    industry = analyze_industry(raw, profile.industry)
    valuation = analyze_valuation(funding, thesis)
    risks = analyze_risks(raw, funding, thesis)
    rec = analyze_recommendation(thesis, valuation, risks, funding, profile)

    report = VCReport(
        generated_at=date.today(),
        profile=profile,
        funding=funding,
        thesis=thesis,
        industry=industry,
        valuation=valuation,
        risks=risks,
        recommendation=rec,
        data_sources=raw.sources_hit,
    )

    md = render_markdown(report)
    assert "模块 1 · 企业画像" in md
    assert "模块 7 · 投资建议" in md
    assert company in md


def test_education_layer() -> None:
    from vc_research.education import QuestProgress, explain_with_analogy

    progress = QuestProgress(company="影石创新")
    assert "profile" in progress.unlocked
    assert "funding" not in progress.unlocked

    hint = progress.complete("profile")
    assert hint and "融资轨迹" in hint
    assert "funding" in progress.unlocked

    text = explain_with_analogy("dilution")
    assert "蛋糕" in text
