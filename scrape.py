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

def scrape_single(url_data, rotate=False, rotate_interval=5, control_port=9051, control_password=None, request_timeout=30, translate_non_english=True, offline_only=False):
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
    meta = {"url": url, "used_tor": use_tor, "status": None, "content_type": None, "language": None, "translated": False, "blocked": False, "from_cache": False}
    try:
        # simple retry/backoff
        last_exc = None
        response = None
        for attempt in range(4):
            try:
                response = requests.get(url, headers=headers, proxies=proxies, timeout=request_timeout, stream=True)
                break
            except Exception as e:
                last_exc = e
                time.sleep(0.7 * (2 ** attempt) + random.random() * 0.3)
        else:
            raise last_exc

        meta["status"] = getattr(response, 'status_code', None)
        ctype = response.headers.get('Content-Type', '') if response is not None else ''
        meta["content_type"] = ctype
        text_content = ""
        if response is not None and response.status_code == 200:
            if 'application/pdf' in ctype or url.lower().endswith('.pdf'):
                # PDF extraction
                try:
                    import io, pdfplumber
                    file_bytes = response.content
                    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                        pages = [p.extract_text() or '' for p in pdf.pages]
                        text_content = "\n".join(pages)
                except Exception as _:
                    text_content = ""
            elif any(ext in ctype for ext in ['image/', 'application/octet-stream']) or any(url.lower().endswith(ext) for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff']):
                # OCR for images
                try:
                    from PIL import Image
                    import io, pytesseract
                    img = Image.open(io.BytesIO(response.content))
                    text_content = pytesseract.image_to_string(img)
                except Exception:
                    text_content = ""
            else:
                # HTML/text
                response.encoding = response.apparent_encoding or response.encoding
                soup = BeautifulSoup(response.text, "html.parser")
                text_content = soup.get_text(" ").replace('\n', ' ').replace('\r', '')
                # CAPTCHA/anti-bot heuristics
                low = text_content.lower()
                if any(k in low for k in ["captcha", "are you a robot", "unusual traffic", "cloudflare", "access denied"]):
                    meta["blocked"] = True
        scraped_text = (url_data['title'] + " " + text_content).strip() if text_content else url_data['title']

        # Language detection and optional translation
        if scraped_text and translate_non_english:
            try:
                from langdetect import detect
                lang = detect(scraped_text[:2000])
                meta["language"] = lang
                if lang != 'en':
                    from googletrans import Translator
                    tr = Translator()
                    translated = tr.translate(scraped_text, dest='en')
                    scraped_text = translated.text
                    meta["translated"] = True
            except Exception:
                pass
    except Exception as e:
        logger.debug(f"scrape error for {url}: {e}")
        scraped_text = url_data['title']

    return url, scraped_text, meta

def scrape_multiple(urls_data, max_workers=5, request_timeout=30, use_cache=True, load_cached_only=False, translate_non_english=True):
    """
    Scrapes multiple URLs concurrently using a thread pool.
    
    Parameters:
      - urls_data: list of URLs to scrape.
      - max_workers: number of concurrent threads for scraping.
    
    Returns:
      A dictionary mapping each URL to its scraped content.
    """
    results = {}
    meta = {}
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
                    if not load_cached_only:
                        to_fetch.append(url_data)
            else:
                if not load_cached_only:
                    to_fetch.append(url_data)
    else:
        to_fetch = list(urls_data)

    if to_fetch:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(scrape_single, url_data, False, 5, 9051, None, request_timeout, translate_non_english): url_data
                for url_data in to_fetch
            }
            for future in as_completed(future_to_url):
                url, content, m = future.result()
                if len(content) > max_chars:
                    content = content[:max_chars]
                results[url] = content
                meta[url] = m
                if use_cache:
                    try:
                        with open(_cache_path(url), "w", encoding="utf-8") as f:
                            json.dump(content, f, ensure_ascii=False)
                    except Exception:
                        pass

    # merge cached
    for url, content in cached.items():
        results[url] = content
        meta[url] = {"url": url, "from_cache": True}

    return results, meta