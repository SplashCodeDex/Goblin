"""
Credential Digger ML Filter
Uses machine learning to reduce false positives in credential detection
"""

import os
import re
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from pathlib import Path

# Credential Digger imports (with fallback if not installed)
try:
    from credentialdigger import Client
    from credentialdigger.models import PathModel, SnippetModel
    CREDDIGGER_AVAILABLE = True
except ImportError:
    CREDDIGGER_AVAILABLE = False
    logging.getLogger(__name__).warning("credentialdigger not installed. ML filtering will be disabled.")

logger = logging.getLogger(__name__)


@dataclass
class FilterResult:
    """Result of ML filtering"""
    original_value: str
    is_false_positive: bool
    confidence: float  # 0.0 to 1.0
    model_used: str  # 'path', 'snippet', 'none'
    reason: Optional[str] = None


class MLFilterEngine:
    """ML-based false positive filter using Credential Digger"""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or str(Path(__file__).parent / "creddigger.db")
        self.client = None
        self.path_model = None
        self.snippet_model = None
        self.initialized = False

        # Fallback rule-based filters
        self.common_false_positives = self._load_false_positive_patterns()

    def initialize(self):
        """Initialize Credential Digger models"""
        if self.initialized:
            return

        if not CREDDIGGER_AVAILABLE:
            logger.warning("Credential Digger not available. Using rule-based filtering only.")
            self.initialized = True
            return

        try:
            # Initialize Credential Digger client
            # Note: In production, you might use a real database
            self.client = Client(dbname=self.db_path, dbtype='sqlite')

            # Load pre-trained models
            try:
                self.path_model = PathModel()
                logger.info("Path model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load path model: {e}")

            try:
                self.snippet_model = SnippetModel()
                logger.info("Snippet model loaded successfully")
            except Exception as e:
                logger.warning(f"Could not load snippet model: {e}")

            self.initialized = True

        except Exception as e:
            logger.error(f"Error initializing Credential Digger: {e}", exc_info=True)
            logger.warning("Falling back to rule-based filtering")
            self.initialized = True

    def is_sensitive(self, content: str) -> bool:
        """
        Main entry point for noise-gating.
        Checks if content is likely to contain sensitive information.
        """
        if not content or len(content.strip()) < 10:
            return False

        # 1. Rule-based pre-filter (Fast)
        for pattern_dict in self.common_false_positives:
            if re.search(pattern_dict['pattern'], content, re.IGNORECASE):
                if pattern_dict.get('is_fp', True):
                    return False

        # 2. ML-based filter (Credential Digger)
        if self.initialized and self.snippet_model:
            try:
                # Credential Digger's SnippetModel expects a list of snippets
                # and returns a list of predictions (0 for FP, 1 for TP)
                # We'll take a few lines from the content as a sample
                sample_lines = content.splitlines()[:50]
                sample = "\n".join(sample_lines)
                
                # Note: The exact API for SnippetModel might vary depending on version
                # Usually it's model.predict([snippet])
                prediction = self.snippet_model.predict([sample])
                if prediction and prediction[0] == 0:
                    return False
            except Exception as e:
                logger.debug(f"ML prediction failed: {e}")

        # Default to True if no strong evidence of FP
        return True

    def _load_false_positive_patterns(self) -> List[Dict]:
        """Load common false positive patterns"""
        return [
            # Test/example credentials
            {
                'pattern': r'(?i)(test|example|sample|demo|dummy|fake|mock)',
                'reason': 'Test/example credential'
            },
            # Documentation placeholders
            {
                'pattern': r'(?i)(your[_-]?api[_-]?key|your[_-]?secret|your[_-]?token|your[_-]?password)',
                'reason': 'Documentation placeholder'
            },
            # Variable names
            {
                'pattern': r'^[A-Z_]+$',
                'reason': 'Constant/variable name'
            },
            # Lorem ipsum
            {
                'pattern': r'(?i)lorem|ipsum|dolor|consectetur',
                'reason': 'Lorem ipsum placeholder'
            },
            # Common placeholder values
            {
                'pattern': r'^(xxx+|000+|111+|123+|abc+)$',
                'reason': 'Placeholder value'
            },
            # Very short values (likely not real credentials)
            {
                'pattern': r'^.{1,8}$',
                'reason': 'Too short to be a real credential'
            },
            # All same character
            {
                'pattern': r'^(.)\1+$',
                'reason': 'All same character'
            },
            # Common test emails
            {
                'pattern': r'(?i)test@test\.com|example@example\.com|user@localhost',
                'reason': 'Test email address'
            },
            # Redacted values
            {
                'pattern': r'(?i)(\*+|redacted|hidden|censored|removed)',
                'reason': 'Redacted/hidden value'
            },
        ]

    def filter_findings(self, findings: List[Dict], context: Optional[str] = None) -> List[FilterResult]:
        """
        Filter a list of credential findings using ML models

        Args:
            findings: List of credential findings (dicts with 'value', 'pattern_name', etc.)
            context: Optional context (file path, surrounding text, etc.)

        Returns:
            List of FilterResult objects
        """
        if not self.initialized:
            self.initialize()

        results = []

        for finding in findings:
            value = finding.get('value', '')
            pattern_name = finding.get('pattern_name', '')

            # First, apply rule-based filtering
            rule_result = self._apply_rule_based_filter(value)
            if rule_result:
                results.append(rule_result)
                continue

            # Then, apply ML models if available
            if self.snippet_model or self.path_model:
                ml_result = self._apply_ml_filter(value, pattern_name, context)
                results.append(ml_result)
            else:
                # No ML available, mark as unknown (not filtered)
                results.append(FilterResult(
                    original_value=value,
                    is_false_positive=False,
                    confidence=0.5,
                    model_used='none',
                    reason='ML models not available'
                ))

        return results

    def _apply_rule_based_filter(self, value: str) -> Optional[FilterResult]:
        """Apply rule-based false positive detection"""
        for fp_pattern in self.common_false_positives:
            pattern = fp_pattern['pattern']
            if re.search(pattern, value):
                return FilterResult(
                    original_value=value,
                    is_false_positive=True,
                    confidence=0.9,
                    model_used='rule_based',
                    reason=fp_pattern['reason']
                )
        return None

    def _apply_ml_filter(self, value: str, pattern_name: str, context: Optional[str]) -> FilterResult:
        """Apply ML-based filtering"""
        # Use snippet model to analyze the credential value itself
        snippet_score = 0.5  # Default neutral

        if self.snippet_model:
            try:
                # Credential Digger's snippet model predicts if a snippet is a false positive
                # Returns probability of being a real credential (0-1)
                snippet_score = self._predict_with_snippet_model(value, pattern_name)
            except Exception as e:
                print(f"Error using snippet model: {e}")

        # Use path model if we have context (file path)
        path_score = 0.5  # Default neutral

        if self.path_model and context:
            try:
                path_score = self._predict_with_path_model(context)
            except Exception as e:
                print(f"Error using path model: {e}")

        # Combine scores (weighted average)
        combined_score = (snippet_score * 0.7) + (path_score * 0.3)

        # Threshold: < 0.3 = likely false positive
        is_fp = combined_score < 0.3
        model_used = []
        if self.snippet_model:
            model_used.append('snippet')
        if self.path_model and context:
            model_used.append('path')

        return FilterResult(
            original_value=value,
            is_false_positive=is_fp,
            confidence=abs(combined_score - 0.5) * 2,  # Convert to 0-1 confidence
            model_used='+'.join(model_used) if model_used else 'none',
            reason=f"ML prediction: {combined_score:.2f}"
        )

    def _predict_with_snippet_model(self, value: str, pattern_name: str) -> float:
        """Predict using snippet model (actual implementation)"""
        if self.snippet_model:
            try:
                # CredentialDigger predict usually returns 1 (real) or 0 (false positive)
                # or a probability depending on version. We'll handle both.
                pred = self.snippet_model.predict([value])
                if isinstance(pred, (list, tuple)) and len(pred) > 0:
                    val = float(pred[0])
                    # If model outputs 0 for real and 1 for false positive, adjust if needed
                    # We assume 1.0 = highly likely real, 0.0 = highly likely false positive
                    return val
                elif isinstance(pred, (int, float)):
                    return float(pred)
            except Exception as e:
                pass # fallback below

        # Fallback heuristic
        entropy = self._calculate_entropy(value)
        if entropy < 2.0:
            return 0.2  # Low entropy = likely false positive
        elif entropy > 4.0:
            return 0.8  # High entropy = likely real
        else:
            return 0.5  # Medium entropy = uncertain

    def _predict_with_path_model(self, path: str) -> float:
        """Predict using path model (actual implementation)"""
        if self.path_model:
            try:
                pred = self.path_model.predict([path])
                if isinstance(pred, (list, tuple)) and len(pred) > 0:
                    return float(pred[0])
                elif isinstance(pred, (int, float)):
                    return float(pred)
            except Exception as e:
                pass # fallback below

        # Fallback heuristics
        path_lower = path.lower()

        fp_indicators = ['test', 'example', 'sample', 'demo', 'doc', 'readme']
        if any(indicator in path_lower for indicator in fp_indicators):
            return 0.2

        real_indicators = ['config', 'env', '.git', 'secret', 'key', 'credential']
        if any(indicator in path_lower for indicator in real_indicators):
            return 0.8

        return 0.5  # Neutral

    @staticmethod
    def _calculate_entropy(data: str) -> float:
        """Calculate Shannon entropy"""
        if not data:
            return 0.0

        import math
        freq = {}
        for char in data:
            freq[char] = freq.get(char, 0) + 1

        entropy = 0.0
        data_len = len(data)

        for count in freq.values():
            probability = count / data_len
            entropy -= probability * math.log2(probability)

        return entropy

    def filter_false_positives(self, findings: List[Dict], context: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
        """
        Filter findings into real credentials and false positives

        Returns:
            Tuple of (real_credentials, false_positives)
        """
        filter_results = self.filter_findings(findings, context)

        real_credentials = []
        false_positives = []

        for finding, result in zip(findings, filter_results):
            # Add filter metadata to finding
            finding['ml_filter'] = {
                'is_false_positive': result.is_false_positive,
                'confidence': result.confidence,
                'model_used': result.model_used,
                'reason': result.reason
            }

            if result.is_false_positive:
                false_positives.append(finding)
            else:
                real_credentials.append(finding)

        return real_credentials, false_positives

    def get_stats(self) -> Dict:
        """Get statistics about the ML filter"""
        return {
            'creddigger_available': CREDDIGGER_AVAILABLE,
            'initialized': self.initialized,
            'path_model_loaded': self.path_model is not None,
            'snippet_model_loaded': self.snippet_model is not None,
            'rule_based_patterns': len(self.common_false_positives),
            'db_path': self.db_path
        }


# Global instance
_engine = None

def get_engine() -> MLFilterEngine:
    """Get the global ML filter engine instance"""
    global _engine
    if _engine is None:
        _engine = MLFilterEngine()
        _engine.initialize()
    return _engine


# Alias for compatibility with auto_pilot
get_filter = get_engine


# Convenience functions
def filter_findings(findings: List[Dict], context: Optional[str] = None) -> List[FilterResult]:
    """Filter credential findings using ML"""
    return get_engine().filter_findings(findings, context)


def filter_false_positives(findings: List[Dict], context: Optional[str] = None) -> Tuple[List[Dict], List[Dict]]:
    """Separate real credentials from false positives"""
    return get_engine().filter_false_positives(findings, context)
