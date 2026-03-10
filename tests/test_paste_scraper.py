import unittest
from unittest.mock import patch, MagicMock
from src.robin.paste_scraper import PastebinHandler, PasteScraper, Watcher
from src.robin.database import initialize_database, get_db_connection

class TestPasteScraper(unittest.TestCase):
    def setUp(self):
        # Ensure database is initialized
        initialize_database()

    @patch('src.robin.paste_scraper.PasteSource._get_request_adaptive')
    def test_pastebin_handler_recent(self, mock_adaptive):
        # Mock HTML response for Pastebin archive
        mock_adaptive.return_value = """
        <table class="maintable">
            <tr><th>Title</th><th>Added</th><th>Author</th><th>Syntax</th></tr>
            <tr>
                <td><a href="/abc123">Test Paste</a></td>
                <td>1 min ago</td>
                <td>Guest</td>
                <td>Python</td>
            </tr>
        </table>
        """
        
        handler = PastebinHandler()
        recent = handler.get_recent()
        
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]['id'], 'abc123')
        self.assertEqual(recent[0]['title'], 'Test Paste')

    @patch('src.robin.paste_scraper.PastebinHandler.scrape_paste_stream')
    @patch('src.robin.paste_scraper.PastebinHandler.get_recent')
    def test_watcher_processing(self, mock_recent, mock_stream):
        # Mock finding a new paste
        mock_recent.return_value = [{'id': 'new123', 'url': 'http://test.com/new123', 'title': 'Leak Test'}]
        
        def side_effect(paste_id, callback):
            callback("password=12345\napi_key=sk-1234567890abcdef1234567890abcdef")
            return True
        mock_stream.side_effect = side_effect
        
        scraper = PasteScraper([PastebinHandler()])
        watcher = Watcher(scraper, poll_interval=1)
        
        # Manually trigger process_new_paste to avoid infinite loop
        watcher._process_new_paste("Pastebin", mock_recent.return_value[0])
        
        # Verify it was saved to database
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM leaks WHERE external_id = 'new123'")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertEqual(row['source_name'], 'Pastebin')
        # Check if relevance score was calculated (sk- key should give some score)
        self.assertGreater(row['relevance_score'], 0)

if __name__ == '__main__':
    unittest.main()
