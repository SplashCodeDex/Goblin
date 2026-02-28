
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
from urllib.parse import unquote, urlparse, urljoin, parse_qs
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


def _request_with_retries(url, headers=None, proxies=None, timeout=30, max_retries=3, base_sleep=0.6):
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


_ONION_REGEX = re.compile(r"(?:https?://)?[a-z2-7]{16,56}\.onion(?:[^\s\"<>]*)?", re.IGNORECASE)


def _clean_onion_url(url: str) -> str:
    if not url:
        return url
    # Decode percent-encoding and strip surrounding whitespace/punctuation
    url = unquote(url).strip().strip("\'\"()[]{}<>")
    # Normalize scheme and leading slashes
    if url.startswith("//"):
        url = "http://" + url.lstrip("/")
    if ".onion" in url and not (url.startswith("http://") or url.startswith("https://")):
        url = "http://" + url.lstrip("/")
    # Trim trailing punctuation commonly attached in HTML text
    while url and url[-1] in ",.;:!?)":
        url = url[:-1]
    # Normalize hostname: lowercase and strip leading www. for onion hosts
    try:
        from urllib.parse import urlparse, urlunparse
        u = urlparse(url)
        host = (u.hostname or u.netloc or "").lower()
        if host.startswith("www.") and host.endswith(".onion"):
            host = host[4:]
        if host:
            url = urlunparse((u.scheme or "http", host, u.path or "/", "", u.query, ""))
    except Exception:
        pass
    return url


def _extract_snippet_from_element(anchor_elem) -> str:
    """
    Extract a description/snippet from the context around an anchor element.

    Tries multiple strategies to find relevant snippet text:
    1. Look for common snippet class names (description, snippet, summary, excerpt)
    2. Check for <dd> tags (Torch-style dt/dd pairs)
    3. Find <p> tags in the parent container
    4. Use next sibling text
    5. Fallback to parent container text (excluding link text)

    Returns: Cleaned snippet text (max 200 chars) or empty string
    """
    snippet = ""

    try:
        # Get the parent container (div, li, article, etc.)
        parent = anchor_elem.find_parent(['div', 'li', 'article', 'section', 'dt', 'tr', 'td'])

        if not parent:
            return ""

        # Strategy 1: Look for elements with snippet-related classes
        for class_name in ['description', 'snippet', 'summary', 'excerpt', 'desc', 'abstract']:
            elem = parent.find(class_=class_name)
            if elem:
                snippet = elem.get_text(strip=True)
                if snippet:
                    break

        # Strategy 2: For dt/dd structure (Torch pattern)
        if not snippet and parent.name == 'dt':
            dd = parent.find_next_sibling('dd')
            if dd:
                snippet = dd.get_text(strip=True)

        # Strategy 3: Look for <p> tags in parent
        if not snippet:
            p_tag = parent.find('p')
            if p_tag:
                snippet = p_tag.get_text(strip=True)

        # Strategy 4: Check next sibling of anchor
        if not snippet:
            next_sibling = anchor_elem.find_next_sibling()
            if next_sibling and next_sibling.name in ['p', 'span', 'div', 'dd']:
                snippet = next_sibling.get_text(strip=True)

        # Strategy 5: Fallback - use parent text excluding link text
        if not snippet:
            parent_text = parent.get_text(separator=' ', strip=True)
            link_text = anchor_elem.get_text(strip=True)
            # Remove link text from parent text
            if link_text and link_text in parent_text:
                snippet = parent_text.replace(link_text, '', 1).strip()
            else:
                snippet = parent_text

        # Clean the snippet
        if snippet:
            # Remove URLs from snippet
            snippet = re.sub(r'https?://[^\s]+', '', snippet)
            snippet = re.sub(r'[a-z2-7]{16,56}\.onion[^\s]*', '', snippet, flags=re.IGNORECASE)
            # Remove excessive whitespace
            snippet = re.sub(r'\s+', ' ', snippet).strip()
            # Remove common noise patterns
            snippet = re.sub(r'^[\[\(\{<].*?[\]\)\}>]\s*', '', snippet)  # Remove leading brackets
            # Truncate to 200 chars
            if len(snippet) > 200:
                snippet = snippet[:200].rsplit(' ', 1)[0] + '...'

    except Exception as e:
        logger.debug(f"snippet extraction error: {e}")
        snippet = ""

    return snippet


def _extract_onions_from_soup(soup: BeautifulSoup) -> list:
    links = []
    seen = set()
    for a in soup.find_all('a'):
        try:
            title = a.get_text(strip=True) or ""
            candidates = [a.get('href') or "", a.get('data-href') or "", a.get('data-url') or "", title]
            # Also check decoded variants (redirect patterns)
            decoded = []
            for c in candidates:
                if c:
                    decoded.append(unquote(c))
            candidates.extend(decoded)
            for cand in candidates:
                if not cand:
                    continue
                for m in _ONION_REGEX.findall(cand):
                    cleaned = _clean_onion_url(m)
                    # Heuristic: if the match was found in anchor text, prefer http scheme for consistency
                    if cand == title and cleaned.startswith("https://") and ".onion" in cleaned:
                        cleaned = "http://" + cleaned[len("https://"):]
                    if cleaned and cleaned not in seen:
                        seen.add(cleaned)
                        # Extract snippet from the surrounding context
                        snippet = _extract_snippet_from_element(a)
                        links.append({
                            "title": title,
                            "link": cleaned,
                            "snippet": snippet,
                            "source": "darkweb"
                        })
        except Exception as e:
            logger.debug(f"link-parse error: {e}")
            continue
    return links


# Per-engine handler to allow custom parsing and pagination
ENGINE_HANDLERS = {}


# Example specialized handlers for known engines (pattern match by hostname substring)
# Ahmia-like: try query params for 'q' and follow pagination anchors with rel or labels

def _find_next_link_generic(soup: BeautifulSoup, current_url: str) -> str | None:
    # 1) rel=next
    rel_next = soup.find('a', attrs={'rel': 'next'})
    if rel_next and rel_next.get('href'):
        return urljoin(current_url, rel_next.get('href'))
    # 2) class contains next or pagination-next
    for a in soup.find_all('a'):
        cls = ' '.join(a.get('class', [])).lower()
        if 'next' in cls or 'pagination-next' in cls:
            href = a.get('href') or ''
            if href:
                return urljoin(current_url, href)
    # 3) text contains common labels
    for a in soup.find_all('a'):
        txt = (a.get_text(' ', strip=True) or '').lower()
        if any(k in txt for k in ['next', 'more', 'older', '>>', '>']):
            href = a.get('href') or ''
            if href:
                return urljoin(current_url, href)
    # 4) pagination containers
    pagers = soup.select('.pagination a, nav.pagination a, ul.pagination a')
    for a in pagers:
        txt = (a.get_text(' ', strip=True) or '').lower()
        if any(k in txt for k in ['next', 'older', 'more', '>']):
            href = a.get('href') or ''
            if href:
                return urljoin(current_url, href)
    return None


def _ahmia_handler(session_get, base_url, request_timeout, max_pages=2, max_per_engine=100):
    collected = []
    url = base_url
    for _ in range(max_pages):
        resp = session_get(url, timeout=request_timeout)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        collected.extend(_extract_onions_from_soup(soup))
        if len(collected) >= max_per_engine:
            break
        # Prefer rel="next" or class/text hints
        next_link = _find_next_link_generic(soup, url)
        if not next_link:
            break
        url = next_link
    # Dedup and cap
    dedup = []
    seen = set()
    for item in collected:
        canon = _canonicalize_url(item["link"])
        if canon not in seen:
            seen.add(canon)
            dedup.append(item)
            if len(dedup) >= max_per_engine:
                break
    return dedup

# Register simple patterns for engines we know by onion hostname fragments
# (deferred until after function definitions)



def _register_engine_handler(pattern, handler):
    ENGINE_HANDLERS[pattern] = handler


def _match_engine_handler(endpoint: str):
    for pat, handler in ENGINE_HANDLERS.items():
        if pat in endpoint:
            return handler
    return None


def _find_next_link(soup: BeautifulSoup, current_url: str) -> str | None:
    # 1) rel="next"
    rel_next = soup.find('a', attrs={'rel': 'next'})
    if rel_next and rel_next.get('href'):
        return urljoin(current_url, rel_next.get('href'))
    # 2) class hints
    for a in soup.find_all('a'):
        classes = (a.get('class') or [])
        if any('next' in c.lower() for c in classes):
            href = a.get('href')
            if href:
                return urljoin(current_url, href)
    # 3) text hints
    for a in soup.find_all('a'):
        txt = (a.get_text(' ', strip=True) or '').lower()
        if any(token in txt for token in ['next', 'more', 'older', '>>', '›', '»']):
            href = a.get('href')
            if href:
                return urljoin(current_url, href)
    # 4) query param increment (page/start/offset)
    try:
        parsed = urlparse(current_url)
        qs = parse_qs(parsed.query)
        for key in ['page', 'p', 'start', 'offset']:
            if key in qs and qs[key]:
                try:
                    cur = int(qs[key][0])
                    qs[key] = [str(cur + 1 if key in ['page', 'p'] else cur + 10)]
                    new_query = '&'.join([f"{k}={v[0]}" for k, v in qs.items()])
                    return parsed._replace(query=new_query).geturl()
                except Exception:
                    continue
    except Exception:
        pass
    return None


def _generic_engine_handler(session_get, base_url, request_timeout, max_pages=1, max_per_engine=100):
    collected = []
    url = base_url
    for _ in range(max_pages):
        resp = session_get(url, timeout=request_timeout)
        if resp.status_code != 200:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        collected.extend(_extract_onions_from_soup(soup))
        if len(collected) >= max_per_engine:
            break
        next_link = _find_next_link_generic(soup, url)
        if not next_link:
            break
        url = next_link
    # cap
    dedup = []
    seen = set()
    for item in collected:
        canon = _canonicalize_url(item["link"])
        if canon not in seen:
            seen.add(canon)
            dedup.append(item)
            if len(dedup) >= max_per_engine:
                break
    return dedup


# Perform final registration now that helpers exist
try:
   _register_engine_handler("juhanurmi", _ahmia_handler)
   _register_engine_handler("ahmia", _ahmia_handler)
except NameError:
   pass


def fetch_search_results(endpoint, query, request_timeout=30, max_per_engine=100):
    url = endpoint.format(query=query)
    headers = {
        "User-Agent": random.choice(USER_AGENTS)
    }
    proxies = get_tor_proxies()
    try:
        # Wrap requests.get to inject headers/proxies
        def session_get(u, timeout):
            return _request_with_retries(u, headers=headers, proxies=proxies, timeout=timeout)
        handler = _match_engine_handler(endpoint) or _generic_engine_handler
        return handler(session_get, url, request_timeout, max_pages=3, max_per_engine=max_per_engine)
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
        # Order endpoints by health score (desc) with slight jitter to avoid starvation
        endpoints = list(SEARCH_ENGINE_ENDPOINTS)
        # Lazy-import engine health helpers (defined above but safe to use)
        try:
            health = {e: _ENGINE_HEALTH.get(e, 0) for e in endpoints}
        except NameError:
            health = {e: 0 for e in endpoints}
        endpoints.sort(key=lambda e: (health.get(e, 0) + random.random() * 0.1), reverse=True)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_endpoint = {
                executor.submit(fetch_search_results, endpoint, refined_query, request_timeout): endpoint
                for endpoint in endpoints
            }
            for future in as_completed(future_to_endpoint):
                endpoint = future_to_endpoint[future]
                try:
                    result_urls = future.result()
                except Exception as e:
                    logger.debug(f"engine error {endpoint}: {e}")
                    result_urls = []
                results.extend(result_urls)
                # Update simple health score (+1 on non-empty results, -0.5 otherwise, clamp [-5, 5])
                try:
                    score = _ENGINE_HEALTH.get(endpoint, 0.0)
                    if result_urls:
                        score += 1.0
                    else:
                        score -= 0.5
                    score = max(-5.0, min(5.0, score))
                    _ENGINE_HEALTH[endpoint] = score
                except NameError:
                    pass
        try:
            _save_engine_health(_ENGINE_HEALTH)
        except NameError:
            pass
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


def stream_search_results(refined_query, max_workers=5, max_results=None, request_timeout=30):
    """
    Generator version of get_search_results that yields unique results as they are found.
    """
    seen_links = set()
    results_count = 0

    endpoints = list(SEARCH_ENGINE_ENDPOINTS)
    # Use health scores if available
    try:
        health = {e: _ENGINE_HEALTH.get(e, 0) for e in endpoints}
    except NameError:
        health = {e: 0 for e in endpoints}

    endpoints.sort(key=lambda e: (health.get(e, 0) + random.random() * 0.1), reverse=True)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_endpoint = {
            executor.submit(fetch_search_results, endpoint, refined_query, request_timeout): endpoint
            for endpoint in endpoints
        }
        for future in as_completed(future_to_endpoint):
            endpoint = future_to_endpoint[future]
            try:
                result_urls = future.result()
                engine_yielded = 0
                for res in result_urls:
                    link = res.get("link")
                    canon = _canonicalize_url(link)
                    if canon not in seen_links:
                        seen_links.add(canon)
                        results_count += 1
                        engine_yielded += 1
                        yield res
                        if max_results and results_count >= max_results:
                            return

                # Update health score
                try:
                    score = _ENGINE_HEALTH.get(endpoint, 0.0)
                    if engine_yielded > 0:
                        score += 1.0
                    else:
                        score -= 0.5
                    score = max(-5.0, min(5.0, score))
                    _ENGINE_HEALTH[endpoint] = score
                except NameError:
                    pass
            except Exception as e:
                logger.debug(f"engine error {endpoint}: {e}")

    try:
        _save_engine_health(_ENGINE_HEALTH)
    except NameError:
        pass
