import asyncio
import logging
import json
import time
from typing import AsyncGenerator, Dict, List, Any, Optional, Set
from datetime import datetime
import requests

from robin.config import GITHUB_TOKEN
from robin.credential_patterns import CredentialPatternEngine
from robin.github_dorking import DORK_CATEGORIES, _rate_limited_get, GITHUB_API, GITHUB_DORK_QUERIES
from robin.trufflehog_engine import get_engine as get_trufflehog
from robin.ml_filter import get_filter as get_ml_filter
from robin.breach_lookup import lookup_email as find_breaches
from robin.leaklooker_engine import scan_databases
from robin.cicd_hunter import sweep_all_susceptible_repos
from robin.paste_scraper import Watcher as PasteWatcher
from robin.github_search import search_github
from robin.database import (
    load_scanned_hashes, save_scanned_hash, 
    load_autopilot_state, save_autopilot_state
)

logger = logging.getLogger(__name__)

class AutoPilotScout:
    """
    Autonomous Discovery Engine for high-value credentials.
    Implements Dual-Track (Flash-Watcher + Deep-Diver) strategy.
    """
    def __init__(self):
        self.pattern_engine = CredentialPatternEngine()
        self.trufflehog = get_trufflehog(enable_verification=True)
        self.ml_filter = get_ml_filter()
        self.is_running = False
        self._last_gist_id = load_autopilot_state("last_gist_id")
        self._dork_index = int(load_autopilot_state("dork_index") or 0)
        self._all_dorks = self._flatten_dorks()
        self._scanned_hashes: Set[str] = load_scanned_hashes(limit=2000)
        self._expanded_accounts: Set[str] = set()
        self.findings_queue = asyncio.Queue()

    def _flatten_dorks(self) -> List[str]:
        """Flattens DORK_CATEGORIES into a list prioritized by 'Most Wanted'."""
        prioritized = []
        # Use the imported dork categories
        dork_source = GITHUB_DORK_QUERIES

        # Priority 1: Email/Pass and API Keys
        for key in ["api_keys", "email_credentials", "most_wanted"]:
            if key in dork_source:
                prioritized.extend(dork_source[key])

        # Add the rest
        for cat, dorks in dork_source.items():
            if cat not in ["api_keys", "email_credentials", "most_wanted"]:
                prioritized.extend(dorks)
        return prioritized

    async def get_db_leak_stream(self):
        """Monitors for exposed databases using LeakLooker."""
        while self.is_running:
            try:
                logger.info("Auto-Pilot: Scanning for exposed databases...")
                # We'll use a curated set of popular DB types
                for db_type in ["mongodb", "elastic", "s3"]:
                    results = await asyncio.to_thread(scan_databases, db_type, max_results=5)
                    for res in results:
                        await self.findings_queue.put({
                            "type": "db_leak",
                            "data": res,
                            "label": f"Exposed {db_type.upper()}",
                            "timestamp": datetime.utcnow().isoformat()
                        })
                await asyncio.sleep(3600) # Hourly DB sweep
            except Exception as e:
                logger.error(f"DB-Leak-Watcher error: {e}")
                await asyncio.sleep(600)

    async def get_cicd_stream(self):
        """Monitors for leaks in CI/CD logs."""
        while self.is_running:
            try:
                logger.info("Auto-Pilot: Sweeping CI/CD logs...")
                hits = await asyncio.to_thread(sweep_all_susceptible_repos, max_repos=5)
                for hit in hits:
                    await self.findings_queue.put({
                        "type": "cicd_leak",
                        "data": hit,
                        "label": f"CI/CD Log: {hit.get('repo_name')}",
                        "timestamp": datetime.utcnow().isoformat()
                    })
                await asyncio.sleep(1800) # 30 min sweep
            except Exception as e:
                logger.error(f"CICD-Watcher error: {e}")
                await asyncio.sleep(300)

    async def get_paste_stream(self):
        """Monitors Pastebin and Telegram channels."""
        from robin.paste_scraper import PasteScraper, PastebinHandler, TelegramHandler
        
        # 1. Standard Polling Watcher (Pastebin, etc.)
        scraper = PasteScraper([PastebinHandler()])
        watcher = PasteWatcher(scraper)
        
        # 2. Real-time Telegram Monitor
        tg_handler = TelegramHandler()
        
        # We'll monitor some common aggregator channels (IDs or @names)
        # Note: In a real scenario, these would come from a config or database
        target_channels = ["@bot_logs", "@credential_leaks_test"] 
        
        # Start TG monitor in background
        def tg_callback(source_name, paste_meta):
            # Inject TG message into findings queue
            asyncio.create_task(self.findings_queue.put({
                "type": "paste_event",
                "data": paste_meta,
                "label": f"Telegram: {source_name}",
                "timestamp": datetime.now(UTC).isoformat()
            }))

        # Run TG monitor as a separate task
        asyncio.create_task(tg_handler.start_monitoring(target_channels, tg_callback))
        
        while self.is_running:
            try:
                # Watcher in paste_scraper.py has monitor_all_recent
                results = await asyncio.to_thread(scraper.monitor_all_recent)
                for source_name, pastes in results.items():
                    for p in pastes:
                        await self.findings_queue.put({
                            "type": "paste_event",
                            "data": p,
                            "label": f"Paste: {source_name}",
                            "timestamp": datetime.now(UTC).isoformat()
                        })
                await asyncio.sleep(300)
            except Exception as e:
                logger.error(f"Paste-Watcher error: {e}")
                await asyncio.sleep(300)

    async def scan_content(self, content: str, source_url: str, metadata: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """Handles noise-gating, ML filtering, and pattern extraction."""
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()
        if content_hash in self._scanned_hashes:
            return []
        
        self._scanned_hashes.add(content_hash)
        await asyncio.to_thread(save_scanned_hash, content_hash)
        
        if len(self._scanned_hashes) > 2000: 
            # Keep in-memory cache lean, database has the full list
            self._scanned_hashes.clear()
            self._scanned_hashes = await asyncio.to_thread(load_scanned_hashes, limit=1000)

        # 1. Noise-Gate & ML Filtering
        if not self.ml_filter.is_sensitive(content):
            return []

        findings = []
        # 2. Pattern Engine (Most Wanted)
        matches = self.pattern_engine.scan_text(content)
        for m in matches:
            # 3. Breach Enrichment for Emails
            enriched_data = {}
            if m.category == "email":
                breaches = await asyncio.to_thread(find_breaches, m.value)
                if breaches:
                    enriched_data["breach_count"] = len(breaches)
                    enriched_data["latest_breach"] = breaches[0].get("Name")

            findings.append({
                "type": m.category,
                "value": m.value,
                "confidence": m.confidence,
                "provider": m.provider,
                "source": source_url,
                "tool": "pattern_engine",
                "enrichment": enriched_data
            })

        # 4. TruffleHog (Verification for high-value keys)
        th_results = self.trufflehog.scan_text(content)
        for r in th_results:
            findings.append({
                "type": r.detector_type,
                "value": r.redacted_value,
                "verified": r.verified,
                "confidence": "critical" if r.verified else "high",
                "source": source_url,
                "tool": "trufflehog",
                "metadata": r.extra_data
            })

        # Lateral Movement: Expand to Account if finding is critical
        if any(f.get("verified") or f.get("confidence") == "critical" for f in findings):
            await self._trigger_lateral_expansion(source_url, metadata)

        return findings

    async def _trigger_lateral_expansion(self, source_url: str, metadata: Optional[Dict]):
        """Expands scanning to all public repos of the user if a leak is found."""
        owner = None
        if metadata and "owner" in metadata:
            owner = metadata["owner"]
        elif "github.com/" in source_url:
            parts = source_url.split("github.com/")[1].split("/")
            if len(parts) >= 1: owner = parts[0]

        if owner and owner not in self._expanded_accounts:
            self._expanded_accounts.add(owner)
            logger.warning(f"AUTO-PILOT LATERAL MOVEMENT: Triggering account-wide scan for '{owner}'")
            # Fetch other repos
            other_repos = await asyncio.to_thread(search_github, f"user:{owner}", limit=50)
            for repo in other_repos:
                await self.findings_queue.put({
                    "type": "lateral_expansion",
                    "data": repo,
                    "label": f"Lateral Hunt: {repo.get('title')}",
                    "timestamp": datetime.utcnow().isoformat()
                })

    async def start_engine(self) -> AsyncGenerator[str, None]:
        """Orchestrated Main Loop running multiple high-power hunters."""
        self.is_running = True

        # Start all producers and keep references to tasks
        producers = [
            self.get_gist_stream_wrapped(),
            self.get_paste_stream(),
            self.get_cicd_stream(),
            self.get_db_leak_stream(),
            self.run_dork_cycle_wrapped()
        ]

        self._producer_tasks = [asyncio.create_task(p) for p in producers]

        while self.is_running:
            event = await self.findings_queue.get()

            # Process findings based on type
            results = []
            label = event.get("label", "Unknown")

            try:
                if event["type"] in ["gist_event", "paste_event", "dork_hit", "cicd_leak"]:
                    content, source_url = await self._fetch_event_content(event)
                    if content:
                        yield json.dumps({"type": "message", "label": label, "text": f"Analyzing content from {source_url}..."})
                        results = await self.scan_content(content, source_url, event.get("data"))

                elif event["type"] == "db_leak":
                    yield json.dumps({"type": "message", "label": label, "text": f"Validating exposed database at {event['data'].get('ip')}..."})
                    results = [{
                        "type": "exposed_database",
                        "value": event["data"].get("ip"),
                        "source": event["data"].get("url"),
                        "confidence": "high",
                        "metadata": event["data"]
                    }]

                elif event["type"] == "lateral_expansion":
                    repo_name = event["data"].get("title") or event["data"].get("full_name")
                    yield json.dumps({"type": "message", "label": "LATERAL", "text": f"Initiating account-wide deep-dive on {repo_name}..."})
                    results = await self._deep_dive_repo(event["data"])

                for res in results:
                    yield json.dumps({"type": "finding", "label": label, "data": res})

            except Exception as e:
                logger.error(f"Finding processing error: {e}")
                yield json.dumps({"type": "error", "error": str(e)})

            self.findings_queue.task_done()

    async def get_gist_stream(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Polls public gist events."""
        while self.is_running:
            try:
                resp = await asyncio.to_thread(_rate_limited_get, f"{GITHUB_API}/gists/public", params={"per_page": 30})
                if resp and resp.status_code == 200:
                    gists = resp.json()
                    new_gists = []
                    if not self._last_gist_id:
                        if gists: self._last_gist_id = gists[0].get("id")
                    else:
                        for g in gists:
                            if g.get("id") == self._last_gist_id: break
                            new_gists.append(g)
                        if gists: self._last_gist_id = gists[0].get("id")
                    for gist in new_gists:
                        yield {"type": "gist_event", "data": gist, "timestamp": datetime.utcnow().isoformat()}
                    
                    if new_gists and self._last_gist_id:
                        await asyncio.to_thread(save_autopilot_state, "last_gist_id", self._last_gist_id)
                await asyncio.sleep(60)
            except Exception as e:
                logger.error(f"Gist-Watcher error: {e}")
                await asyncio.sleep(60)

    async def run_dork_cycle(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Runs scheduled precision dorks."""
        while self.is_running:
            try:
                dork = self._all_dorks[self._dork_index % len(self._all_dorks)]
                self._dork_index += 1
                logger.info(f"Auto-Pilot Deep-Diver: Running dork '{dork}'")
                await asyncio.to_thread(save_autopilot_state, "dork_index", str(self._dork_index))
                
                from robin.github_dorking import search_single_dork
                hits = await asyncio.to_thread(search_single_dork, dork, 5)
                for hit in hits:
                    yield {"type": "dork_hit", "data": hit, "dork": dork, "timestamp": datetime.utcnow().isoformat()}
                await asyncio.sleep(180)
            except Exception as e:
                logger.error(f"Deep-Diver error: {e}")
                await asyncio.sleep(180)

    async def _fetch_event_content(self, event) -> tuple[Optional[str], Optional[str]]:
        """Universal content fetcher."""
        try:
            if event["type"] == "gist_event":
                files = event["data"].get("files", {})
                for fname, fdata in files.items():
                    raw_url = fdata.get("raw_url")
                    if raw_url:
                        resp = await asyncio.to_thread(requests.get, raw_url, timeout=10)
                        if resp.status_code == 200: return resp.text, raw_url

            elif event["type"] == "paste_event":
                return event["data"].get("content"), event["data"].get("url")

            elif event["type"] == "dork_hit":
                link = event["data"].get("link")
                if link:
                    raw_url = link.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                    resp = await asyncio.to_thread(requests.get, raw_url, timeout=10)
                    if resp.status_code == 200: return resp.text, raw_url

            elif event["type"] == "cicd_leak":
                return event["data"].get("content"), event["data"].get("log_url")

        except Exception as e:
            logger.error(f"Content fetch failed: {e}")
        return None, None

    async def _deep_dive_repo(self, repo_data) -> List[Dict]:
        """Performs a full recursive scan of a target repository."""
        results = []
        repo_name = repo_data.get("title") or repo_data.get("full_name")
        if not repo_name: return []

        logger.info(f"Auto-Pilot: Starting Deep-Dive on {repo_name}")
        # Use existing search_github_code with a path-based query or just fetch tree
        import base64
        owner, repo = repo_name.split("/")
        tree_url = f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/main?recursive=1"
        resp = await asyncio.to_thread(_rate_limited_get, tree_url)

        if resp and resp.status_code == 200:
            tree = resp.json().get("tree", [])
            # Focus on config/env/secrets files first
            priority_files = [f for f in tree if any(k in f['path'].lower() for k in ["env", "config", "json", "yml", "yaml", "sql"])]
            for file_entry in priority_files[:20]: # Limit depth to avoid bans
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/main/{file_entry['path']}"
                file_resp = await asyncio.to_thread(requests.get, raw_url, timeout=10)
                if file_resp.status_code == 200:
                    findings = await self.scan_content(file_resp.text, raw_url, {"owner": owner, "repo": repo})
                    results.extend(findings)
                await asyncio.sleep(1) # Jitter

        return results

    async def get_gist_stream_wrapped(self):
        async for e in self.get_gist_stream():
            await self.findings_queue.put(e)

    async def run_dork_cycle_wrapped(self):
        async for e in self.run_dork_cycle():
            await self.findings_queue.put(e)

    def stop(self):
        self.is_running = False

# Global instance for the API
scout_instance = AutoPilotScout()
