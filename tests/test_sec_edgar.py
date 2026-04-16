"""SecEdgarSource 单元测试 — 使用 mocked httpx.Client.

真实网络测试用 `-m live` 标记,CI 跳过。
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from vc_research.data_sources.sec_edgar_source import (
    SecEdgarSource,
    _extract_key_facts,
    _format_addr,
    _format_recent_filings,
)


def test_unknown_company_returns_none():
    src = SecEdgarSource()
    assert src.fetch("不存在公司") is None


def test_format_addr_partial():
    assert _format_addr({"city": "Shanghai"}) == "Shanghai"
    assert _format_addr({}) == ""
    assert _format_addr({"city": "Basel", "zipCode": "4051"}) == "Basel · 4051"


def test_format_recent_filings_filters_forms():
    recent = {
        "form": ["10-K", "DEF 14A", "20-F", "3"],
        "filingDate": ["2024-02-20", "2024-03-15", "2024-04-01", "2024-01-05"],
        "accessionNumber": ["acc-1", "acc-2", "acc-3", "acc-4"],
        "primaryDocument": ["a.htm", "b.htm", "c.htm", "d.htm"],
    }
    out = _format_recent_filings(recent)
    assert len(out) == 2
    assert out[0]["form"] == "10-K"
    assert out[1]["form"] == "20-F"
    assert out[1]["accession"] == "acc-3"


def test_extract_key_facts_picks_latest_fy():
    facts = {
        "facts": {
            "us-gaap": {
                "Revenues": {
                    "units": {
                        "USD": [
                            {"end": "2022-12-31", "val": 100, "fy": 2022, "fp": "FY"},
                            {"end": "2023-12-31", "val": 200, "fy": 2023, "fp": "FY"},
                            {"end": "2023-06-30", "val": 90, "fy": 2023, "fp": "Q2"},
                        ]
                    }
                }
            }
        }
    }
    out = _extract_key_facts(facts)
    assert "Revenues_USD" in out
    assert out["Revenues_USD"][0]["fy"] == 2023
    assert out["Revenues_USD"][0]["val"] == 200


def test_fetch_with_mocked_response():
    src = SecEdgarSource(user_agent="test/1.0 a@b.c")
    fake_sub = {
        "name": "NIO Inc.",
        "tickers": ["NIO"],
        "exchanges": ["NYSE"],
        "sicDescription": "Motor Vehicles",
        "stateOfIncorporation": "E9",
        "addresses": {"business": {"city": "Shanghai", "stateOrCountry": "F4"}},
        "filings": {"recent": {"form": [], "filingDate": [], "accessionNumber": [], "primaryDocument": []}},
    }
    with patch.object(src, "_get", side_effect=[fake_sub, None]):
        payload = src.fetch("蔚来")
    assert payload is not None
    assert payload["legal_name"] == "NIO Inc."
    assert payload["ticker"] == "NIO"
    assert payload["exchanges"] == "NYSE"
    assert payload["cik"] == "0001736541"


def test_fetch_404_returns_none():
    src = SecEdgarSource()
    with patch.object(src, "_get", return_value=None):
        assert src.fetch("蔚来") is None
