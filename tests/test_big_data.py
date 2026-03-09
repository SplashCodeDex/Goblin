import unittest
import os
import gzip
from unittest.mock import patch, MagicMock
from src.robin.paste_scraper import PastebinHandler, PasteScraper, Watcher
from src.robin.dedup import ContentHasher
from src.robin.database import initialize_database, get_db_connection, check_for_near_duplicates
from src.robin.blob_store import BlobStore

class TestBigData(unittest.TestCase):
    def setUp(self):
        initialize_database()
        # Clean up any previous test blobs
        if not os.path.exists("data/blobs"):
            os.makedirs("data/blobs", exist_ok=True)

    def test_simhash_deduplication(self):
        content1 = "This is a large combolist with many entries. user1:pass1, user2:pass2, user3:pass3." * 100
        content2 = "MODIFIED HEADER: This is a large combolist with many entries. user1:pass1, user2:pass2, user3:pass3." * 100
        
        hash1 = ContentHasher.calculate_hash(content1)
        hash2 = ContentHasher.calculate_hash(content2)
        
        similarity = ContentHasher.get_similarity(hash1, hash2)
        self.assertGreater(similarity, 0.9) # Should be very similar
        self.assertTrue(ContentHasher.is_near_duplicate(hash1, hash2))

    @patch('src.robin.paste_scraper.PastebinHandler.scrape_paste')
    @patch('src.robin.paste_scraper.PastebinHandler.get_recent')
    def test_large_leak_to_blob(self, mock_recent, mock_scrape):
        # Create a 6MB synthetic leak (exceeds 5MB threshold)
        large_content = "api_key=sk-" + "A" * (6 * 1024 * 1024)
        mock_recent.return_value = [{'id': 'large999', 'url': 'http://test.com/large999', 'title': 'Massive Dump'}]
        mock_scrape.return_value = large_content
        
        scraper = PasteScraper([PastebinHandler()])
        watcher = Watcher(scraper)
        
        # Trigger processing
        watcher._process_new_paste("Pastebin", mock_recent.return_value[0])
        
        # Verify DB entry points to blob
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT content, content_hash FROM leaks WHERE external_id = 'large999'")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertTrue(row['content'].startswith("data/blobs/"))
        self.assertIsNotNone(row['content_hash'])
        
        # Verify physical blob exists and is compressed
        blob_path = row['content']
        self.assertTrue(os.path.exists(blob_path))
        with gzip.open(blob_path, 'rt', encoding='utf-8') as f:
            read_back = f.read()
            self.assertEqual(len(read_back), len(large_content))

    def test_parallel_chunk_scanner(self):
        from src.robin.paste_scraper import ParallelChunkScanner
        # Create content with keys in different chunks
        chunk1 = "key1=sk-1234567890abcdef1234567890abcdef\n" + "A" * 1024 * 1024
        chunk2 = "B" * 1024 * 1024 + "\nkey2=sk-abcdef1234567890abcdef1234567890"
        content = chunk1 + chunk2
        
        scanner = ParallelChunkScanner(chunk_size=1024 * 1024)
        matches = scanner.scan(content)
        
        # Should find both keys
        match_values = [m.value for m in matches]
        self.assertTrue(any("1234567890abcdef" in v for v in match_values))
        self.assertTrue(any("abcdef1234567890" in v for v in match_values))

if __name__ == '__main__':
    unittest.main()
