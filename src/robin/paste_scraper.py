import logging
import random
import time
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from .scrape import get_tor_session, USER_AGENTS

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

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches the site for a specific query.
        Default implementation uses Google Dorking via site: parameter.
        """
        # Note: Many paste sites block internal search or don't have one.
        # We can leverage search.py logic or site-specific search URLs.
        return []

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

class PastebinHandler(PasteSource):
    """
    Handler for Pastebin.com.
    """
    def __init__(self):
        super().__init__("Pastebin", "https://pastebin.com")

    def get_recent(self) -> List[Dict[str, Any]]:
        url = f"{self.base_url}/archive"
        resp = self._get_request(url)
        if not resp or resp.status_code != 200:
            return []
        
        soup = BeautifulSoup(resp.text, "html.parser")
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
        # Use raw URL for easier content extraction
        url = f"{self.base_url}/raw/{paste_id}"
        resp = self._get_request(url)
        return resp.text if resp and resp.status_code == 200 else None

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
        resp = self._get_request(url)
        if not resp or resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
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
        resp = self._get_request(url)
        if not resp or resp.status_code != 200:
            return None
        
        soup = BeautifulSoup(resp.text, "html.parser")
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
    def __init__(self):
        super().__init__("TelegramLogs", "https://t.me")
        from .config import TELEGRAM_API_ID, TELEGRAM_API_HASH
        self.api_id = TELEGRAM_API_ID
        self.api_hash = TELEGRAM_API_HASH
        self.client = None

    def get_recent(self) -> List[Dict[str, Any]]:
        # In a real implementation, this would use telethon to listen to channels.
        # For now, we provide a placeholder that could be expanded.
        return []

    def scrape_paste(self, paste_id: str) -> Optional[str]:
        # Implementation would fetch specific message content.
        return None

    async def monitor_channels(self, channel_ids: List[str]):
        """
        Asynchronous monitoring of specific channels.
        """
        if not self.api_id or not self.api_hash:
            logger.warning("Telegram API credentials missing. Skipping monitor.")
            return

        from telethon import TelegramClient, events
        self.client = TelegramClient('robin_session', self.api_id, self.api_hash)
        
        @self.client.on(events.NewMessage(chats=channel_ids))
        async def handler(event):
            # Process new log message
            logger.info(f"New Telegram log from {event.chat_id}")
            # Logic to save to database would go here
            
        await self.client.start()
        await self.client.run_until_disconnected()

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
        self._seen_ids = set() # Simple in-memory deduplication (resets on restart)

    def start(self):
        """
        Starts the monitoring loop.
        """
        self.running = True
        logger.info(f"Watcher started. Polling interval: {self.poll_interval}s")
        
        try:
            while self.running:
                all_recent = self.scraper.monitor_all_recent()
                for source_name, pastes in all_recent.items():
                    for paste in pastes:
                        p_id = f"{source_name}:{paste['id']}"
                        if p_id not in self._seen_ids:
                            self._seen_ids.add(p_id)
                            self._process_new_paste(source_name, paste)
                
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
        """
        source = next((s for s in self.scraper.sources if s.name == source_name), None)
        if not source:
            return

        logger.info(f"New paste discovered on {source_name}: {paste_meta['id']}")
        content = source.scrape_paste(paste_meta['id'])
        
        if content:
            # AI Analysis Pipeline
            analysis = self._analyze_leak(content, paste_meta['title'])
            
            from .database import get_db_connection
            from datetime import datetime
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # Insert into leaks table with analysis results
                cursor.execute("""
                INSERT OR IGNORE INTO leaks (
                    source_type, source_name, external_id, url, title, 
                    content, summary, relevance_score, patterns_found, timestamp
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'paste',
                    source_name,
                    paste_meta['id'],
                    paste_meta['url'],
                    paste_meta['title'],
                    content,
                    analysis.get("summary"),
                    analysis.get("relevance_score", 0.0),
                    analysis.get("patterns_json"),
                    datetime.utcnow().isoformat() + "Z"
                ))
                
                leak_id = cursor.lastrowid
                if leak_id:
                    # Insert metadata if available
                    meta = paste_meta.get("meta", {})
                    cursor.execute("""
                    INSERT INTO paste_metadata (leak_id, author, syntax, scrape_timestamp)
                    VALUES (?, ?, ?, ?)
                    """, (
                        leak_id,
                        meta.get("author"),
                        meta.get("syntax"),
                        datetime.utcnow().isoformat() + "Z"
                    ))
                
                conn.commit()
                conn.close()
                logger.info(f"Successfully saved and analyzed paste {paste_meta['id']}.")
            except Exception as e:
                logger.error(f"Failed to save paste {paste_meta['id']}: {e}")

    def _analyze_leak(self, content: str, title: str) -> Dict[str, Any]:
        """
        Runs the content through pattern matching and LLM summarization.
        """
        import json
        from .credential_patterns import scan_text
        from .llm import get_llm, generate_summary
        from .config import DEFAULT_MODEL

        # 1. Pattern Matching
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
            # Simple scoring: high=1.0, medium=0.5, low=0.2
            weight = {"high": 1.0, "medium": 0.5, "low": 0.2}.get(m.confidence, 0.1)
            total_confidence += weight

        # Normalize relevance score (capped at 5.0)
        relevance_score = min(5.0, total_confidence)

        # 2. LLM Summarization (Only if relevance score > 0 or interesting title)
        summary = None
        if relevance_score > 0.5 or any(k in title.lower() for k in ["leak", "db", "combo", "pass"]):
            try:
                llm = get_llm(DEFAULT_MODEL)
                summary = generate_summary(llm, title, { "leak_content": content[:2000] })
            except Exception as e:
                logger.warning(f"LLM summarization failed: {e}")
                summary = "Analysis failed."

        return {
            "summary": summary,
            "relevance_score": relevance_score,
            "patterns_json": json.dumps(patterns),
            "match_count": len(matches)
        }
