"""
Tests for GitHub Dorking Engine – Phase 3
"""
import pytest
from robin.github_dorking import (
    DORK_CATEGORIES,
    get_dork_categories,
    get_total_dork_count,
)


def test_dork_categories_exist():
    cats = DORK_CATEGORIES
    assert len(cats) >= 9  # At least 9 categories
    expected = [
        "api_keys", "cloud_credentials", "database_credentials",
        "private_keys", "oauth_tokens", "messaging_webhooks",
        "payment_credentials", "ci_cd_secrets", "miscellaneous"
    ]
    for cat in expected:
        assert cat in cats, f"Missing category: {cat}"


def test_total_dork_count_at_least_80():
    total = get_total_dork_count()
    assert total >= 80, f"Expected >= 80 dorks, got {total}"


def test_get_dork_categories_returns_counts():
    cats = get_dork_categories()
    for cat, count in cats.items():
        assert isinstance(count, int)
        assert count > 0, f"Category {cat} has no dorks"


def test_api_keys_category_has_enough():
    assert len(DORK_CATEGORIES["api_keys"]) >= 10


def test_cloud_credentials_category():
    assert len(DORK_CATEGORIES["cloud_credentials"]) >= 10


def test_database_credentials_category():
    assert len(DORK_CATEGORIES["database_credentials"]) >= 8


def test_private_keys_category():
    assert len(DORK_CATEGORIES["private_keys"]) >= 5
