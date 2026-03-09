import unittest
from unittest.mock import patch, MagicMock
from src.robin.paste_scraper import PastebinHandler
from src.robin.browser_engine import BrowserManager

class TestInvisibleScraper(unittest.TestCase):
    def setUp(self):
        self.browser_manager = BrowserManager()

    @patch('src.robin.browser_engine.uc.Chrome')
    def test_browser_manager_singleton(self, mock_chrome):
        # Verify singleton behavior
        bm1 = BrowserManager()
        bm2 = BrowserManager()
        self.assertIs(bm1, bm2)

    @patch('src.robin.scrape.requests.get')
    @patch('src.robin.browser_engine.BrowserManager.scrape_url')
    @patch('src.robin.scrape.renew_tor_identity')
    def test_adaptive_switching_on_403(self, mock_rotate, mock_scrape_url, mock_requests_get):
        # Simulate a 403 block on the first attempt
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.text = "Access Denied - Cloudflare"
        mock_requests_get.return_value = mock_response
        
        # Mock browser success
        mock_scrape_url.return_value = "<html><body>Paste Content</body></html>"
        
        handler = PastebinHandler()
        # Initial state: use_browser should be False
        self.assertFalse(handler.use_browser)
        
        # Trigger scrape_paste (which calls _get_request_adaptive)
        result = handler.scrape_paste("abc123")
        
        # Verify:
        # 1. Requests was called
        # 2. Tor rotation was triggered
        # 3. use_browser is now True
        # 4. BrowserManager.scrape_url was called as fallback
        self.assertTrue(handler.use_browser)
        mock_rotate.assert_called_once()
        mock_scrape_url.assert_called_with("https://pastebin.com/raw/abc123", wait_for_selector=None, timeout=30)
        self.assertIn("Paste Content", result)

    @patch('src.robin.browser_engine.BrowserManager.get_driver')
    def test_browser_quit(self, mock_get_driver):
        mock_driver = MagicMock()
        self.browser_manager.driver = mock_driver
        self.browser_manager.quit_driver()
        
        mock_driver.quit.assert_called_once()
        self.assertIsNone(self.browser_manager.driver)

if __name__ == '__main__':
    unittest.main()
