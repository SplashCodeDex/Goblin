import unittest
import os
import sys
import json

# Add src to path
sys.path.append(os.path.join(os.getcwd(), "src"))

from robin.database import (
    initialize_database, save_autopilot_state, load_autopilot_state,
    save_scanned_hash, load_scanned_hashes
)
from robin.paste_scraper import Watcher, PasteScraper

class TestPersistence(unittest.TestCase):
    def setUp(self):
        initialize_database()

    def test_autopilot_state(self):
        save_autopilot_state("test_key", "test_value")
        val = load_autopilot_state("test_key")
        self.assertEqual(val, "test_value")
        
        # Update
        save_autopilot_state("test_key", "new_value")
        val = load_autopilot_state("test_key")
        self.assertEqual(val, "new_value")

    def test_scanned_hashes(self):
        h = "abc123hash"
        save_scanned_hash(h)
        hashes = load_scanned_hashes(limit=10)
        self.assertIn(h, hashes)

    def test_watcher_persistence(self):
        scraper = PasteScraper([])
        # First instance saves some IDs
        w1 = Watcher(scraper)
        w1._seen_ids.add("Pastebin:123")
        
        # Manually trigger the persistence logic that's normally in start()
        from robin.database import save_autopilot_state
        save_autopilot_state("watcher_seen_ids", json.dumps(list(w1._seen_ids)))
        
        # Second instance should load them
        w2 = Watcher(scraper)
        self.assertIn("Pastebin:123", w2._seen_ids)

if __name__ == "__main__":
    unittest.main()
