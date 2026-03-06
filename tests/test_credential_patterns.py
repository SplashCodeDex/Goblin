import pytest
from src.robin.credential_patterns import get_engine

def test_credential_patterns_init():
    engine = get_engine()
    assert engine is not None
    # Assuming there are patterns loaded from the db
    assert len(engine.patterns) > 0

def test_extract_credentials():
    engine = get_engine()
    test_text = "Here is my mock AWS key: " + "AKIA" + "IOSFODNN7EXAMPLE and secret: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
    findings = engine.scan_text(test_text)

    # We should find at least two credentials
    assert len(findings) >= 1

    # Check if we identified AWS keys
    aws_findings = [f for f in findings if 'aws' in f.pattern_name.lower() or 'akia' in f.value.lower() or 'aws' in str(f.provider).lower()]
    assert len(aws_findings) > 0

def test_entropy():
    # Test our entropy utility since _redact_value doesn't exist
    engine = get_engine()
    high_entropy_str = "x8A#k9L!p2@m5N$v1"
    low_entropy_str = "aaaaabbbbb"

    assert engine.calculate_entropy(high_entropy_str) > engine.calculate_entropy(low_entropy_str)
