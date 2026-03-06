"""
Unified Credential Pattern Engine
Combines 1600+ patterns from Secrets Patterns DB + 150+ from Gitleaks
Includes entropy analysis and provider-specific detection
"""

import re
import math
import yaml
import tomllib
from pathlib import Path
from typing import List, Dict, Optional, Set
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class CredentialMatch:
    """Represents a detected credential match"""
    pattern_name: str
    pattern_id: str
    value: str
    start_pos: int
    end_pos: int
    confidence: str  # high, medium, low
    category: str  # api_keys, credentials, tokens, private_keys, etc.
    provider: Optional[str] = None  # AWS, GitHub, Stripe, etc.
    entropy: Optional[float] = None
    source_tool: str = "credential_patterns"  # Which tool detected it
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class CredentialPatternEngine:
    """Unified pattern engine that loads and compiles patterns from multiple sources"""

    def __init__(self):
        self.patterns: List[Dict] = []
        self.compiled_patterns: List[Dict] = []
        self.allowlist_patterns: List[re.Pattern] = []
        self.categories: Dict[str, List[Dict]] = defaultdict(list)
        self.loaded = False

    def load_patterns(self):
        """Load and compile all patterns from all sources"""
        if self.loaded:
            return

        # Load from Secrets Patterns DB
        self._load_secrets_patterns_db()

        # Load from Gitleaks
        self._load_gitleaks_patterns()

        # Add custom dark web patterns
        self._load_custom_patterns()

        # Compile all patterns
        self._compile_patterns()

        self.loaded = True

    def _load_secrets_patterns_db(self):
        """Load patterns from Secrets Patterns DB YAML"""
        yaml_path = Path(__file__).parent.parent.parent / "vendor" / "secrets-patterns-db" / "db" / "rules-stable.yml"

        if not yaml_path.exists():
            print(f"Warning: Secrets Patterns DB not found at {yaml_path}")
            return

        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data or 'patterns' not in data:
                print("Warning: Invalid Secrets Patterns DB format")
                return

            for pattern in data['patterns']:
                # Extract regex properly. The 'pattern' key may be a dictionary containing 'regex'
                regex_val = pattern.get('regex')
                if not regex_val:
                    pat_val = pattern.get('pattern', '')
                    if isinstance(pat_val, dict):
                        regex_val = pat_val.get('regex', '')
                    else:
                        regex_val = pat_val

                pattern_entry = {
                    'id': pattern.get('id', pattern.get('name', 'unknown')),
                    'name': pattern.get('name', pattern.get('id', 'unknown')),
                    'regex': regex_val,
                    'confidence': pattern.get('confidence', 'medium'),
                    'category': self._normalize_category(pattern.get('category', 'credentials')),
                    'provider': pattern.get('provider'),
                    'description': pattern.get('description', ''),
                    'tags': pattern.get('tags', []),
                    'source': 'secrets-patterns-db'
                }

                if pattern_entry['regex']:
                    self.patterns.append(pattern_entry)
                    self.categories[pattern_entry['category']].append(pattern_entry)

            print(f"Loaded {len(self.patterns)} patterns from Secrets Patterns DB")

        except Exception as e:
            print(f"Error loading Secrets Patterns DB: {e}")

    def _load_gitleaks_patterns(self):
        """Load patterns from Gitleaks TOML"""
        toml_path = Path(__file__).parent.parent.parent / "vendor" / "gitleaks" / "gitleaks.toml"

        if not toml_path.exists():
            print(f"Warning: Gitleaks config not found at {toml_path}")
            return

        try:
            with open(toml_path, 'rb') as f:
                data = tomllib.load(f)

            # Load rules
            rules = data.get('rules', [])
            initial_count = len(self.patterns)

            for rule in rules:
                # Skip if we already have a similar pattern
                rule_id = rule.get('id', '')
                if any(p['id'] == rule_id for p in self.patterns):
                    continue

                pattern_entry = {
                    'id': rule_id,
                    'name': rule.get('description', rule_id),
                    'regex': rule.get('regex', ''),
                    'confidence': 'high' if rule.get('entropy', 0) > 0 else 'medium',
                    'category': self._infer_category_from_id(rule_id),
                    'provider': self._extract_provider_from_id(rule_id),
                    'description': rule.get('description', ''),
                    'keywords': rule.get('keywords', []),
                    'entropy': rule.get('entropy'),
                    'tags': [rule_id.split('-')[0]] if '-' in rule_id else [],
                    'source': 'gitleaks'
                }

                if pattern_entry['regex']:
                    self.patterns.append(pattern_entry)
                    self.categories[pattern_entry['category']].append(pattern_entry)

            # Load allowlist patterns
            if 'allowlist' in data:
                allowlist = data['allowlist']
                for pattern_str in allowlist.get('regexes', []):
                    try:
                        self.allowlist_patterns.append(re.compile(pattern_str))
                    except re.error:
                        pass

            new_patterns = len(self.patterns) - initial_count
            print(f"Loaded {new_patterns} additional patterns from Gitleaks (Total: {len(self.patterns)})")
            print(f"Loaded {len(self.allowlist_patterns)} allowlist patterns from Gitleaks")

        except Exception as e:
            print(f"Error loading Gitleaks patterns: {e}")

    def _load_custom_patterns(self):
        """Add custom patterns for dark web specific formats"""
        custom_patterns = [
            # Combo list format (email:password)
            {
                'id': 'custom-combo-list',
                'name': 'Combo List Format',
                'regex': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\s*[:;,\s]+\s*[^\s]{4,}',
                'confidence': 'high',
                'category': 'credentials',
                'provider': 'combo_list',
                'description': 'Email:Password combo list format',
                'tags': ['darkweb', 'breach'],
                'source': 'custom'
            },
            # Database dump format (username|email|password|hash)
            {
                'id': 'custom-db-dump',
                'name': 'Database Dump Format',
                'regex': r'(?:username|user|email)[\s]*[:|=][\s]*([^\s|]+)[\s]*\|[\s]*(?:password|pass|pwd)[\s]*[:|=][\s]*([^\s|]+)',
                'confidence': 'high',
                'category': 'credentials',
                'provider': 'db_dump',
                'description': 'Database dump with delimited fields',
                'tags': ['darkweb', 'breach'],
                'source': 'custom'
            },
            # Bitcoin private keys (WIF format)
            {
                'id': 'custom-bitcoin-wif',
                'name': 'Bitcoin Private Key (WIF)',
                'regex': r'\b[5KL][1-9A-HJ-NP-Za-km-z]{50,51}\b',
                'confidence': 'high',
                'category': 'crypto_wallets',
                'provider': 'bitcoin',
                'description': 'Bitcoin Wallet Import Format private key',
                'tags': ['cryptocurrency', 'bitcoin'],
                'source': 'custom'
            },
            # Ethereum private keys
            {
                'id': 'custom-ethereum-key',
                'name': 'Ethereum Private Key',
                'regex': r'\b(?:0x)?[a-fA-F0-9]{64}\b',
                'confidence': 'medium',
                'category': 'crypto_wallets',
                'provider': 'ethereum',
                'description': 'Ethereum private key (64 hex chars)',
                'tags': ['cryptocurrency', 'ethereum'],
                'source': 'custom'
            },
            # SSH private key markers
            {
                'id': 'custom-ssh-key',
                'name': 'SSH Private Key',
                'regex': r'-----BEGIN (?:RSA|DSA|EC|OPENSSH) PRIVATE KEY-----',
                'confidence': 'high',
                'category': 'private_keys',
                'provider': 'ssh',
                'description': 'SSH private key header',
                'tags': ['ssh', 'private_key'],
                'source': 'custom'
            },
            # API key patterns (generic high-entropy)
            {
                'id': 'custom-api-key-generic',
                'name': 'Generic API Key',
                'regex': r'(?i)(?:api[_-]?key|apikey|api[_-]?secret|api[_-]?token|access[_-]?token|secret[_-]?key)[\s]*[=:][\s]*["\']?([a-zA-Z0-9_\-]{20,})["\']?',
                'confidence': 'medium',
                'category': 'api_keys',
                'provider': 'generic',
                'description': 'Generic API key pattern',
                'tags': ['api', 'key'],
                'source': 'custom'
            },
            # High-entropy string (from old fallback)
            {
                'id': 'custom-high-entropy-b64-hex',
                'name': 'High Entropy String (40+ chars)',
                'regex': r'\b[A-Za-z0-9_-]{40,}\b',
                'confidence': 'low',
                'category': 'api_keys',
                'provider': 'generic',
                'description': '40+ char hex or base64-like string',
                'tags': ['high_entropy', 'key'],
                'source': 'custom'
            },
            # MongoDB connection strings
            {
                'id': 'custom-mongodb-uri',
                'name': 'MongoDB Connection String',
                'regex': r'mongodb(?:\+srv)?://[^\s]+',
                'confidence': 'high',
                'category': 'connection_strings',
                'provider': 'mongodb',
                'description': 'MongoDB connection URI',
                'tags': ['database', 'mongodb'],
                'source': 'custom'
            },
            # PostgreSQL connection strings
            {
                'id': 'custom-postgresql-uri',
                'name': 'PostgreSQL Connection String',
                'regex': r'postgres(?:ql)?://[^\s]+',
                'confidence': 'high',
                'category': 'connection_strings',
                'provider': 'postgresql',
                'description': 'PostgreSQL connection URI',
                'tags': ['database', 'postgresql'],
                'source': 'custom'
            },
            # Redis connection strings
            {
                'id': 'custom-redis-uri',
                'name': 'Redis Connection String',
                'regex': r'redis://[^\s]+',
                'confidence': 'high',
                'category': 'connection_strings',
                'provider': 'redis',
                'description': 'Redis connection URI',
                'tags': ['database', 'redis'],
                'source': 'custom'
            },
        ]

        initial_count = len(self.patterns)
        for pattern in custom_patterns:
            self.patterns.append(pattern)
            self.categories[pattern['category']].append(pattern)

        new_patterns = len(self.patterns) - initial_count
        print(f"Loaded {new_patterns} custom dark web patterns (Total: {len(self.patterns)})")

    def _compile_patterns(self):
        """Compile all regex patterns for performance"""
        self.compiled_patterns = []

        for pattern in self.patterns:
            try:
                compiled = {
                    **pattern,
                    'compiled_regex': re.compile(pattern['regex'], re.IGNORECASE | re.MULTILINE)
                }
                self.compiled_patterns.append(compiled)
            except re.error as e:
                print(f"Warning: Failed to compile pattern {pattern['id']}: {e}")

        print(f"Compiled {len(self.compiled_patterns)} patterns for scanning")

    def _normalize_category(self, category: str) -> str:
        """Normalize category names"""
        category_map = {
            'api_key': 'api_keys',
            'apikey': 'api_keys',
            'credential': 'credentials',
            'password': 'credentials',
            'token': 'tokens',
            'secret': 'tokens',
            'private_key': 'private_keys',
            'privatekey': 'private_keys',
            'connection_string': 'connection_strings',
            'connectionstring': 'connection_strings',
            'cloud': 'cloud_credentials',
            'payment': 'payment',
            'crypto': 'crypto_wallets',
            'wallet': 'crypto_wallets',
        }

        normalized = category.lower().replace('-', '_').replace(' ', '_')
        return category_map.get(normalized, normalized)

    def _infer_category_from_id(self, pattern_id: str) -> str:
        """Infer category from Gitleaks pattern ID"""
        pattern_id_lower = pattern_id.lower()

        if 'key' in pattern_id_lower or 'secret' in pattern_id_lower:
            if 'private' in pattern_id_lower or 'ssh' in pattern_id_lower or 'rsa' in pattern_id_lower:
                return 'private_keys'
            return 'api_keys'
        elif 'token' in pattern_id_lower:
            return 'tokens'
        elif 'password' in pattern_id_lower or 'credential' in pattern_id_lower:
            return 'credentials'
        elif 'connection' in pattern_id_lower or 'uri' in pattern_id_lower or 'url' in pattern_id_lower:
            return 'connection_strings'
        elif 'bitcoin' in pattern_id_lower or 'crypto' in pattern_id_lower or 'wallet' in pattern_id_lower:
            return 'crypto_wallets'
        elif 'stripe' in pattern_id_lower or 'payment' in pattern_id_lower:
            return 'payment'
        else:
            return 'credentials'

    def _extract_provider_from_id(self, pattern_id: str) -> Optional[str]:
        """Extract provider name from Gitleaks pattern ID"""
        # Common pattern: provider-type (e.g., aws-access-key, github-token)
        parts = pattern_id.lower().split('-')
        if len(parts) > 0:
            provider = parts[0]
            # List of known providers
            known_providers = {
                'aws', 'azure', 'gcp', 'google', 'github', 'gitlab', 'stripe',
                'slack', 'twilio', 'mailchimp', 'sendgrid', 'facebook', 'twitter',
                'digitalocean', 'heroku', 'npm', 'pypi', 'docker', 'cloudflare',
                'okta', 'auth0', 'firebase', 'mongodb', 'postgres', 'mysql',
                'redis', 'openai', 'anthropic', 'huggingface', 'discord', 'telegram'
            }
            if provider in known_providers:
                return provider
        return None

    def scan_text(self, text: str, min_confidence: str = 'low', categories: Optional[List[str]] = None) -> List[CredentialMatch]:
        """
        Scan text for credential patterns

        Args:
            text: Text to scan
            min_confidence: Minimum confidence level (low, medium, high)
            categories: Optional list of categories to scan for

        Returns:
            List of CredentialMatch objects
        """
        if not self.loaded:
            self.load_patterns()

        matches: List[CredentialMatch] = []
        seen_matches: Set[tuple] = set()  # Deduplicate

        confidence_levels = {'low': 0, 'medium': 1, 'high': 2}
        min_level = confidence_levels.get(min_confidence, 0)

        # Select patterns to use
        patterns_to_scan = self.compiled_patterns
        if categories:
            patterns_to_scan = [p for p in self.compiled_patterns if p['category'] in categories]

        for pattern in patterns_to_scan:
            # Check confidence level
            pattern_level = confidence_levels.get(pattern.get('confidence', 'medium'), 1)
            if pattern_level < min_level:
                continue

            # Keyword pre-filtering for performance (if keywords are specified)
            if 'keywords' in pattern and pattern['keywords']:
                if not any(kw.lower() in text.lower() for kw in pattern['keywords']):
                    continue

            try:
                for match in pattern['compiled_regex'].finditer(text):
                    value = match.group(0)
                    start_pos = match.start()
                    end_pos = match.end()

                    # Check allowlist
                    if self._is_allowlisted(value):
                        continue

                    # Deduplicate
                    match_key = (pattern['id'], value, start_pos)
                    if match_key in seen_matches:
                        continue
                    seen_matches.add(match_key)

                    # Calculate entropy for this match
                    entropy = self.calculate_entropy(value)

                    credential_match = CredentialMatch(
                        pattern_name=pattern['name'],
                        pattern_id=pattern['id'],
                        value=value,
                        start_pos=start_pos,
                        end_pos=end_pos,
                        confidence=pattern['confidence'],
                        category=pattern['category'],
                        provider=pattern.get('provider'),
                        entropy=entropy,
                        source_tool='credential_patterns',
                        description=pattern.get('description'),
                        tags=pattern.get('tags')
                    )

                    matches.append(credential_match)

            except Exception as e:
                print(f"Error scanning with pattern {pattern['id']}: {e}")

        return matches

    def _is_allowlisted(self, value: str) -> bool:
        """Check if value matches any allowlist pattern"""
        for pattern in self.allowlist_patterns:
            if pattern.search(value):
                return True
        return False

    @staticmethod
    def calculate_entropy(data: str) -> float:
        """Calculate Shannon entropy of a string"""
        if not data:
            return 0.0

        # Count character frequencies
        freq = {}
        for char in data:
            freq[char] = freq.get(char, 0) + 1

        # Calculate entropy
        entropy = 0.0
        data_len = len(data)

        for count in freq.values():
            probability = count / data_len
            entropy -= probability * math.log2(probability)

        return entropy

    def get_stats(self) -> Dict:
        """Get statistics about loaded patterns"""
        if not self.loaded:
            self.load_patterns()

        category_counts = {cat: len(patterns) for cat, patterns in self.categories.items()}
        source_counts = defaultdict(int)

        for pattern in self.patterns:
            source_counts[pattern['source']] += 1

        return {
            'total_patterns': len(self.patterns),
            'compiled_patterns': len(self.compiled_patterns),
            'allowlist_patterns': len(self.allowlist_patterns),
            'categories': category_counts,
            'sources': dict(source_counts)
        }


# Global instance
_engine = None

def get_engine() -> CredentialPatternEngine:
    """Get the global credential pattern engine instance"""
    global _engine
    if _engine is None:
        _engine = CredentialPatternEngine()
        _engine.load_patterns()
    return _engine


# Convenience functions
def scan_text(text: str, min_confidence: str = 'low', categories: Optional[List[str]] = None) -> List[CredentialMatch]:
    """Scan text for credentials using the global engine"""
    return get_engine().scan_text(text, min_confidence, categories)


def calculate_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string"""
    return CredentialPatternEngine.calculate_entropy(data)


def get_pattern_stats() -> Dict:
    """Get pattern statistics"""
    return get_engine().get_stats()
