"""
Tests for Breach Lookup Engine – Phase 2 enhancements
"""
import pytest
from robin.breach_lookup import BreachLookupEngine, get_engine


def test_engine_init():
    engine = BreachLookupEngine()
    assert engine is not None


def test_extract_emails():
    engine = BreachLookupEngine()
    text = "Contact us at test@example.com or admin@goblin.io — not an email."
    emails = engine.extract_emails_from_text(text)
    assert "test@example.com" in emails
    assert "admin@goblin.io" in emails


def test_no_api_keys_returns_none():
    engine = BreachLookupEngine()
    # With no API keys, lookup should return None
    if not engine.enabled_sources:
        result = engine.lookup_email("test@example.com")
        assert result is None


def test_cache_stats_structure():
    engine = BreachLookupEngine()
    stats = engine.get_cache_stats()
    assert "total_cached_emails" in stats
    assert "enabled_sources" in stats
    assert "all_sources" in stats
    assert "source_count" in stats
    assert "total_source_count" in stats
    assert stats["total_source_count"] == 7  # 7 configured APIs


def test_all_seven_sources_configured():
    engine = BreachLookupEngine()
    expected_sources = ['hibp', 'snusbase', 'dehashed', 'intelx', 'leaklookup', 'weleakinfo', 'scylla']
    for src in expected_sources:
        assert src in engine.api_keys, f"Missing source: {src}"


def test_breach_statistics_structure():
    engine = BreachLookupEngine()
    stats = engine.get_breach_statistics()
    assert "unique_breaches" in stats
    assert "data_classes" in stats
    assert "sources" in stats
    assert "total_leaked_passwords" in stats


def test_engine_singleton():
    e1 = get_engine()
    e2 = get_engine()
    assert e1 is e2
