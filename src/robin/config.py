import os
from dotenv import load_dotenv

load_dotenv()

# Configuration variables loaded from the .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")

# Tor proxy configuration
TOR_SOCKS_HOST = os.getenv("TOR_SOCKS_HOST", "127.0.0.1")
TOR_SOCKS_PORT = int(os.getenv("TOR_SOCKS_PORT", "9050"))
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
TOR_PASSWORD = os.getenv("TOR_PASSWORD", None)

# Search Engine Configuration
SEARCH_ENGINE_ENDPOINTS = [
    "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={query}",
    "http://haystak5njsmn2hqkewiiqjvdx7dj4773755fqnrxcn33x63kkyjqnqd.onion/?q={query}",
    "http://torchdeedp3i2j47.onion/search?q={query}",
    "http://xmh57jrzrnw6insl.onion/4a1f6b371c/search.cgi?s={query}"
]

# Scraping configuration
MAX_SCRAPE_CHARS = int(os.getenv("MAX_SCRAPE_CHARS", "1200"))
