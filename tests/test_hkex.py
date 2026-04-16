"""HkexSource 单元测试 — 纯静态 symbology,无网络调用."""

from __future__ import annotations

from vc_research.data_sources.hkex_source import HkexSource, lookup_hk_ticker


def test_unknown_company_returns_none():
    src = HkexSource()
    assert src.fetch("不存在的公司") is None


def test_fetch_xiaomi():
    src = HkexSource()
    payload = src.fetch("小米")
    assert payload is not None
    assert payload["hk_ticker"] == "01810"
    assert payload["hk_ticker_full"] == "01810.HK"
    assert "01810" in payload["hkex_profile_url"]
    assert "01810" in payload["hkex_search_url"]


def test_fetch_handles_english_alias():
    src = HkexSource()
    assert src.fetch("Xiaomi")["hk_ticker"] == "01810"
    assert src.fetch("NIO")["hk_ticker"] == "09866"
    assert src.fetch("SenseTime")["hk_ticker"] == "00020"


def test_lookup_hk_ticker_helper():
    assert lookup_hk_ticker("腾讯") == "00700"
    assert lookup_hk_ticker("阿里巴巴") == "09988"
    assert lookup_hk_ticker("unknown") is None


def test_source_metadata():
    src = HkexSource()
    assert src.name == "hkex"
    assert "港交所" in src.provenance
