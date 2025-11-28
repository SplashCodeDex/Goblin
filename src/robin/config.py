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

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", None)

# Scraping configuration
MAX_SCRAPE_CHARS = int(os.getenv("MAX_SCRAPE_CHARS", "1200"))

def get_config():
    """Returns the current configuration, masking sensitive values."""
    return {
        "OPENAI_API_KEY": _mask(OPENAI_API_KEY),
        "GOOGLE_API_KEY": _mask(GOOGLE_API_KEY),
        "ANTHROPIC_API_KEY": _mask(ANTHROPIC_API_KEY),
        "OLLAMA_BASE_URL": OLLAMA_BASE_URL,
        "GITHUB_TOKEN": _mask(GITHUB_TOKEN),
        "TOR_SOCKS_HOST": TOR_SOCKS_HOST,
        "TOR_SOCKS_PORT": TOR_SOCKS_PORT,
        "TOR_CONTROL_PORT": TOR_CONTROL_PORT,
        "TOR_PASSWORD": _mask(TOR_PASSWORD),
        "MAX_SCRAPE_CHARS": MAX_SCRAPE_CHARS
    }

def _mask(value):
    if not value: return ""
    if len(value) < 8: return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]

def update_config(updates):
    """Updates the .env file with new values."""
    from dotenv import set_key
    env_file = ".env"
    if not os.path.exists(env_file):
        open(env_file, 'a').close()

    for key, value in updates.items():
        # Only update known keys for security
        if key in [
            "OPENAI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OLLAMA_BASE_URL",
            "GITHUB_TOKEN", "TOR_SOCKS_HOST", "TOR_SOCKS_PORT", "TOR_CONTROL_PORT",
            "TOR_PASSWORD", "MAX_SCRAPE_CHARS"
        ]:
            set_key(env_file, key, str(value))
            # Update global variable in memory (rudimentary reload)
            globals()[key] = value

    # Reload dotenv to ensure os.environ is updated
    load_dotenv(override=True)
