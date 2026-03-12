import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from robin.ml_filter import MLFilterEngine

class TestMLMicroservice(unittest.TestCase):
    def setUp(self):
        self.engine = MLFilterEngine()

    @patch('requests.post')
    def test_is_sensitive_microservice_success(self, mock_post):
        # Mock API returning TP (1)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [1]
        mock_post.return_value = mock_response
        
        result = self.engine.is_sensitive("some suspected leak content here")
        self.assertTrue(result)
        
        # Mock API returning FP (0)
        mock_response.json.return_value = [0]
        result = self.engine.is_sensitive("fake content")
        self.assertFalse(result)

    @patch('requests.post')
    def test_is_sensitive_fallback_on_error(self, mock_post):
        # Mock API error
        mock_post.side_effect = Exception("API Down")
        
        # Should fallback to True (default) or local rules
        result = self.engine.is_sensitive("some content")
        self.assertTrue(result)

    def test_rule_based_prefilter(self):
        # Should be caught by rules before API call
        result = self.engine.is_sensitive("This is just a dummy test password=abc")
        self.assertFalse(result)

if __name__ == "__main__":
    unittest.main()
