import logging
import random
import time
import re
import gzip
import os
import psutil
import json
import sqlite3
from datetime import datetime, UTC
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

from .scrape import get_tor_session, USER_AGENTS
from .dedup import ContentHasher
from .database import get_db_connection, check_for_near_duplicates
from .blob_store import BlobStore
from .credential_patterns import scan_text
from .llm import get_llm, generate_summary
from .config import DEFAULT_MODEL

logger = logging.getLogger(__name__)

class PasteSource(ABC):
    """
    Abstract base class for all paste site handlers.
    Each handler must implement site-specific scraping logic.
    """
    def __init__(self, name: str, base_url: str, is_onion: bool = False):
        self.name = name
        self.base_url = base_url
        self.is_onion = is_onion
        self.session = get_tor_session() if is_onion else None
        self.use_browser = False # Flag to force browser mode for next request

    @abstractmethod
    def get_recent(self) -> List[Dict[str, Any]]:
        """
        Polls the 'Recent' or 'Latest' feed of the site.
        Returns a list of metadata dictionaries: [{'id': ..., 'url': ..., 'title': ...}]
        """
        pass

    @abstractmethod
    def scrape_paste(self, paste_id: str) -> Optional[str]:
        """
        Scrapes the raw content of a specific paste by its ID or relative URL.
        """
        pass

    def scrape_paste_stream(self, paste_id: str, chunk_callback, chunk_size: int = 1024 * 1024) -> bool:
        """
        Streams the raw content of a specific paste and calls chunk_callback for each chunk.
        Default implementation uses _get_request_stream.
        """
        url = f"{self.base_url}/raw/{paste_id}"
        if self.name == "Pastebin": # Special case for Pastebin raw URL
             url = f"{self.base_url}/raw/{paste_id}"
        
        resp = self._get_request_stream(url)
        if not resp or resp.status_code != 200:
            return False
            
        try:
            for chunk in resp.iter_content(chunk_size=chunk_size):
                if chunk:
                    chunk_callback(chunk.decode('utf-8', errors='ignore'))
            return True
        except Exception as e:
            logger.error(f"Streaming failed for {paste_id}: {e}")
            return False

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches the site for a specific query.
        Default implementation uses Google Dorking via site: parameter.
        """
        # Note: Many paste sites block internal search or don't have one.
        # We can leverage search.py logic or site-specific search URLs.
        return []

    def _get_request_adaptive(self, url: str, wait_for_selector: Optional[str] = None, timeout: int = 30) -> Optional[str]:
        """
        Adaptive requester: uses high-speed requests by default, switches to UC browser on block.
        """
        from .browser_engine import browser_manager
        from .scrape import force_rotate_identity

        if self.use_browser:
            logger.info(f"[{self.name}] browser mode active. Using UC for {url}")
            return browser_manager.scrape_url(url, wait_for_selector=wait_for_selector, timeout=timeout)

        # 1. Try standard request
        headers = {"User-Agent": random.choice(USER_AGENTS)}
        try:
            if self.is_onion:
                resp = self.session.get(url, headers=headers, timeout=timeout)
            else:
                import requests
                resp = requests.get(url, headers=headers, timeout=timeout)
            
            # Check for blocks
            if resp.status_code == 403 or resp.status_code == 429 or "cloudflare" in resp.text.lower():
                logger.warning(f"[{self.name}] Block detected (Status {resp.status_code}). Triggering rotation and browser fallback.")
                force_rotate_identity()
                self.use_browser = True
                return browser_manager.scrape_url(url, wait_for_selector=wait_for_selector, timeout=timeout)
            
            return resp.text if resp.status_code == 200 else None
        except Exception as e:
            logger.error(f"[{self.name}] Request failed: {e}. Falling back to browser.")
            self.use_browser = True
            return browser_manager.scrape_url(url, wait_for_selector=wait_for_selector, timeout=timeout)

    def _get_request(self, url: str, headers: Optional[Dict] = None, timeout: int = 30):
        """
        Internal helper for making GET requests with appropriate routing.
        """
        if headers is None:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        try:
            if self.is_onion:
                return self.session.get(url, headers=headers, timeout=timeout)
            else:
                import requests
                return requests.get(url, headers=headers, timeout=timeout)
        except Exception as e:
            logger.error(f"[{self.name}] Request failed for {url}: {e}")
            return None

    def _get_request_stream(self, url: str, headers: Optional[Dict] = None, timeout: int = 60):
        """
        Internal helper for making streaming GET requests.
        Returns a requests.Response object with stream=True.
        """
        if headers is None:
            headers = {"User-Agent": random.choice(USER_AGENTS)}
        
        try:
            if self.is_onion:
                return self.session.get(url, headers=headers, timeout=timeout, stream=True)
            else:
                import requests
                return requests.get(url, headers=headers, timeout=timeout, stream=True)
        except Exception as e:
            logger.error(f"[{self.name}] Stream request failed for {url}: {e}")
            return None

class PastebinHandler(PasteSource):
    """
    Handler for Pastebin.com.
    """
    def __init__(self):
        super().__init__("Pastebin", "https://pastebin.com")

    def get_recent(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/archive"
        # Use adaptive to handle Cloudflare on archive page
        text = self._get_request_adaptive(url, wait_for_selector="table.maintable")
        if not text:
            return []
        
        soup = BeautifulSoup(text, "html.parser")
        table = soup.find("table", class_="maintable")
        if not table:
            return []
        
        pastes = []
        for row in table.find_all("tr")[1:]: # Skip header
            cols = row.find_all("td")
            if len(cols) > 0:
                link_elem = cols[0].find("a")
                if link_elem:
                    href = link_elem.get("href")
                    paste_id = href.lstrip("/")
                    pastes.append({
                        "id": paste_id,
                        "url": f"{self.base_url}{href}",
                        "title": link_elem.get_text(strip=True),
                        "meta": {
                            "author": cols[2].get_text(strip=True) if len(cols) > 2 else None,
                            "syntax": cols[3].get_text(strip=True) if len(cols) > 3 else None
                        }
                    })
        return pastes

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        # Try raw first (fastest)
        url = f"{self.base_url}/raw/{paste_id}"
        content = self._get_request_adaptive(url)
        return content

class PasteeeHandler(PasteSource):
    """
    Handler for Paste.ee.
    """
    def __init__(self):
        super().__init__("Paste.ee", "https://paste.ee")

    def get_recent(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/public"
        resp = self._get_request(url)
        if not resp or resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        pastes = []
        # Find the main container for public pastes
        container = soup.find("div", class_="col-md-9")
        if not container:
            return []
            
        for row in container.find_all("div", class_="row")[1:]: # Skip generic info
            link_elem = row.find("a")
            if link_elem and "/p/" in link_elem.get("href", ""):
                href = link_elem.get("href")
                paste_id = href.split("/")[-1]
                pastes.append({
                    "id": paste_id,
                    "url": f"{self.base_url}{href}",
                    "title": link_elem.get_text(strip=True),
                    "meta": {}
                })
        return pastes

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        url = f"{self.base_url}/r/{paste_id}"
        resp = self._get_request(url)
        return resp.text if resp and resp.status_code == 200 else None

class ControlCHandler(PasteSource):
    """
    Handler for ControlC.com.
    """
    def __init__(self):
        super().__init__("ControlC", "https://controlc.com")

    def get_recent(self) -> List[Dict[str, Any]]:
        # ControlC doesn't have a simple public archive, but it's used for targeted search.
        # For now, we return empty list for 'recent' but implement scrape_paste.
        return []

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        url = f"{self.base_url}/{paste_id}"
        text = self._get_request_adaptive(url, wait_for_selector="#paste_content")
        if not text:
            return None
        
        soup = BeautifulSoup(text, "html.parser")
        content_box = soup.find("div", id="paste_content")
        return content_box.get_text() if content_box else None

class JustPasteItHandler(PasteSource):
    """
    Handler for JustPaste.it.
    """
    def __init__(self):
        super().__init__("JustPasteIt", "https://justpaste.it")

    def get_recent(self) -> List[Dict[str, Any]]:
        # JustPaste.it often hides public lists, but we can scrape the search results.
        return []

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        url = f"{self.base_url}/{paste_id}"
        text = self._get_request_adaptive(url, wait_for_selector="article.content")
        if not text:
            return None
        
        soup = BeautifulSoup(text, "html.parser")
        # JustPaste.it uses a specific content class
        article = soup.find("article", class_="content")
        return article.get_text(separator="\n") if article else None

class RentryHandler(PasteSource):
    """
    Handler for Rentry.co.
    """
    def __init__(self):
        super().__init__("Rentry", "https://rentry.co")

    def get_recent(self) -> List[Dict[str, Any]]:
        # Rentry doesn't have a public 'latest' page by default.
        return []

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        # Rentry raw URL is /raw/id
        url = f"{self.base_url}/raw/{paste_id}"
        resp = self._get_request(url)
        return resp.text if resp and resp.status_code == 200 else None

class DumpToHandler(PasteSource):
    """
    Handler for Dump.to.
    """
    def __init__(self):
        super().__init__("DumpTo", "https://dump.to")

    def get_recent(self) -> List[Dict[str, Any]]:
        # Dump.to archive/latest page
        url = f"{self.base_url}/latest"
        resp = self._get_request(url)
        if not resp or resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        pastes = []
        # Parsing logic for dump.to table/list
        container = soup.find("div", class_="list-group")
        if container:
            for a in container.find_all("a", class_="list-group-item"):
                href = a.get("href")
                paste_id = href.lstrip("/")
                pastes.append({
                    "id": paste_id,
                    "url": f"{self.base_url}{href}",
                    "title": a.get_text(strip=True),
                    "meta": {}
                })
        return pastes

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        url = f"{self.base_url}/raw/{paste_id}"
        resp = self._get_request(url)
        return resp.text if resp and resp.status_code == 200 else None

class DeepPasteHandler(PasteSource):
    """
    Handler for DeepPaste (.onion).
    """
    def __init__(self):
        # Placeholder for DeepPaste onion address
        super().__init__("DeepPaste", "http://depastevgu4p6fiv.onion", is_onion=True)

    def get_recent(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/archive"
        resp = self._get_request(url)
        if not resp or resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        pastes = []
        # Typical onion paste site structure (simple tables)
        for a in soup.find_all("a"):
            href = a.get("href", "")
            if "show.php?id=" in href or "/view/" in href:
                paste_id = href.split("=")[-1] if "=" in href else href.split("/")[-1]
                pastes.append({
                    "id": paste_id,
                    "url": f"{self.base_url}/{href.lstrip('/')}",
                    "title": a.get_text(strip=True),
                    "meta": {}
                })
        return pastes

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        url = f"{self.base_url}/raw.php?id={paste_id}"
        resp = self._get_request(url)
        return resp.text if resp and resp.status_code == 200 else None

class StrongholdHandler(PasteSource):
    """
    Handler for Stronghold Paste (.onion).
    """
    def __init__(self):
        super().__init__("Stronghold", "http://strngpst775v3v76.onion", is_onion=True)

    def get_recent(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/latest"
        resp = self._get_request(url)
        if not resp or resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
        pastes = []
        for a in soup.find_all("a"):
            if "/paste/" in a.get("href", ""):
                href = a.get("href")
                paste_id = href.split("/")[-1]
                pastes.append({
                    "id": paste_id,
                    "url": f"{self.base_url}{href}",
                    "title": a.get_text(strip=True),
                    "meta": {}
                })
        return pastes

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        url = f"{self.base_url}/raw/{paste_id}"
        resp = self._get_request(url)
        return resp.text if resp and resp.status_code == 200 else None

class TelegramHandler(PasteSource):
    """
    Handler for Telegram Log Channels.
    Requires API_ID and API_HASH.
    """
    def __init__(self, session_name: str = 'robin_telegram'):
        super().__init__("TelegramLogs", "https://t.me")
        from .config import TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_PHONE
        self.api_id = TELEGRAM_API_ID
        self.api_hash = TELEGRAM_API_HASH
        self.phone = TELEGRAM_PHONE
        self.session_name = session_name
        self.client = None
        self._callback = None

    def get_recent(self) -> List[Dict[str, Any]]:
        # Telegram monitoring is event-driven via Telethon, 
        # so we don't use the polling get_recent.
        return []

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        return None

    async def start_monitoring(self, channel_ids: List[str], callback):
        """
        Asynchronous monitoring of specific channels.
        :param callback: Function to call when a new message is received. 
                         Signature: callback(source_name, paste_meta)
        """
        if not self.api_id or not self.api_hash:
            logger.warning("Telegram API credentials missing. Skipping monitor.")
            return

        from telethon import TelegramClient, events
        
        # Use a persistent session file in .cache
        session_path = os.path.join(".cache", self.session_name)
        os.makedirs(".cache", exist_ok=True)
        
        self.client = TelegramClient(session_path, self.api_id, self.api_hash)
        self._callback = callback
        
        @self.client.on(events.NewMessage(chats=channel_ids))
        async def handler(event):
            try:
                # Extract content and create metadata
                content = event.message.text
                if not content: return
                
                chat = await event.get_chat()
                chat_title = getattr(chat, 'title', str(event.chat_id))
                
                paste_meta = {
                    "id": str(event.id),
                    "url": f"https://t.me/c/{event.chat_id}/{event.id}",
                    "title": f"Msg from {chat_title}",
                    "content": content,
                    "meta": {
                        "author": str(event.sender_id),
                        "chat_id": str(event.chat_id)
                    }
                }
                
                logger.info(f"New Telegram message from {chat_title} (ID: {event.id})")
                if self._callback:
                    # Telegram messages are handled as 'findings' directly if content is included
                    self._callback(self.name, paste_meta)
            except Exception as e:
                logger.error(f"Error handling Telegram message: {e}")

        logger.info(f"Starting Telegram monitor for {len(channel_ids)} channels...")
        await self.client.start(phone=self.phone)
        await self.client.run_until_disconnected()

    def stop(self):
        if self.client:
            self.client.disconnect()

class PasteScraper:
    """
    Coordinator class for managing multiple PasteSource handlers.
    """
    def __init__(self, sources: List[PasteSource] = None):
        self.sources = sources or []

    def add_source(self, source: PasteSource):
        self.sources.append(source)

    def monitor_all_recent(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Triggers get_recent() on all registered sources.
        """
        results = {}
        for source in self.sources:
            try:
                logger.info(f"Polling recent pastes from {source.name}...")
                results[source.name] = source.get_recent()
            except Exception as e:
                logger.error(f"Error polling {source.name}: {e}")
                results[source.name] = []
        return results

    def search_all(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches all sources for a query.
        """
        all_results = []
        for source in self.sources:
            try:
                logger.info(f"Searching {source.name} for '{query}'...")
                res = source.search(query)
                for r in res:
                    r["source_name"] = source.name
                all_results.extend(res)
            except Exception as e:
                logger.error(f"Search error for {source.name}: {e}")
        return all_results

class Watcher:
    """
    Background monitoring engine that continuously polls paste sources.
    """
    def __init__(self, scraper: PasteScraper, poll_interval: int = 300):
        self.scraper = scraper
        self.poll_interval = poll_interval
        self.running = False

        # Load seen IDs from database
        from .database import load_autopilot_state
        saved_ids = load_autopilot_state("watcher_seen_ids")
        try:
            self._seen_ids = set(json.loads(saved_ids)) if saved_ids else set()
        except Exception as e:
            logger.warning(f"Failed to load watcher_seen_ids: {e}")
            self._seen_ids = set()

    def start(self):
        """
        Starts the monitoring loop.
        """
        self.running = True
        logger.info(f"Watcher started. Polling interval: {self.poll_interval}s")

        from .database import save_autopilot_state

        try:
            while self.running:
                all_recent = self.scraper.monitor_all_recent()
                new_found = False
                for source_name, pastes in all_recent.items():
                    for paste in pastes:
                        p_id = f"{source_name}:{paste['id']}"
                        if p_id not in self._seen_ids:
                            self._seen_ids.add(p_id)
                            self._process_new_paste(source_name, paste)
                            new_found = True

                if new_found:
                    # Persist seen IDs (keep last 5000 to avoid DB bloat)
                    ids_list = list(self._seen_ids)[-5000:]
                    save_autopilot_state("watcher_seen_ids", json.dumps(ids_list))

                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            self.stop()
    def stop(self):
        """
        Stops the monitoring loop.
        """
        self.running = False
        logger.info("Watcher stopped.")

    def _process_new_paste(self, source_name: str, paste_meta: Dict[str, Any]):
        """
        Scrapes, analyzes, and saves a newly discovered paste.
        Updated with SimHash deduplication and Big Data streaming support.
        """
        source = next((s for s in self.scraper.sources if s.name == source_name), None)
        if not source:
            return

        logger.info(f"New paste discovered on {source_name}: {paste_meta['id']}")
        
        process = psutil.Process(os.getpid())
        
        full_content = ""
        storage_content = ""
        c_hash = None
        
        # Temporary buffer for chunked processing
        total_size = 0
        is_large = False
        blob_writer = None
        temp_blob_path = None

        def chunk_handler(chunk_text):
            nonlocal full_content, total_size, is_large, blob_writer, temp_blob_path
            total_size += len(chunk_text)
            
            # Memory Monitor: If RSS > 150MB, force immediate blob storage
            mem_usage = process.memory_info().rss / (1024 * 1024)
            if mem_usage > 150:
                logger.warning(f"High memory usage detected ({mem_usage:.2f}MB). Forcing stream to blob.")
                is_large = True

            if total_size > 50 * 1024: # 50KB threshold
                is_large = True

            if is_large:
                if not blob_writer:
                    logger.info(f"Streaming large paste {paste_meta['id']} to blob storage.")
                    temp_blob_path = BlobStore.save_blob(paste_meta['id'], source_name, "")
                    blob_writer = gzip.open(temp_blob_path, 'at', encoding='utf-8')
                    if full_content:
                        blob_writer.write(full_content)
                        full_content = ""
                
                blob_writer.write(chunk_text)
            else:
                full_content += chunk_text

        # Start streaming
        success = source.scrape_paste_stream(paste_meta['id'], chunk_handler)
        
        if blob_writer:
            blob_writer.close()

        if not success and total_size == 0:
            logger.error(f"Failed to fetch content for {paste_meta['id']}")
            return

        final_content = full_content if not is_large else temp_blob_path
        storage_content = final_content

        # 2. Deduplication (SimHash)
        hash_input = full_content if not is_large else ""
        if is_large:
            with gzip.open(temp_blob_path, 'rt', encoding='utf-8') as f:
                hash_input = f.read(100 * 1024)
        
        c_hash = ContentHasher.calculate_hash(hash_input)
        duplicate = check_for_near_duplicates(c_hash) if c_hash else None
        
        timestamp_now = datetime.now(UTC).isoformat() + "Z"

        if duplicate:
            logger.info(f"Paste {paste_meta['id']} is a near-duplicate of leak ID {duplicate['id']}")
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                INSERT OR IGNORE INTO leaks (
                    source_type, source_name, external_id, url, title, 
                    content, content_hash, parent_id, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'paste', source_name, paste_meta['id'], paste_meta['url'], paste_meta['title'],
                    f"LINKED_TO:{duplicate['id']}", c_hash, duplicate['id'], timestamp_now
                ))
                conn.commit()
                conn.close()
                logger.info(f"Successfully created linked reference for duplicate {paste_meta['id']}.")
            except Exception as e:
                logger.error(f"Failed to create linked reference: {e}")

            if is_large and temp_blob_path and os.path.exists(temp_blob_path):
                os.remove(temp_blob_path)
            return

        # 4. AI Analysis Pipeline
        analysis_input = full_content if not is_large else temp_blob_path
        analysis = self._analyze_leak(analysis_input, paste_meta['title'])
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
            INSERT OR IGNORE INTO leaks (
                source_type, source_name, external_id, url, title, 
                content, content_hash, summary, relevance_score, patterns_found, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                'paste', source_name, paste_meta['id'], paste_meta['url'], paste_meta['title'],
                storage_content, c_hash, analysis.get("summary"), analysis.get("relevance_score", 0.0),
                analysis.get("patterns_json"), timestamp_now
            ))
            
            leak_id = cursor.lastrowid
            if leak_id:
                meta = paste_meta.get("meta", {})
                cursor.execute("""
                INSERT INTO paste_metadata (leak_id, author, syntax, scrape_timestamp)
                VALUES (?, ?, ?, ?)
                """, (leak_id, meta.get("author"), meta.get("syntax"), timestamp_now))
            
            conn.commit()
            conn.close()
            logger.info(f"Successfully saved and analyzed paste {paste_meta['id']}.")
        except Exception as e:
            logger.error(f"Failed to save paste {paste_meta['id']}: {e}")
            if is_large and temp_blob_path and os.path.exists(temp_blob_path):
                os.remove(temp_blob_path)

    def _analyze_leak(self, content: str, title: str) -> Dict[str, Any]:
        """
        Runs the content through pattern matching and LLM summarization.
        Supports parallel chunk scanning for large files.
        """
        matches = []
        # Check if content is a path (ends with .gz) or raw text
        is_blob = isinstance(content, str) and content.startswith("data/blobs/")
        
        if is_blob:
            logger.info("Using ParallelChunkScanner for large content (blob).")
            # For now, we load blob to scan, but ParallelChunkScanner could be optimized to read handle
            with gzip.open(content, 'rt', encoding='utf-8') as f:
                text = f.read()
            scanner = ParallelChunkScanner()
            matches = scanner.scan(text)
        elif len(content) > 5 * 1024 * 1024:
            logger.info("Using ParallelChunkScanner for large content (memory).")
            scanner = ParallelChunkScanner()
            matches = scanner.scan(content)
        else:
            matches = scan_text(content, min_confidence='low')

        patterns = []
        total_confidence = 0
        
        for m in matches:
            patterns.append({
                "type": m.category,
                "provider": m.provider,
                "confidence": m.confidence,
                "value": m.value[:10] + "..." # Redact for metadata
            })
            weight = {"high": 1.0, "medium": 0.5, "low": 0.2}.get(m.confidence, 0.1)
            total_confidence += weight

        relevance_score = min(5.0, total_confidence)

        summary = None
        if relevance_score > 0.5 or any(k in title.lower() for k in ["leak", "db", "combo", "pass"]):
            try:
                llm = get_llm(DEFAULT_MODEL)
                if is_blob:
                    with gzip.open(content, 'rt', encoding='utf-8') as f:
                        # Read first 5KB and last 5KB
                        first_part = f.read(5000)
                        f.seek(0, os.SEEK_END)
                        size = f.tell()
                        f.seek(max(0, size - 5000))
                        last_part = f.read(5000)
                        context_text = first_part + "\n... [TRUNCATED] ...\n" + last_part
                elif len(content) > 10000:
                    context_text = content[:5000] + "\n... [TRUNCATED] ...\n" + content[-5000:]
                else:
                    context_text = content
                summary = generate_summary(llm, title, { "leak_content": context_text })
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}")
                summary = "Analysis failed."

        return {
            "summary": summary,
            "relevance_score": relevance_score,
            "patterns_json": json.dumps(patterns),
            "match_count": len(matches)
        }

class ParallelChunkScanner:
    """
    Splits large text into chunks and scans them in parallel for credentials.
    """
    def __init__(self, chunk_size: int = 1024 * 1024, overlap: int = 4096):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def scan(self, text: str) -> List[Any]:
        chunks = []
        start = 0
        n = len(text)
        while start < n:
            end = min(n, start + self.chunk_size)
            chunks.append(text[start:end])
            if end == n:
                break
            start = end - self.overlap
            
        all_matches = []
        seen_values = set()
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_chunk = {executor.submit(scan_text, chunk, 'low'): i for i, chunk in enumerate(chunks)}
            for future in as_completed(future_to_chunk):
                try:
                    matches = future.result()
                    for m in matches:
                        if m.value not in seen_values:
                            all_matches.append(m)
                            seen_values.add(m.value)
                except Exception as e:
                    logger.error(f"Chunk scan failed: {e}")
                    
        return all_matches
