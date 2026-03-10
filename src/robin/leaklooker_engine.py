"""
LeakLooker Integration Engine
Scans for exposed databases and services using BinaryEdge API
"""

import os
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ExposedDatabase:
    """Represents an exposed database or service"""
    ip: str
    port: int
    service_type: str  # mongodb, elasticsearch, s3, etc.
    country: Optional[str] = None
    asn: Optional[str] = None
    organization: Optional[str] = None
    database_name: Optional[str] = None
    collections: List[str] = field(default_factory=list)
    size_mb: Optional[float] = None
    open_access: bool = True
    metadata: Dict = field(default_factory=dict)
    discovered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    source_tool: str = "leaklooker"


class LeakLookerEngine:
    """Wrapper for LeakLooker-style database scanning"""

    def __init__(self):
        self.binaryedge_api_key = os.getenv('BINARYEDGE_API_KEY')
        self.api_base = "https://api.binaryedge.io/v2"

    def scan_exposed_databases(self, query: str, max_results: int = 100) -> List[ExposedDatabase]:
        """
        Scan for exposed databases using BinaryEdge API

        Args:
            query: Search query (domain, keyword, etc.)
            max_results: Maximum number of results to return

        Returns:
            List of ExposedDatabase objects
        """
        if not self.binaryedge_api_key:
            print("Warning: BINARYEDGE_API_KEY not set. Cannot scan for exposed databases.")
            return []

        results = []

        # Scan for different types of exposed services
        results.extend(self._scan_mongodb(query, max_results))
        results.extend(self._scan_elasticsearch(query, max_results))
        results.extend(self._scan_redis(query, max_results))
        results.extend(self._scan_s3_buckets(query, max_results))

        return results[:max_results]

    def _scan_mongodb(self, query: str, max_results: int) -> List[ExposedDatabase]:
        """Scan for exposed MongoDB instances"""
        return self._scan_service('mongodb', query, max_results, port=27017)

    def _scan_elasticsearch(self, query: str, max_results: int) -> List[ExposedDatabase]:
        """Scan for exposed Elasticsearch instances"""
        return self._scan_service('elasticsearch', query, max_results, port=9200)

    def _scan_redis(self, query: str, max_results: int) -> List[ExposedDatabase]:
        """Scan for exposed Redis instances"""
        return self._scan_service('redis', query, max_results, port=6379)

    def _scan_service(self, service_type: str, query: str, max_results: int, port: int) -> List[ExposedDatabase]:
        """Generic service scanner using BinaryEdge"""
        if not self.binaryedge_api_key:
            return []

        results = []

        try:
            # BinaryEdge search query
            search_query = f"{service_type} AND {query}"

            headers = {
                'X-Key': self.binaryedge_api_key
            }

            url = f"{self.api_base}/query/search"
            params = {
                'query': search_query,
                'page': 1
            }

            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                for event in data.get('events', [])[:max_results]:
                    results.append(self._parse_event(event, service_type))
            elif response.status_code == 401:
                print("BinaryEdge API Key invalid or expired.")
            elif response.status_code == 429:
                print("BinaryEdge rate limit exceeded.")

        except Exception as e:
            print(f"Error scanning {service_type}: {e}")

        return results

    def _scan_s3_buckets(self, query: str, max_results: int) -> List[ExposedDatabase]:
        """Scan for exposed S3 buckets using GrayhatWarfare API if available"""
        results = []
        grayhat_api_key = os.getenv('GRAYHATWARFARE_API_KEY')
        if not grayhat_api_key:
            return results

        try:
            url = "https://buckets.grayhatwarfare.com/api/v2/buckets"
            headers = {"Authorization": f"Bearer {grayhat_api_key}"}
            params = {"keywords": query, "limit": max_results}

            response = requests.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                for bucket in data.get('buckets', []):
                    results.append(ExposedDatabase(
                        ip="",
                        port=80,
                        service_type="s3",
                        database_name=bucket.get('bucket'),
                        metadata=bucket,
                        source_tool="grayhatwarfare"
                    ))
        except Exception as e:
            print(f"Error scanning S3 buckets: {e}")

        return results

    def _parse_event(self, event: Dict, service_type: str) -> ExposedDatabase:
        """Parse BinaryEdge event into ExposedDatabase"""
        return ExposedDatabase(
            ip=event.get('target', {}).get('ip', ''),
            port=event.get('target', {}).get('port', 0),
            service_type=service_type,
            country=event.get('origin', {}).get('country', ''),
            asn=event.get('origin', {}).get('asn', ''),
            organization=event.get('origin', {}).get('org', ''),
            metadata=event
        )

    def get_stats(self) -> Dict:
        """Get statistics about the engine"""
        return {
            'binaryedge_configured': bool(self.binaryedge_api_key),
            'supported_services': ['mongodb', 'elasticsearch', 'redis', 's3']
        }


# Global instance
_engine = None

def get_engine() -> LeakLookerEngine:
    """Get the global LeakLooker engine instance"""
    global _engine
    if _engine is None:
        _engine = LeakLookerEngine()
    return _engine


def scan_exposed_databases(query: str, max_results: int = 100) -> List[ExposedDatabase]:
    """Scan for exposed databases"""
    return get_engine().scan_exposed_databases(query, max_results)


# Alias for compatibility with auto_pilot
scan_databases = scan_exposed_databases
