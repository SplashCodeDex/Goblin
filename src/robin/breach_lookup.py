"""
h8mail Breach Lookup Integration
Enriches emails with breach history from multiple sources
"""

import os
import re
import json
import time
import hashlib
import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests

logger = logging.getLogger(__name__)

# Rate limit delay between calls to the same API (seconds)
BREACH_RATE_LIMIT_S = float(os.getenv('BREACH_RATE_LIMIT_MS', '1000')) / 1000.0
BREACH_REQUEST_TIMEOUT = 15

# h8mail imports (with fallback if not installed)
try:
    import h8mail
    H8MAIL_AVAILABLE = True
except ImportError:
    H8MAIL_AVAILABLE = False
    logging.getLogger(__name__).warning("h8mail not installed. Breach lookup features will be disabled.")


@dataclass
class BreachRecord:
    """Represents a breach record for an email"""
    email: str
    breach_name: str
    breach_date: Optional[str] = None
    data_classes: List[str] = field(default_factory=list)  # Types of data leaked
    password: Optional[str] = None  # Leaked password if available
    password_hash: Optional[str] = None
    source: str = "unknown"  # Which breach DB (HIBP, Snusbase, etc.)
    metadata: Dict = field(default_factory=dict)


@dataclass
class EmailBreachSummary:
    """Summary of all breaches for an email"""
    email: str
    total_breaches: int
    breach_records: List[BreachRecord]
    pwned: bool  # True if email found in any breach
    leaked_passwords: List[str] = field(default_factory=list)
    data_classes_summary: Set[str] = field(default_factory=set)
    sources: Set[str] = field(default_factory=set)
    lookup_timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


class BreachLookupEngine:
    """Wrapper for h8mail breach lookup with caching"""

    def __init__(self, cache_ttl_hours: int = 168):  # 1 week default
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.cache: Dict[str, EmailBreachSummary] = {}
        self.cache_file = Path(__file__).parent / ".breach_cache.json"
        self._load_cache()

        # API keys from environment
        self.api_keys = {
            'hibp': os.getenv('HIBP_API_KEY'),
            'snusbase': os.getenv('SNUSBASE_API_KEY'),
            'dehashed': os.getenv('DEHASHED_API_KEY'),
            'intelx': os.getenv('INTELX_API_KEY'),
            'leaklookup': os.getenv('LEAKLOOKUP_API_KEY'),
            'weleakinfo': os.getenv('WELEAKINFO_API_KEY'),
            'scylla': os.getenv('SCYLLA_API_KEY'),
        }

        self.enabled_sources = [k for k, v in self.api_keys.items() if v]

    def _load_cache(self):
        """Load breach lookup cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    now = datetime.now()

                    # Reconstruct cache with filtering of expired entries
                    for email, data in cache_data.items():
                        try:
                            timestamp = datetime.fromisoformat(data['lookup_timestamp'])
                            if timestamp + self.cache_ttl > now:
                                # Reconstruct breach records
                                breach_records = [
                                    BreachRecord(**record) for record in data['breach_records']
                                ]
                                summary = EmailBreachSummary(
                                    email=data['email'],
                                    total_breaches=data['total_breaches'],
                                    breach_records=breach_records,
                                    pwned=data['pwned'],
                                    leaked_passwords=data['leaked_passwords'],
                                    data_classes_summary=set(data['data_classes_summary']),
                                    sources=set(data['sources']),
                                    lookup_timestamp=data['lookup_timestamp']
                                )
                                self.cache[email] = summary
                        except Exception as e:
                            print(f"Error loading cached entry for {email}: {e}")

            except Exception as e:
                print(f"Error loading breach cache: {e}")
                self.cache = {}

    def _save_cache(self):
        """Save breach lookup cache to disk"""
        try:
            cache_data = {}
            for email, summary in self.cache.items():
                cache_data[email] = {
                    'email': summary.email,
                    'total_breaches': summary.total_breaches,
                    'breach_records': [
                        {
                            'email': r.email,
                            'breach_name': r.breach_name,
                            'breach_date': r.breach_date,
                            'data_classes': r.data_classes,
                            'password': r.password,
                            'password_hash': r.password_hash,
                            'source': r.source,
                            'metadata': r.metadata
                        }
                        for r in summary.breach_records
                    ],
                    'pwned': summary.pwned,
                    'leaked_passwords': summary.leaked_passwords,
                    'data_classes_summary': list(summary.data_classes_summary),
                    'sources': list(summary.sources),
                    'lookup_timestamp': summary.lookup_timestamp
                }

            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            print(f"Error saving breach cache: {e}")

    def lookup_email(self, email: str, force_refresh: bool = False) -> Optional[EmailBreachSummary]:
        """
        Lookup breach history for a single email

        Args:
            email: Email address to lookup
            force_refresh: Force refresh even if cached

        Returns:
            EmailBreachSummary or None if lookup fails
        """
        # Normalize email
        email = email.lower().strip()

        # Check cache first
        if not force_refresh and email in self.cache:
            return self.cache[email]

        # Check if any sources are enabled
        if not self.enabled_sources:
            print("Warning: No breach lookup API keys configured")
            return None

        try:
            # Perform lookup using available sources
            breach_records = []

            # HIBP (Have I Been Pwned)
            if 'hibp' in self.enabled_sources:
                hibp_results = self._lookup_hibp(email)
                breach_records.extend(hibp_results)

            # Snusbase
            if 'snusbase' in self.enabled_sources:
                snusbase_results = self._lookup_snusbase(email)
                breach_records.extend(snusbase_results)

            # Dehashed
            if 'dehashed' in self.enabled_sources:
                dehashed_results = self._lookup_dehashed(email)
                breach_records.extend(dehashed_results)

            # IntelX
            if 'intelx' in self.enabled_sources:
                intelx_results = self._lookup_intelx(email)
                breach_records.extend(intelx_results)

            # LeakLookup
            if 'leaklookup' in self.enabled_sources:
                leaklookup_results = self._lookup_leaklookup(email)
                breach_records.extend(leaklookup_results)

            # WeLeakInfo
            if 'weleakinfo' in self.enabled_sources:
                weleakinfo_results = self._lookup_weleakinfo(email)
                breach_records.extend(weleakinfo_results)

            # Scylla
            if 'scylla' in self.enabled_sources:
                scylla_results = self._lookup_scylla(email)
                breach_records.extend(scylla_results)

            # Build summary
            summary = self._build_summary(email, breach_records)

            # Cache the result
            self.cache[email] = summary
            self._save_cache()

            return summary

        except Exception as e:
            logger.error(f"Error looking up email {email}: {e}")
            return None

    def lookup_emails_bulk(self, emails: List[str], max_concurrent: int = 5) -> Dict[str, EmailBreachSummary]:
        """
        Lookup breach history for multiple emails concurrently.

        Args:
            emails: List of email addresses
            max_concurrent: Maximum concurrent lookups

        Returns:
            Dictionary mapping email to EmailBreachSummary
        """
        results = {}

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            future_map = {
                executor.submit(self.lookup_email, email): email
                for email in emails
            }
            for future in as_completed(future_map):
                email = future_map[future]
                try:
                    summary = future.result()
                    if summary:
                        results[email] = summary
                except Exception as e:
                    logger.error(f"Bulk lookup error for {email}: {e}")

        return results

    def _lookup_hibp(self, email: str) -> List[BreachRecord]:
        """Lookup email in Have I Been Pwned"""
        records = []
        if not self.api_keys.get('hibp'):
            return records

        try:
            url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
            headers = {
                'hibp-api-key': self.api_keys['hibp'],
                'user-agent': 'Goblin-Threat-Intel'
            }
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                for breach in response.json():
                    records.append(BreachRecord(
                        email=email,
                        breach_name=breach.get('Name', 'Unknown'),
                        breach_date=breach.get('BreachDate'),
                        data_classes=breach.get('DataClasses', []),
                        source='hibp',
                        metadata=breach
                    ))
            elif response.status_code == 429:
                print(f"HIBP Rate limit exceeded for {email}")
        except Exception as e:
            print(f"Error looking up HIBP for {email}: {e}")

        return records

    def _lookup_snusbase(self, email: str) -> List[BreachRecord]:
        """Lookup email in Snusbase"""
        records = []
        if not self.api_keys.get('snusbase'):
            return records

        try:
            url = "https://api.snusbase.com/data/search"
            headers = {
                'Auth': self.api_keys['snusbase'],
                'Content-Type': 'application/json'
            }
            payload = {
                'terms': [email],
                'types': ['email'],
                'wildcard': False
            }
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                results = data.get('results', {})
                for term, term_results in results.items():
                    for result in term_results:
                        data_classes = []
                        if result.get('password'): data_classes.append('Passwords')
                        if result.get('hash'): data_classes.append('Password Hashes')

                        records.append(BreachRecord(
                            email=email,
                            breach_name=result.get('database', 'Unknown Snusbase Breach'),
                            password=result.get('password'),
                            password_hash=result.get('hash'),
                            data_classes=data_classes,
                            source='snusbase',
                            metadata=result
                        ))
        except Exception as e:
            print(f"Error looking up Snusbase for {email}: {e}")

        return records

    def _lookup_dehashed(self, email: str) -> List[BreachRecord]:
        """Lookup email in Dehashed"""
        records = []
        if not self.api_keys.get('dehashed'):
            return records

        try:
            url = "https://api.dehashed.com/search"
            # Dehashed usually requires an email and API key for basic auth
            dehashed_email = os.getenv('DEHASHED_EMAIL', 'admin@example.com') # fallback or require from env
            auth = (dehashed_email, self.api_keys['dehashed'])
            headers = {'Accept': 'application/json'}
            params = {'query': f'email:"{email}"'}

            response = requests.get(url, headers=headers, auth=auth, params=params)
            if response.status_code == 200:
                data = response.json()
                for entry in data.get('entries', []) or []:
                    data_classes = []
                    if entry.get('password'): data_classes.append('Passwords')
                    if entry.get('hashed_password'): data_classes.append('Password Hashes')

                    records.append(BreachRecord(
                        email=email,
                        breach_name=entry.get('obtain_from', entry.get('database_name', 'Unknown Dehashed Breach')),
                        password=entry.get('password'),
                        password_hash=entry.get('hashed_password'),
                        data_classes=data_classes,
                        source='dehashed',
                        metadata=entry
                    ))
        except Exception as e:
            print(f"Error looking up Dehashed for {email}: {e}")

        return records

    def _lookup_intelx(self, email: str) -> List[BreachRecord]:
        """Lookup email in Intelligence X with full result polling."""
        records = []
        if not self.api_keys.get('intelx'):
            return records

        try:
            # Step 1: Initiate the search
            search_url = "https://2.intelx.io/intelligent/search"
            headers = {'x-key': self.api_keys['intelx']}
            payload = {
                'term': email,
                'maxresults': 20,
                'media': 0,  # 0 = all media types
                'sort': 2,   # 2 = relevance
                'terminate': [],
            }

            response = requests.post(search_url, headers=headers, json=payload, timeout=BREACH_REQUEST_TIMEOUT)
            if response.status_code != 200:
                logger.warning(f"IntelX search initiation failed: {response.status_code}")
                return records

            data = response.json()
            search_id = data.get('id')
            if not search_id:
                return records

            # Step 2: Poll for results with exponential backoff (max 5 attempts, 30s total)
            result_url = f"https://2.intelx.io/intelligent/search/result?id={search_id}"
            for attempt in range(5):
                wait_time = min(2 ** attempt, 10)  # 1, 2, 4, 8, 10 seconds
                time.sleep(wait_time)

                result_resp = requests.get(result_url, headers=headers, timeout=BREACH_REQUEST_TIMEOUT)
                if result_resp.status_code != 200:
                    continue

                result_data = result_resp.json()
                status = result_data.get('status', -1)
                search_records = result_data.get('records', [])

                for rec in search_records:
                    breach_name = rec.get('name', rec.get('systemid', 'IntelligenceX Finding'))
                    date_str = rec.get('date', rec.get('added'))
                    data_classes = []
                    media_type = rec.get('media', 0)
                    if media_type in (1, 2):  # Pastes / dumps
                        data_classes.append('Paste/Dump')
                    if media_type == 24:  # Leaked credentials
                        data_classes.append('Credentials')

                    records.append(BreachRecord(
                        email=email,
                        breach_name=breach_name,
                        breach_date=date_str,
                        data_classes=data_classes or ['IntelX Match'],
                        source='intelx',
                        metadata={
                            'search_id': search_id,
                            'systemid': rec.get('systemid'),
                            'bucket': rec.get('bucket'),
                            'media': media_type,
                        }
                    ))

                # status 0 = still running, 1 = timed out, 2 = finished
                if status in (1, 2) or len(search_records) > 0:
                    break

        except Exception as e:
            logger.error(f"Error looking up IntelX for {email}: {e}")

        return records

    def _lookup_leaklookup(self, email: str) -> List[BreachRecord]:
        """Lookup email in LeakLookup.com API."""
        records = []
        if not self.api_keys.get('leaklookup'):
            return records

        try:
            url = "https://leak-lookup.com/api/search"
            payload = {
                'key': self.api_keys['leaklookup'],
                'type': 'email_address',
                'query': email
            }
            response = requests.post(url, data=payload, timeout=BREACH_REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                if data.get('error') == 'false' and data.get('message'):
                    # message is a dict of {database_name: [records]}
                    results_data = data['message']
                    if isinstance(results_data, dict):
                        for db_name, entries in results_data.items():
                            data_classes = []
                            if isinstance(entries, list):
                                for entry in entries:
                                    pwd = entry.get('password') if isinstance(entry, dict) else None
                                    pwd_hash = entry.get('hash') if isinstance(entry, dict) else None
                                    if pwd: data_classes.append('Passwords')
                                    if pwd_hash: data_classes.append('Password Hashes')
                                    records.append(BreachRecord(
                                        email=email,
                                        breach_name=db_name,
                                        password=pwd,
                                        password_hash=pwd_hash,
                                        data_classes=data_classes or ['Email Addresses'],
                                        source='leaklookup',
                                        metadata=entry if isinstance(entry, dict) else {'raw': entry}
                                    ))
                            else:
                                # Simple string result
                                records.append(BreachRecord(
                                    email=email,
                                    breach_name=db_name,
                                    data_classes=['Email Addresses'],
                                    source='leaklookup',
                                    metadata={'raw': entries}
                                ))
            elif response.status_code == 429:
                logger.warning(f"LeakLookup rate limit exceeded for {email}")
                time.sleep(BREACH_RATE_LIMIT_S)
        except Exception as e:
            logger.error(f"Error looking up LeakLookup for {email}: {e}")

        return records

    def _lookup_weleakinfo(self, email: str) -> List[BreachRecord]:
        """Lookup email in WeLeakInfo v2 API."""
        records = []
        if not self.api_keys.get('weleakinfo'):
            return records

        try:
            url = f"https://api.weleakinfo.to/api?value={email}&type=email"
            headers = {
                'Authorization': f'Bearer {self.api_keys["weleakinfo"]}',
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers, timeout=BREACH_REQUEST_TIMEOUT)
            if response.status_code == 200:
                data = response.json()
                if data.get('Success') and data.get('Data'):
                    for entry in data['Data']:
                        data_classes = []
                        pwd = entry.get('Password')
                        pwd_hash = entry.get('Hash')
                        if pwd: data_classes.append('Passwords')
                        if pwd_hash: data_classes.append('Password Hashes')
                        if entry.get('Username'): data_classes.append('Usernames')

                        records.append(BreachRecord(
                            email=email,
                            breach_name=entry.get('Database', 'WeLeakInfo Finding'),
                            password=pwd,
                            password_hash=pwd_hash,
                            data_classes=data_classes or ['Email Addresses'],
                            source='weleakinfo',
                            metadata=entry
                        ))
            elif response.status_code == 429:
                logger.warning(f"WeLeakInfo rate limit exceeded for {email}")
                time.sleep(BREACH_RATE_LIMIT_S)
        except Exception as e:
            logger.error(f"Error looking up WeLeakInfo for {email}: {e}")

        return records

    def _lookup_scylla(self, email: str) -> List[BreachRecord]:
        """Lookup email in Scylla.so API."""
        records = []
        if not self.api_keys.get('scylla'):
            return records

        try:
            url = f"https://scylla.so/search?q=email:{email}&size=20"
            headers = {
                'api-key': self.api_keys['scylla'],
                'Accept': 'application/json'
            }
            response = requests.get(url, headers=headers, timeout=BREACH_REQUEST_TIMEOUT)
            if response.status_code == 200:
                results_data = response.json()
                hits = results_data if isinstance(results_data, list) else results_data.get('hits', {}).get('hits', [])
                for hit in hits:
                    src = hit.get('_source', hit) if isinstance(hit, dict) else {}
                    data_classes = []
                    pwd = src.get('passhash') or src.get('password')
                    if pwd: data_classes.append('Passwords')
                    if src.get('username'): data_classes.append('Usernames')
                    if src.get('ip'): data_classes.append('IP Addresses')
                    if src.get('domain'): data_classes.append('Domains')

                    records.append(BreachRecord(
                        email=email,
                        breach_name=src.get('source', src.get('domain', 'Scylla Finding')),
                        password=pwd,
                        data_classes=data_classes or ['Email Addresses'],
                        source='scylla',
                        metadata=src
                    ))
            elif response.status_code == 429:
                logger.warning(f"Scylla rate limit exceeded for {email}")
                time.sleep(BREACH_RATE_LIMIT_S)
        except Exception as e:
            logger.error(f"Error looking up Scylla for {email}: {e}")

        return records

    def _build_summary(self, email: str, breach_records: List[BreachRecord]) -> EmailBreachSummary:
        """Build a summary from breach records"""
        leaked_passwords = []
        data_classes = set()
        sources = set()

        for record in breach_records:
            if record.password:
                leaked_passwords.append(record.password)
            data_classes.update(record.data_classes)
            sources.add(record.source)

        summary = EmailBreachSummary(
            email=email,
            total_breaches=len(breach_records),
            breach_records=breach_records,
            pwned=len(breach_records) > 0,
            leaked_passwords=leaked_passwords,
            data_classes_summary=data_classes,
            sources=sources
        )

        return summary

    def extract_emails_from_text(self, text: str) -> List[str]:
        """Extract email addresses from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return list(set(email.lower() for email in emails))

    def clear_cache(self):
        """Clear the breach lookup cache"""
        self.cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

    def get_cache_stats(self) -> Dict:
        """Get statistics about the cache"""
        pwned_count = sum(1 for s in self.cache.values() if s.pwned)

        return {
            'total_cached_emails': len(self.cache),
            'pwned_emails': pwned_count,
            'clean_emails': len(self.cache) - pwned_count,
            'enabled_sources': self.enabled_sources,
            'all_sources': list(self.api_keys.keys()),
            'source_count': len(self.enabled_sources),
            'total_source_count': len(self.api_keys),
            'cache_file': str(self.cache_file),
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600
        }

    def get_breach_statistics(self) -> Dict:
        """Get statistics about all cached breaches"""
        all_breaches = set()
        all_data_classes = set()
        all_sources = set()
        total_passwords = 0

        for summary in self.cache.values():
            for record in summary.breach_records:
                all_breaches.add(record.breach_name)
                all_data_classes.update(record.data_classes)
                all_sources.add(record.source)
                if record.password:
                    total_passwords += 1

        return {
            'unique_breaches': len(all_breaches),
            'breach_names': sorted(list(all_breaches)),
            'data_classes': sorted(list(all_data_classes)),
            'sources': sorted(list(all_sources)),
            'total_leaked_passwords': total_passwords
        }


# Global instance
_engine = None

def get_engine() -> BreachLookupEngine:
    """Get the global breach lookup engine instance"""
    global _engine
    if _engine is None:
        _engine = BreachLookupEngine()
    return _engine


# Convenience functions
def lookup_email(email: str) -> Optional[EmailBreachSummary]:
    """Lookup breach history for an email"""
    return get_engine().lookup_email(email)


def lookup_emails_bulk(emails: List[str]) -> Dict[str, EmailBreachSummary]:
    """Lookup breach history for multiple emails"""
    return get_engine().lookup_emails_bulk(emails)


def extract_and_lookup_emails(text: str) -> Dict[str, EmailBreachSummary]:
    """Extract emails from text and lookup their breach history"""
    engine = get_engine()
    emails = engine.extract_emails_from_text(text)
    return engine.lookup_emails_bulk(emails)


def is_email_pwned(email: str) -> bool:
    """Check if an email has been pwned"""
    summary = lookup_email(email)
    return summary.pwned if summary else False
