import os
import sys
import unittest
import requests
import time
import subprocess
from datetime import datetime

# Add src to path so we can import robin directly in this script if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

# We can now import from robin, but for integration tests we mostly use subprocesses
# to ensure the CLI/module execution works as expected.

class TestIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("Testing database initialization...")
        # Ensure data directory exists
        os.makedirs("data", exist_ok=True)

        # Prepare environment with PYTHONPATH set to src
        cls.env = os.environ.copy()
        cls.env["PYTHONPATH"] = os.path.abspath("src")

        # Initialize database directly using the module
        # This should create data/robin.db because of our change in database.py
        subprocess.run([sys.executable, "-m", "robin.database"], check=True, env=cls.env)

        # Start API server in background
        print("Starting API server...")
        cls.api_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "robin.api.server:app", "--port", "8000"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=cls.env
        )
        time.sleep(5) # Wait for server to start

    @classmethod
    def tearDownClass(cls):
        print("Stopping API server...")
        cls.api_process.terminate()
        cls.api_process.wait()

    def test_health_check(self):
        print("Testing API endpoints...")
        try:
            response = requests.get("http://localhost:8000/api/health")
            self.assertEqual(response.status_code, 200)
            print("Health check passed.")
        except requests.exceptions.ConnectionError:
            self.fail("Could not connect to API server")

    def test_schedule_flow(self):
        # 1. Create a scheduled query
        payload = {
            "name": "Integration Test Query",
            "query_text": "test query",
            "schedule": "0 * * * *",
            "search_engines": ["google"]
        }
        response = requests.post("http://localhost:8000/api/schedule", json=payload)
        self.assertEqual(response.status_code, 200)
        print("Schedule query passed.")

        # 2. Verify it exists
        response = requests.get("http://localhost:8000/api/scheduled_queries")
        self.assertEqual(response.status_code, 200)
        queries = response.json()["queries"]
        self.assertTrue(any(q["name"] == "Integration Test Query" for q in queries))
        print("Get scheduled queries passed.")

        # 3. Delete it
        query_id = next(q["id"] for q in queries if q["name"] == "Integration Test Query")
        response = requests.delete(f"http://localhost:8000/api/schedule/{query_id}")
        self.assertEqual(response.status_code, 200)
        print("Delete scheduled query passed.")

if __name__ == "__main__":
    unittest.main()
