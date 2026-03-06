import os
from dotenv import load_dotenv

load_dotenv()

# Configuration variables loaded from the .env file
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL")
CORS_ALLOW_ORIGINS = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173")

# Tor proxy configuration
TOR_SOCKS_HOST = os.getenv("TOR_SOCKS_HOST", "127.0.0.1")
TOR_SOCKS_PORT = int(os.getenv("TOR_SOCKS_PORT", "9050"))
TOR_CONTROL_PORT = int(os.getenv("TOR_CONTROL_PORT", "9051"))
TOR_PASSWORD = os.getenv("TOR_PASSWORD", None)

# Search Engine Configuration (centralized)
SEARCH_ENGINE_ENDPOINTS = [
    # Ahmia and other engines
    "http://juhanurmihxlp77nkq76byazcldy2hlmovfu2epvl5ankdibsot4csyd.onion/search/?q={query}",
    "http://3bbad7fauom4d6sgppalyqddsqbf5u5p56b5k5uk2zxsy3d6ey2jobad.onion/search?q={query}",
    "http://darkhuntyla64h75a3re5e2l3367lqn7ltmdzpgmr6b4nbz3q2iaxrid.onion/search?q={query}",
    "http://iy3544gmoeclh5de6gez2256v6pjh4omhpqdh2wpeeppjtvqmjhkfwad.onion/torgle/?query={query}",
    "http://amnesia7u5odx5xbwtpnqk3edybgud5bmiagu75bnqx2crntw5kry7ad.onion/search?query={query}",
    "http://kaizerwfvp5gxu6cppibp7jhcqptavq3iqef66wbxenh6a2fklibdvid.onion/search?q={query}",
    "http://anima4ffe27xmakwnseih3ic2y7y3l6e7fucwk4oerdn4odf7k74tbid.onion/search?q={query}",
    "http://tornadoxn3viscgz647shlysdy7ea5zqzwda7hierekeuokh5eh5b3qd.onion/search?q={query}",
    "http://tornetupfu7gcgidt33ftnungxzyfq2pygui5qdoyss34xbgx2qruzid.onion/search?q={query}",
    "http://torlbmqwtudkorme6prgfpmsnile7ug2zm4u3ejpcncxuhpu4k2j4kyd.onion/index.php?a=search&q={query}",
    "http://findtorroveq5wdnipkaojfpqulxnkhblymc7aramjzajcvpptd4rjqd.onion/search?q={query}",
    "http://2fd6cemt4gmccflhm6imvdfvli3nf7zn6rfrwpsy7uhxrgbypvwf5fad.onion/search?query={query}",
    "http://oniwayzz74cv2puhsgx4dpjwieww4wdphsydqvf5q7eyz4myjvyw26ad.onion/search.php?s={query}",
    "http://tor66sewebgixwhcqfnp5inzp5x5uohhdy3kvtnyfxc2e5mxiuh34iid.onion/search?q={query}",
    "http://3fzh7yuupdfyjhwt3ugzqqof6ulbcl27ecev33knxe3u7goi3vfn2qqd.onion/oss/index.php?search={query}"
]

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", None)

# Scraping configuration
MAX_SCRAPE_CHARS = int(os.getenv("MAX_SCRAPE_CHARS", "1200"))
CREDENTIAL_SCRAPE_CHARS = int(os.getenv("CREDENTIAL_SCRAPE_CHARS", "50000"))

# Credential Hunting Features (toggles)
ENABLE_LIVE_VERIFICATION = os.getenv("ENABLE_LIVE_VERIFICATION", "false").lower() == "true"
ENABLE_BREACH_LOOKUP = os.getenv("ENABLE_BREACH_LOOKUP", "false").lower() == "true"
ENABLE_DB_DISCOVERY = os.getenv("ENABLE_DB_DISCOVERY", "false").lower() == "true"
ENABLE_ML_FILTERING = os.getenv("ENABLE_ML_FILTERING", "true").lower() == "true"
ENABLE_GITHUB_DORKING = os.getenv("ENABLE_GITHUB_DORKING", "false").lower() == "true"

# Breach Lookup Rate Limiting
BREACH_RATE_LIMIT_MS = int(os.getenv("BREACH_RATE_LIMIT_MS", "1000"))

# Breach Lookup API Keys
HIBP_API_KEY = os.getenv("HIBP_API_KEY", None)  # Have I Been Pwned
SNUSBASE_API_KEY = os.getenv("SNUSBASE_API_KEY", None)
DEHASHED_API_KEY = os.getenv("DEHASHED_API_KEY", None)
INTELX_API_KEY = os.getenv("INTELX_API_KEY", None)  # Intelligence X
LEAKLOOKUP_API_KEY = os.getenv("LEAKLOOKUP_API_KEY", None)
WELEAKINFO_API_KEY = os.getenv("WELEAKINFO_API_KEY", None)
SCYLLA_API_KEY = os.getenv("SCYLLA_API_KEY", None)

# Database Discovery API Keys
BINARYEDGE_API_KEY = os.getenv("BINARYEDGE_API_KEY", None)

# Credential Pattern Engine Configuration
CREDENTIAL_MIN_CONFIDENCE = os.getenv("CREDENTIAL_MIN_CONFIDENCE", "medium")  # low, medium, high
CREDENTIAL_CATEGORIES = os.getenv("CREDENTIAL_CATEGORIES", "").split(",") if os.getenv("CREDENTIAL_CATEGORIES") else None

# Default source weight distribution for search results
# These can be overridden per request via API
DEFAULT_SOURCE_WEIGHTS = {
    "darkweb": 0.40,          # 40% - Primary focus on dark web intelligence
    "github": 0.20,           # 20% - GitHub repositories
    "github_code": 0.10,      # 10% - Code snippets
    "github_commits": 0.05,   #  5% - Commit messages
    "github_dorks": 0.15,     # 15% - GitHub credential dorking
    "github_gists": 0.10,     # 10% - Public gist search
}

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
        "MAX_SCRAPE_CHARS": MAX_SCRAPE_CHARS,
        "CREDENTIAL_SCRAPE_CHARS": CREDENTIAL_SCRAPE_CHARS,
        "CORS_ALLOW_ORIGINS": CORS_ALLOW_ORIGINS,
        "DEFAULT_SOURCE_WEIGHTS": DEFAULT_SOURCE_WEIGHTS,
        # Credential Hunting Features
        "ENABLE_LIVE_VERIFICATION": ENABLE_LIVE_VERIFICATION,
        "ENABLE_BREACH_LOOKUP": ENABLE_BREACH_LOOKUP,
        "ENABLE_DB_DISCOVERY": ENABLE_DB_DISCOVERY,
        "ENABLE_ML_FILTERING": ENABLE_ML_FILTERING,
        "ENABLE_GITHUB_DORKING": ENABLE_GITHUB_DORKING,
        "BREACH_RATE_LIMIT_MS": BREACH_RATE_LIMIT_MS,
        "CREDENTIAL_MIN_CONFIDENCE": CREDENTIAL_MIN_CONFIDENCE,
        # API Keys (masked)
        "HIBP_API_KEY": _mask(HIBP_API_KEY),
        "SNUSBASE_API_KEY": _mask(SNUSBASE_API_KEY),
        "DEHASHED_API_KEY": _mask(DEHASHED_API_KEY),
        "INTELX_API_KEY": _mask(INTELX_API_KEY),
        "LEAKLOOKUP_API_KEY": _mask(LEAKLOOKUP_API_KEY),
        "WELEAKINFO_API_KEY": _mask(WELEAKINFO_API_KEY),
        "SCYLLA_API_KEY": _mask(SCYLLA_API_KEY),
        "BINARYEDGE_API_KEY": _mask(BINARYEDGE_API_KEY)
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
            "TOR_PASSWORD", "MAX_SCRAPE_CHARS", "CREDENTIAL_SCRAPE_CHARS", "CORS_ALLOW_ORIGINS",
            "ENABLE_LIVE_VERIFICATION", "ENABLE_BREACH_LOOKUP", "ENABLE_DB_DISCOVERY", "ENABLE_ML_FILTERING",
            "ENABLE_GITHUB_DORKING", "BREACH_RATE_LIMIT_MS",
            "HIBP_API_KEY", "SNUSBASE_API_KEY", "DEHASHED_API_KEY", "INTELX_API_KEY",
            "LEAKLOOKUP_API_KEY", "WELEAKINFO_API_KEY", "SCYLLA_API_KEY", "BINARYEDGE_API_KEY",
            "CREDENTIAL_MIN_CONFIDENCE", "CREDENTIAL_CATEGORIES"
        ]:
            set_key(env_file, key, str(value))
            # Update global variable in memory (rudimentary reload)
            globals()[key] = value

    # Reload dotenv to ensure os.environ is updated
    load_dotenv(override=True)
