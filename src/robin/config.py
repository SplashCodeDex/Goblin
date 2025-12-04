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
