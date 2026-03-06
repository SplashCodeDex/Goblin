import pytest
from src.robin.ml_filter import get_engine

def test_ml_filter_init():
    engine = get_engine()
    assert engine is not None
    assert len(engine.common_false_positives) > 0

def test_rule_based_filter():
    engine = get_engine()

    # It should identify "example" or "test" as false positive
    findings = [{'value': 'test_api_key_123', 'pattern_name': 'AWS Key'}]
    results = engine.filter_findings(findings, context="test_file.py")

    assert len(results) == 1
    assert results[0].is_false_positive is True
    assert results[0].model_used == 'rule_based'

def test_ml_heuristics_fallback():
    engine = get_engine()

    # Mocking that models failed to load
    engine.snippet_model = None
    engine.path_model = None

    findings = [{'value': 'super_secret_real_key_with_high_entropy_data_12345!', 'pattern_name': 'Generic Secret'}]
    real, fps = engine.filter_false_positives(findings, context="config/secrets.json")

    assert len(fps) == 0
    assert len(real) == 1
    assert real[0]['ml_filter']['is_false_positive'] is False
    assert real[0]['ml_filter']['model_used'] == 'none'
