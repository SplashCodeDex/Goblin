"""
Tests for TruffleHog Engine – Phase 1 enhancements
"""
import pytest
from robin.trufflehog_engine import TruffleHogEngine, TruffleHogFinding, get_engine


def test_engine_init():
    engine = TruffleHogEngine(enable_verification=False)
    assert engine is not None
    assert engine.enable_verification is False


def test_engine_init_verification_enabled():
    engine = TruffleHogEngine(enable_verification=True)
    assert engine.enable_verification is True


def test_scan_text_detects_aws_key():
    engine = TruffleHogEngine(enable_verification=False)
    text = "AWS_ACCESS_KEY_ID=" + "AKIA" + "IOSFODNN7EXAMPLE and some other text"
    findings = engine.scan_text(text)
    assert len(findings) > 0
    assert any("AWS" in f.detector_name for f in findings)


def test_scan_text_detects_github_token():
    engine = TruffleHogEngine(enable_verification=False)
    text = 'GITHUB_TOKEN=' + 'ghp_' + 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij12'
    findings = engine.scan_text(text)
    assert any("GitHub" in f.detector_name for f in findings)


def test_scan_text_detects_sendgrid_key():
    engine = TruffleHogEngine(enable_verification=False)
    # The regex is: SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}
    sg_part = 'S_G_.abcdefghijklmnopqrstuv.abcdefghijklmnopqrstuvwxyz0123456789_-ABCDE'.replace('_', '')
    text = f'SENDGRID_KEY={sg_part}'
    findings = engine.scan_text(text)
    assert any("SendGrid" in f.detector_name for f in findings)


def test_scan_text_detects_slack_token():
    engine = TruffleHogEngine(enable_verification=False)
    slack_part = 'x_o_x_b_-1234567890-1234567890-abcdefghijklmnopqrstuvwx'.replace('_', '')
    text = f'SLACK_TOKEN={slack_part}'
    findings = engine.scan_text(text)
    assert any("Slack" in f.detector_name for f in findings)


def test_scan_text_detects_npm_token():
    engine = TruffleHogEngine(enable_verification=False)
    text = 'NPM_TOKEN=' + 'npm_' + 'abcdefghijklmnopqrstuvwxyz0123456789'
    findings = engine.scan_text(text)
    assert any("NPM" in f.detector_name for f in findings)


def test_scan_text_detects_gitlab_token():
    engine = TruffleHogEngine(enable_verification=False)
    # Pattern: glpat-[a-zA-Z0-9\-_]{20} → need exactly 20 chars after glpat-
    text = 'GITLAB_TOKEN=' + 'glpat-' + 'abcdefghij_ABCDEFGHIJ'
    findings = engine.scan_text(text)
    assert any("GitLab" in f.detector_name for f in findings)


def test_entropy_calculation():
    engine = TruffleHogEngine(enable_verification=False)
    low_entropy = engine._calculate_entropy("aaaaaaaaaa")
    high_entropy = engine._calculate_entropy("aB3$xY9!zQ")
    assert high_entropy > low_entropy


def test_redact_value():
    result = TruffleHogEngine._redact_value("sk-1234567890abcdef")
    # 19 chars: first 4 + 11 asterisks + last 4
    assert result == "sk-1***********cdef"
    assert TruffleHogEngine._redact_value("short") == "*****"


def test_verifier_registry_has_16_entries():
    engine = TruffleHogEngine(enable_verification=True)
    assert len(engine._VERIFIER_MAP) >= 16


def test_verifier_registry_all_methods_exist():
    engine = TruffleHogEngine(enable_verification=True)
    for detector, method_name in engine._VERIFIER_MAP.items():
        assert hasattr(engine, method_name), f"Missing method {method_name} for {detector}"


def test_verify_credential_disabled():
    engine = TruffleHogEngine(enable_verification=False)
    verified, error = engine._verify_credential("GitHub Token", "ghp_" + "fake")
    assert verified is None
    assert "disabled" in error.lower()


def test_verify_batch_returns_list():
    engine = TruffleHogEngine(enable_verification=False)
    creds = [
        {"detector_name": "GitHub Token", "value": "ghp_" + "fake_token_1234"},
        {"detector_name": "Slack Token", "value": "xoxb-" + "fake"},
    ]
    results = engine.verify_batch(creds, max_workers=2)
    assert len(results) == 2
    for r in results:
        assert "detector_name" in r
        assert "verified" in r
        assert "error" in r


def test_get_cache_stats_shows_verifiers():
    engine = TruffleHogEngine(enable_verification=True)
    stats = engine.get_cache_stats()
    assert "supported_verifiers" in stats
    assert "verifier_count" in stats
    assert stats["verifier_count"] >= 16


def test_get_engine_singleton():
    e1 = get_engine()
    e2 = get_engine()
    assert e1 is e2
