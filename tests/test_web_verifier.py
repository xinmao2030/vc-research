"""WebVerifier 单元测试 — 全部 mock,不依赖 Perplexity API."""

from __future__ import annotations

import json

import pytest

from vc_research.data_sources.aggregator import RawCompanyData
from vc_research.data_sources.web_verifier import (
    ClaimVerification,
    VerificationReport,
    VerifyStatus,
    WebVerifier,
    _extract_json_array,
)


# ── fixtures ──────────────────────────────────────────────


class FakePerplexity:
    name = "perplexity"

    def __init__(self, response_items: list[dict] | None = None, error: Exception | None = None):
        self._items = response_items or []
        self._error = error

    def complete_with_citations(self, system, user, *, max_tokens=4096, temperature=0.1):
        if self._error:
            raise self._error
        return json.dumps(self._items, ensure_ascii=False), ["https://example.com"]

    @property
    def available(self):
        return True

    @property
    def model_id(self):
        return "sonar-fake"


def _make_raw(name: str = "TestCo", **kwargs) -> RawCompanyData:
    return RawCompanyData(name=name, **kwargs)


# ── VerificationReport ────────────────────────────────────


class TestVerificationReport:
    def test_empty_report(self):
        r = VerificationReport(company="X")
        assert r.confirmed_count == 0
        assert r.disputed_count == 0
        assert r.confidence_pct == 0.0
        assert "X" in r.summary()

    def test_counts(self):
        r = VerificationReport(
            company="X",
            claims=[
                ClaimVerification("a", "founding", VerifyStatus.CONFIRMED, "v", "v"),
                ClaimVerification("b", "funding", VerifyStatus.CONFIRMED, "v", "v"),
                ClaimVerification("c", "exec", VerifyStatus.DISPUTED, "v1", "v2"),
                ClaimVerification("d", "product", VerifyStatus.UNVERIFIABLE, "", ""),
            ],
        )
        assert r.confirmed_count == 2
        assert r.disputed_count == 1
        # confidence = 2 / 3 (excluding unverifiable)
        assert abs(r.confidence_pct - 66.67) < 1

    def test_disputed_items(self):
        c = ClaimVerification("bad", "funding", VerifyStatus.DISPUTED, "1M", "2M")
        r = VerificationReport(company="X", claims=[c])
        assert r.disputed_items() == [c]


# ── _extract_json_array ──────────────────────────────────


class TestExtractJsonArray:
    def test_plain_array(self):
        assert _extract_json_array('[{"a": 1}]') == [{"a": 1}]

    def test_markdown_fenced(self):
        text = '```json\n[{"x": 2}]\n```'
        assert _extract_json_array(text) == [{"x": 2}]

    def test_with_think_tags(self):
        text = '<think>thinking...</think>\n[{"y": 3}]'
        assert _extract_json_array(text) == [{"y": 3}]

    def test_embedded_in_text(self):
        text = 'Here is the result: [{"z": 4}] done.'
        assert _extract_json_array(text) == [{"z": 4}]

    def test_invalid_raises(self):
        with pytest.raises((json.JSONDecodeError, ValueError)):
            _extract_json_array("not json at all")


# ── WebVerifier._extract_claims ──────────────────────────


class TestExtractClaims:
    def test_extracts_from_itjuzi(self):
        raw = _make_raw(
            itjuzi={
                "founded_date": "2020-01-15",
                "founders": [{"name": "张三", "title": "CEO"}],
                "headquarters": "北京",
                "funding_rounds": [
                    {"stage": "A轮", "amount_usd": 10_000_000, "lead_investors": ["红杉"]}
                ],
                "products": ["产品A", "产品B"],
            }
        )
        v = WebVerifier(provider=FakePerplexity())
        claims = v._extract_claims(raw)
        categories = [c["category"] for c in claims]
        assert "founding" in categories
        assert "executive" in categories
        assert "funding" in categories
        assert "product" in categories

    def test_empty_raw(self):
        raw = _make_raw()
        v = WebVerifier(provider=FakePerplexity())
        assert v._extract_claims(raw) == []


# ── WebVerifier.verify ───────────────────────────────────


class TestVerify:
    def test_happy_path(self):
        fake_response = [
            {
                "claim": "成立日期: 2020-01-15",
                "category": "founding",
                "status": "confirmed",
                "web_value": "2020-01-15",
                "notes": "匹配",
            },
            {
                "claim": "创始人: 张三",
                "category": "executive",
                "status": "disputed",
                "web_value": "李四",
                "notes": "实际创始人是李四",
            },
        ]
        raw = _make_raw(
            itjuzi={
                "founded_date": "2020-01-15",
                "founders": [{"name": "张三", "title": "CEO"}],
            }
        )
        v = WebVerifier(provider=FakePerplexity(response_items=fake_response))
        report = v.verify(raw)
        assert report.company == "TestCo"
        assert report.confirmed_count == 1
        assert report.disputed_count == 1

    def test_empty_data_returns_empty_report(self):
        raw = _make_raw()
        v = WebVerifier(provider=FakePerplexity())
        report = v.verify(raw)
        assert len(report.claims) == 0

    def test_api_error_graceful(self):
        raw = _make_raw(
            crunchbase={"founded_date": "2019-06-01"}
        )
        v = WebVerifier(provider=FakePerplexity(error=RuntimeError("API down")))
        report = v.verify(raw)
        assert len(report.claims) == 1
        assert report.claims[0].status == VerifyStatus.UNVERIFIABLE
        assert "API down" in report.claims[0].notes

    def test_unparseable_response(self):
        class BadProvider:
            name = "bad"

            def complete_with_citations(self, system, user, **kw):
                return "not json at all", []

            @property
            def available(self):
                return True

            @property
            def model_id(self):
                return "bad"

        raw = _make_raw(itjuzi={"founded_date": "2020"})
        v = WebVerifier(provider=BadProvider())
        report = v.verify(raw)
        # 降级: 原始 claims 标记 unverifiable
        assert all(c.status == VerifyStatus.UNVERIFIABLE for c in report.claims)
