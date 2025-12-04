
import random
import time
import socket
import re
import json
import hashlib
import os
import requests
import logging
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from .config import TOR_SOCKS_HOST, TOR_SOCKS_PORT, SEARCH_ENGINE_ENDPOINTS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def is_tor_running(host: str = TOR_SOCKS_HOST, port: int = TOR_SOCKS_PORT, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def get_tor_proxies():
    return {
        "http": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
        "https": f"socks5h://{TOR_SOCKS_HOST}:{TOR_SOCKS_PORT}",
    }


def _request_with_retries(url, headers=None, proxies=None, timeout=30, max_retries=1, base_sleep=0.5):
    last_exc = None
    for attempt in range(max_retries):
        try:
            return requests.get(url, headers=headers, proxies=proxies, timeout=timeout)
        except Exception as e:
            last_exc = e
            sleep = base_sleep * (2 ** attempt) + random.random() * 0.2
            time.sleep(sleep)
    raise last_exc

def _disk_cache_path(prefix: str, key: str) -> str:
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()
    folder = os.path.join(".cache", prefix)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{h}.json")

def _cache_get(prefix: str, key: str):
    p = _disk_cache_path(prefix, key)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None
    return None

def _cache_put(prefix: str, key: str, data):
    p = _disk_cache_path(prefix, key)
    try:
        with open(p, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def fetch_search_results(endpoint, query, request_timeout=30):
    url = endpoint.format(query=query)
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    proxies = get_tor_proxies()
    try:
        response = _request_with_retries(url, headers=headers, proxies=proxies, timeout=request_timeout)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            links = []
            for a in soup.find_all('a'):
                try:
                    href = a.get('href') or ""
                    title = a.get_text(strip=True)
                    # Normalize onion links
                    if href.startswith('//'):
                        href = 'http:' + href
                    if re.match(r'^([a-zA-Z]+:)?//', href) is None and '.onion' in href:
                        href = 'http://' + href.lstrip('/')
                    m = re.findall(r'https?:\/\/[^\s\"]*\.onion[^\s\"]*', href)
                    if m:
                        links.append({"title": title, "link": m[0]})
                except Exception as e:
                    logger.debug(f"link-parse error on {endpoint}: {e}")
                    continue
            return links
        else:
            logger.debug(f"Non-200 from {url}: {response.status_code}")
            return []
    except Exception as e:
        logger.debug(f"request error for {url}: {e}")
        return []

def _canonicalize_url(url: str) -> str:
    try:
        from urllib.parse import urlparse, urlunparse
        u = urlparse(url)
        netloc = u.hostname.lower() if u.hostname else u.netloc.lower()
        path = u.path or '/'
        # drop query/fragment for dedupe
        clean = urlunparse((u.scheme, netloc, path, '', '', ''))
        return clean
    except Exception:
        return url


def get_search_results(refined_query, max_workers=5, max_results=None, request_timeout=30, use_cache=True, load_cached_only=False):
    cache_key = json.dumps({"q": refined_query, "mw": max_workers, "to": request_timeout, "mr": max_results})
    if use_cache:
        cached = _cache_get("search", cache_key)
        if cached is not None:
            return cached
    results = []
    if not load_cached_only:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(fetch_search_results, endpoint, refined_query, request_timeout)
                       for endpoint in SEARCH_ENGINE_ENDPOINTS]
            for future in as_completed(futures):
                result_urls = future.result()
                results.extend(result_urls)
    # Deduplicate results based on canonicalized link, cap if max_results provided.
    seen_links = set()
    unique_results = []
    for res in results:
        link = res.get("link")
        canon = _canonicalize_url(link)
        if canon not in seen_links:
            seen_links.add(canon)
            # keep original title/link
            unique_results.append(res)
            if max_results and len(unique_results) >= max_results:
                break
    if use_cache:
        _cache_put("search", cache_key, unique_results)
    return unique_results
