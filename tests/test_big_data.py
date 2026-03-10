import unittest
import os
import gzip
import logging
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
        
        # Clear leaks table for fresh tests
        conn = get_db_connection()
        conn.execute("DELETE FROM leaks")
        conn.execute("DELETE FROM paste_metadata")
        conn.commit()
        conn.close()

    def test_simhash_deduplication(self):
        content1 = "This is a large combolist with many entries. user1:pass1, user2:pass2, user3:pass3." * 100
        content2 = "MODIFIED HEADER: This is a large combolist with many entries. user1:pass1, user2:pass2, user3:pass3." * 100
        
        hash1 = ContentHasher.calculate_hash(content1)
        hash2 = ContentHasher.calculate_hash(content2)
        
        similarity = ContentHasher.get_similarity(hash1, hash2)
        self.assertGreater(similarity, 0.9) # Should be very similar
        self.assertTrue(ContentHasher.is_near_duplicate(hash1, hash2))

    @patch('src.robin.llm.generate_summary')
    @patch('src.robin.llm.get_llm')
    @patch('src.robin.paste_scraper.PastebinHandler.scrape_paste_stream')
    @patch('src.robin.paste_scraper.PastebinHandler.get_recent')
    def test_large_leak_to_blob(self, mock_recent, mock_scrape_stream, mock_get_llm, mock_gen_summary):
        # Setup mocks
        mock_gen_summary.return_value = "Synthetic summary"
        mock_get_llm.return_value = MagicMock()
        
        # Create a 100KB synthetic leak (exceeds 50KB threshold)
        large_content = "api_key=sk-1234567890abcdef1234567890abcdef\n" + "A" * (100 * 1024)
        
        def side_effect(paste_id, callback, chunk_size=1024*1024):
            callback(large_content)
            return True
        
        mock_scrape_stream.side_effect = side_effect
        mock_recent.return_value = [{'id': 'large999', 'url': 'http://test.com/large999', 'title': 'Massive Dump'}]
        
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

    @patch('src.robin.llm.generate_summary')
    @patch('src.robin.llm.get_llm')
    @patch('src.robin.paste_scraper.PastebinHandler.scrape_paste_stream')
    @patch('src.robin.paste_scraper.PastebinHandler.get_recent')
    def test_stress_50mb_leak(self, mock_recent, mock_scrape_stream, mock_get_llm, mock_gen_summary):
        """Phase 4: Stress test with 50MB synthetic leak"""
        mock_gen_summary.return_value = "Synthetic summary"
        mock_get_llm.return_value = MagicMock()
        
        # Simulate a 50MB stream by calling callback multiple times
        def side_effect(paste_id, callback, chunk_size=1024*1024):
            # Send 50 chunks of 1MB
            for i in range(50):
                callback("A" * (1024 * 1024))
            # Include a key at the end
            callback("\napi_key=sk-STRESS50MBTESTING1234567890ABCDEF")
            return True
        
        mock_scrape_stream.side_effect = side_effect
        mock_recent.return_value = [{'id': 'stress50', 'url': 'http://test.com/stress50', 'title': '50MB Stress'}]
        
        scraper = PasteScraper([PastebinHandler()])
        watcher = Watcher(scraper)
        
        import psutil
        process = psutil.Process(os.getpid())
        start_mem = process.memory_info().rss / (1024 * 1024)
        
        # Trigger processing
        watcher._process_new_paste("Pastebin", mock_recent.return_value[0])
        
        end_mem = process.memory_info().rss / (1024 * 1024)
        peak_diff = end_mem - start_mem
        
        print(f"\n[STRESS TEST] Memory diff: {peak_diff:.2f}MB")
        
        # Verify peak RSS memory usage remains under 100MB extra
        # Note: psutil.rss is not always perfect for "peak", but gives a good idea.
        self.assertLess(peak_diff, 100)
        
        # Verify DB entry
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT content FROM leaks WHERE external_id = 'stress50'")
        row = cursor.fetchone()
        conn.close()
        
        self.assertIsNotNone(row)
        self.assertTrue(row['content'].startswith("data/blobs/"))

    @patch('src.robin.llm.generate_summary')
    @patch('src.robin.llm.get_llm')
    @patch('src.robin.paste_scraper.PastebinHandler.scrape_paste_stream')
    @patch('src.robin.paste_scraper.PastebinHandler.get_recent')
    def test_end_to_end_dedup(self, mock_recent, mock_scrape_stream, mock_get_llm, mock_gen_summary):
        """Phase 4: Verify near-duplicate paste detection"""
        mock_gen_summary.return_value = "Synthetic summary"
        mock_get_llm.return_value = MagicMock()
        
        content1 = "api_key=sk-ORIGINAL1234567890\n" + "DATA " * 1000
        content2 = "api_key=sk-ORIGINAL1234567890\n" + "DATA " * 990 + " MODIFIED" # > 90% similar
        
        # First paste
        def side_effect1(paste_id, callback, chunk_size=1024*1024):
            callback(content1)
            return True
        mock_scrape_stream.side_effect = side_effect1
        mock_recent.return_value = [{'id': 'orig1', 'url': 'http://test.com/orig1', 'title': 'Original'}]
        
        scraper = PasteScraper([PastebinHandler()])
        watcher = Watcher(scraper)
        watcher._process_new_paste("Pastebin", mock_recent.return_value[0])
        
        # Second paste (duplicate)
        def side_effect2(paste_id, callback, chunk_size=1024*1024):
            callback(content2)
            return True
        mock_scrape_stream.side_effect = side_effect2
        mock_recent.return_value = [{'id': 'dup1', 'url': 'http://test.com/dup1', 'title': 'Duplicate'}]
        
        watcher._process_new_paste("Pastebin", mock_recent.return_value[0])
        
        # Verify two records exist, second one linked to first
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, external_id, parent_id FROM leaks ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()
        
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['external_id'], 'orig1')
        self.assertEqual(rows[1]['external_id'], 'dup1')
        self.assertEqual(rows[1]['parent_id'], rows[0]['id'])

    def test_parallel_chunk_scanner(self):
        from src.robin.paste_scraper import ParallelChunkScanner
        # Create content with keys in different chunks (using smaller chunks for speed)
        # We use 'api_key' because 'api' and 'key' are in the mega-keyword regex.
        chunk1 = "api_key=sk-1234567890abcdef1234567890abcdef\n" + "A" * 10240
        chunk2 = "B" * 10240 + "\napi_key=sk-abcdef1234567890abcdef1234567890"
        content = chunk1 + chunk2
        
        scanner = ParallelChunkScanner(chunk_size=10240, overlap=100)
        matches = scanner.scan(content)
        
        # Should find both keys
        match_values = [m.value for m in matches]
        self.assertTrue(any("1234567890abcdef" in v for v in match_values))
        self.assertTrue(any("abcdef1234567890" in v for v in match_values))

if __name__ == '__main__':
    unittest.main()
