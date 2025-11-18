import random, time, logging
import requests
import threading
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from config import MAX_SCRAPE_CHARS

import warnings
warnings.filterwarnings("ignore")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define a list of rotating user agents.
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.7; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (X11; Linux i686; rv:137.0) Gecko/20100101 Firefox/137.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_7_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.3 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.3179.54",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 Edg/135.0.3179.54"
]

# Global counter and lock for thread-safe Tor rotation
request_counter = 0
counter_lock = threading.Lock()

def scrape_single(url_data, rotate=False, rotate_interval=5, control_port=9051, control_password=None, request_timeout=30):
    """
    Scrapes a single URL.
    If the URL is an onion site, routes the request through Tor.
    Returns a tuple (url, scraped_text).
    """
    url = url_data['link']
    use_tor = ".onion" in url
    proxies = None
    if use_tor:
        try:
            from search import get_tor_proxies
            proxies = get_tor_proxies()
        except Exception:
            proxies = {
                "http": "socks5h://127.0.0.1:9050",
                "https": "socks5h://127.0.0.1:9050"
            }
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    try:
        # simple retry/backoff
        last_exc = None
        for attempt in range(3):
            try:
                response = requests.get(url, headers=headers, proxies=proxies, timeout=request_timeout)
                break
            except Exception as e:
                last_exc = e
                time.sleep(0.5 * (2 ** attempt) + random.random() * 0.2)
        else:
            raise last_exc

        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            scraped_text = url_data['title'] + " " + soup.get_text().replace('\n', ' ').replace('\r', '')
        else:
            scraped_text = url_data['title']
    except Exception as e:
        logger.debug(f"scrape error for {url}: {e}")
        scraped_text = url_data['title']

    return url, scraped_text

def scrape_multiple(urls_data, max_workers=5, request_timeout=30, use_cache=True):
    """
    Scrapes multiple URLs concurrently using a thread pool.
    
    Parameters:
      - urls_data: list of URLs to scrape.
      - max_workers: number of concurrent threads for scraping.
    
    Returns:
      A dictionary mapping each URL to its scraped content.
    """
    results = {}
    max_chars = MAX_SCRAPE_CHARS  # Taking first n chars from the scraped data
    # simple disk cache for scraped pages
    import os, json, hashlib
    def _cache_path(url: str):
        h = hashlib.sha256(url.encode("utf-8")).hexdigest()
        folder = os.path.join(".cache", "scrape")
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, f"{h}.json")

    cached = {}
    to_fetch = []
    if use_cache:
        for url_data in urls_data:
            p = _cache_path(url_data['link'])
            if os.path.exists(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        cached[url_data['link']] = json.load(f)
                except Exception:
                    to_fetch.append(url_data)
            else:
                to_fetch.append(url_data)
    else:
        to_fetch = list(urls_data)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {
            executor.submit(scrape_single, url_data, False, 5, 9051, None, request_timeout): url_data
            for url_data in to_fetch
        }
        for future in as_completed(future_to_url):
            url, content = future.result()
            if len(content) > max_chars:
                content = content[:max_chars]
            results[url] = content
            if use_cache:
                try:
                    with open(_cache_path(url), "w", encoding="utf-8") as f:
                        json.dump(content, f, ensure_ascii=False)
                except Exception:
                    pass
    # merge cached
    results.update(cached)
    return results