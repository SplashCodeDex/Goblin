"""
TruffleHog3 Integration Engine
Provides live credential verification and entropy-based detection
"""

import os
import re
import json
import hashlib
import logging
from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import math

try:
    import requests as _requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

logger = logging.getLogger(__name__)

# Verification timeout for each HTTP call (seconds)
VERIFICATION_TIMEOUT = 10

# TruffleHog3 imports (with fallback if not installed)
try:
    import trufflehog3
    TRUFFLEHOG_AVAILABLE = True
except ImportError:
    TRUFFLEHOG_AVAILABLE = False
    print("Warning: truffleHog3 not installed. Verification features will be disabled.")


@dataclass
class TruffleHogFinding:
    """Represents a finding from TruffleHog"""
    detector_type: str
    detector_name: str
    raw_value: str
    redacted_value: str
    verified: bool  # True if key is verified active, False if inactive, None if unknown
    verification_error: Optional[str] = None
    start_pos: int = 0
    end_pos: int = 0
    entropy: Optional[float] = None
    metadata: Optional[Dict] = None
    source_tool: str = "trufflehog"


@dataclass
class HighEntropyString:
    """Represents a high-entropy string detected"""
    value: str
    entropy: float
    start_pos: int
    end_pos: int
    string_type: str  # base64, hex, random
    source_tool: str = "trufflehog_entropy"


class TruffleHogEngine:
    """Wrapper for TruffleHog3 functionality with caching"""

    def __init__(self, enable_verification: bool = False, cache_ttl_hours: int = 24):
        self.enable_verification = enable_verification
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.verification_cache: Dict[str, Dict] = {}
        self.cache_file = Path(__file__).parent / ".trufflehog_cache.json"
        self._load_cache()

        # Entropy thresholds
        self.base64_entropy_threshold = 4.5
        self.hex_entropy_threshold = 3.0

    def _load_cache(self):
        """Load verification cache from disk"""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Filter out expired entries
                    now = datetime.now()
                    self.verification_cache = {
                        k: v for k, v in cache_data.items()
                        if datetime.fromisoformat(v['timestamp']) + self.cache_ttl > now
                    }
            except Exception as e:
                print(f"Error loading verification cache: {e}")
                self.verification_cache = {}

    def _save_cache(self):
        """Save verification cache to disk"""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self.verification_cache, f)
        except Exception as e:
            print(f"Error saving verification cache: {e}")

    def _cache_key(self, secret_type: str, secret_value: str) -> str:
        """Generate cache key for a credential"""
        # Hash the secret value to avoid storing it in plain text
        value_hash = hashlib.sha256(secret_value.encode()).hexdigest()
        return f"{secret_type}:{value_hash}"

    def scan_text(self, text: str, max_depth: int = 1000) -> List[TruffleHogFinding]:
        """
        Scan text using TruffleHog detectors

        Args:
            text: Text to scan
            max_depth: Maximum depth for regex scanning

        Returns:
            List of TruffleHogFinding objects
        """
        if not TRUFFLEHOG_AVAILABLE:
            return []

        findings: List[TruffleHogFinding] = []

        try:
            # TruffleHog3 uses regex-based detection
            # We'll implement a simplified version that mimics the core functionality
            # For production use, you'd integrate with the actual TruffleHog3 library

            # Common secret patterns used by TruffleHog
            detector_patterns = self._get_detector_patterns()

            for detector_name, pattern_info in detector_patterns.items():
                pattern = pattern_info['pattern']
                detector_type = pattern_info['type']

                for match in re.finditer(pattern, text, re.IGNORECASE):
                    raw_value = match.group(0)
                    redacted_value = self._redact_value(raw_value)

                    # Check cache first
                    cache_key = self._cache_key(detector_name, raw_value)
                    cached_result = self.verification_cache.get(cache_key)

                    if cached_result:
                        verified = cached_result.get('verified', None)
                        verification_error = cached_result.get('error')
                    elif self.enable_verification:
                        # Perform live verification
                        verified, verification_error = self._verify_credential(detector_name, raw_value)
                        # Cache the result
                        self.verification_cache[cache_key] = {
                            'verified': verified,
                            'error': verification_error,
                            'timestamp': datetime.now().isoformat()
                        }
                        self._save_cache()
                    else:
                        verified = None
                        verification_error = None

                    finding = TruffleHogFinding(
                        detector_type=detector_type,
                        detector_name=detector_name,
                        raw_value=raw_value,
                        redacted_value=redacted_value,
                        verified=verified,
                        verification_error=verification_error,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        entropy=self._calculate_entropy(raw_value),
                        metadata={'pattern_matched': detector_name}
                    )

                    findings.append(finding)

        except Exception as e:
            print(f"Error scanning with TruffleHog: {e}")

        return findings

    def _get_detector_patterns(self) -> Dict[str, Dict]:
        """Get detector patterns (simplified set of common detectors)"""
        return {
            'AWS Access Key': {
                'pattern': r'AKIA[0-9A-Z]{16}',
                'type': 'cloud_credentials'
            },
            'AWS Secret Key': {
                'pattern': r'(?i)aws(.{0,20})?["\']?[0-9a-zA-Z/+]{40}["\']?',
                'type': 'cloud_credentials'
            },
            'GitHub Token': {
                'pattern': r'gh[pousr]_[A-Za-z0-9_]{36,}',
                'type': 'api_keys'
            },
            'GitHub PAT': {
                'pattern': r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}',
                'type': 'api_keys'
            },
            'Stripe API Key': {
                'pattern': r'(?:r|s)k_live_[0-9a-zA-Z]{24,}',
                'type': 'payment'
            },
            'OpenAI API Key': {
                'pattern': r'sk-[a-zA-Z0-9]{48}',
                'type': 'api_keys'
            },
            'Anthropic API Key': {
                'pattern': r'sk-ant-[a-zA-Z0-9\-]{95,}',
                'type': 'api_keys'
            },
            'Google API Key': {
                'pattern': r'AIza[0-9A-Za-z\-_]{35}',
                'type': 'api_keys'
            },
            'Azure Connection String': {
                'pattern': r'DefaultEndpointsProtocol=https;AccountName=[^;]+;AccountKey=[^;]+',
                'type': 'connection_strings'
            },
            'Slack Token': {
                'pattern': r'xox[baprs]-[0-9]{10,13}-[0-9]{10,13}-[a-zA-Z0-9]{24,}',
                'type': 'api_keys'
            },
            'Slack Webhook': {
                'pattern': r'https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+',
                'type': 'webhooks'
            },
            'Twilio API Key': {
                'pattern': r'SK[0-9a-fA-F]{32}',
                'type': 'api_keys'
            },
            'SendGrid API Key': {
                'pattern': r'SG\.[a-zA-Z0-9_\-]{22}\.[a-zA-Z0-9_\-]{43}',
                'type': 'api_keys'
            },
            'Mailgun API Key': {
                'pattern': r'key-[0-9a-zA-Z]{32}',
                'type': 'api_keys'
            },
            'DigitalOcean Token': {
                'pattern': r'dop_v1_[a-f0-9]{64}',
                'type': 'api_keys'
            },
            'Heroku API Key': {
                'pattern': r'[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}',
                'type': 'api_keys'
            },
            'Discord Bot Token': {
                'pattern': r'[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27}',
                'type': 'api_keys'
            },
            'Discord Webhook': {
                'pattern': r'https://discord(?:app)?\.com/api/webhooks/\d+/[A-Za-z0-9_\-]+',
                'type': 'webhooks'
            },
            'NPM Token': {
                'pattern': r'npm_[a-zA-Z0-9]{36}',
                'type': 'api_keys'
            },
            'PyPI Token': {
                'pattern': r'pypi-AgEIcHlwaS5vcmc[A-Za-z0-9\-_]{70,}',
                'type': 'api_keys'
            },
            'GitLab Token': {
                'pattern': r'glpat-[a-zA-Z0-9\-_]{20}',
                'type': 'api_keys'
            },
            'Firebase API Key': {
                'pattern': r'(?i)firebase[_\s-]*(?:api)?[_\s-]*key["\s:=]+([a-zA-Z0-9_\-]{39})',
                'type': 'api_keys'
            },
            'JWT Token': {
                'pattern': r'eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*',
                'type': 'tokens'
            },
            'RSA Private Key': {
                'pattern': r'-----BEGIN RSA PRIVATE KEY-----',
                'type': 'private_keys'
            },
            'SSH Private Key': {
                'pattern': r'-----BEGIN OPENSSH PRIVATE KEY-----',
                'type': 'private_keys'
            },
            'PGP Private Key': {
                'pattern': r'-----BEGIN PGP PRIVATE KEY BLOCK-----',
                'type': 'private_keys'
            },
        }

    # ─── Verifier registry ────────────────────────────────────────────
    # Maps detector_name → verifier method name
    _VERIFIER_MAP = {
        'AWS Access Key':       '_verify_aws_key',
        'AWS Secret Key':       '_verify_aws_key',
        'GitHub Token':         '_verify_github_token',
        'GitHub PAT':           '_verify_github_token',
        'Slack Token':          '_verify_slack_token',
        'Stripe API Key':       '_verify_stripe_key',
        'SendGrid API Key':     '_verify_sendgrid_key',
        'Twilio API Key':       '_verify_twilio_key',
        'Mailgun API Key':      '_verify_mailgun_key',
        'GitLab Token':         '_verify_gitlab_token',
        'DigitalOcean Token':   '_verify_digitalocean_token',
        'Heroku API Key':       '_verify_heroku_key',
        'NPM Token':            '_verify_npm_token',
        'Cloudflare API Key':   '_verify_cloudflare_token',
        'Firebase API Key':     '_verify_firebase_key',
        'Discord Bot Token':    '_verify_discord_token',
        'OpenAI API Key':       '_verify_openai_key',
        'Google API Key':       '_verify_gemini_key',
        'Anthropic API Key':    '_verify_anthropic_key',
    }

    def _verify_credential(self, detector_name: str, raw_value: str) -> Tuple[Optional[bool], Optional[str]]:
        """
        Verify if a credential is still active using the verifier registry.

        Returns:
            (verified: bool or None, error: str or None)
            - True: Credential is verified active
            - False: Credential is verified inactive/invalid
            - None: Could not verify (unsupported type or error)
        """
        if not self.enable_verification:
            return None, "Verification disabled for security"

        if not REQUESTS_AVAILABLE:
            return None, "requests library not installed — required for live verification"

        method_name = self._VERIFIER_MAP.get(detector_name)
        if method_name is None:
            return None, f"Live verification not supported for {detector_name}"

        try:
            verifier = getattr(self, method_name)
            return verifier(raw_value)
        except Exception as e:
            logger.error(f"Verification error for {detector_name}: {e}")
            return None, str(e)

    def verify_batch(self, credentials: List[Dict[str, str]], max_workers: int = 5) -> List[Dict]:
        """
        Verify multiple credentials concurrently.

        Args:
            credentials: List of dicts with 'detector_name' and 'value' keys
            max_workers: Max concurrent verification threads

        Returns:
            List of dicts with 'detector_name', 'value', 'verified', 'error' keys
        """
        results = []

        def _verify_one(cred: Dict[str, str]) -> Dict:
            det = cred.get('detector_name', 'unknown')
            val = cred.get('value', '')
            verified, error = self._verify_credential(det, val)
            return {
                'detector_name': det,
                'value': self._redact_value(val),
                'verified': verified,
                'error': error
            }

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_verify_one, c): c for c in credentials}
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception as e:
                    cred = futures[future]
                    results.append({
                        'detector_name': cred.get('detector_name', 'unknown'),
                        'value': self._redact_value(cred.get('value', '')),
                        'verified': None,
                        'error': str(e)
                    })

        return results

    # ─── Individual verifiers ────────────────────────────────────────

    def _verify_aws_key(self, raw_value: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify an AWS key using STS GetCallerIdentity if boto3 is available."""
        try:
            import boto3
            from botocore.exceptions import ClientError, NoCredentialsError

            # If it looks like an access key ID (AKIA...), we can only verify
            # if we also find the secret key nearby. Return None for partial.
            if raw_value.startswith('AKIA') and len(raw_value) == 20:
                return None, "Access key ID found; need secret key for verification"

            # If we have what looks like a 40-char secret key, try with env access key
            access_key = os.getenv('AWS_ACCESS_KEY_ID')
            if access_key and len(raw_value) == 40:
                client = boto3.client(
                    'sts',
                    aws_access_key_id=access_key,
                    aws_secret_access_key=raw_value,
                )
                try:
                    client.get_caller_identity()
                    return True, None
                except ClientError:
                    return False, "Invalid AWS credentials"

            return None, "Requires both access key and secret key to verify AWS"
        except ImportError:
            return None, "boto3 not installed"
        except Exception as e:
            return None, str(e)

    def _verify_github_token(self, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a GitHub personal access token or fine-grained token."""
        try:
            resp = _requests.get(
                'https://api.github.com/user',
                headers={'Authorization': f'token {token}', 'Accept': 'application/vnd.github.v3+json'},
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid credentials"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_slack_token(self, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Slack bot/user/app token via auth.test."""
        try:
            resp = _requests.post(
                'https://slack.com/api/auth.test',
                headers={'Authorization': f'Bearer {token}'},
                timeout=VERIFICATION_TIMEOUT
            )
            data = resp.json()
            if data.get('ok'):
                return True, None
            return False, data.get('error', 'invalid_auth')
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_stripe_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Stripe secret/restricted key via charges endpoint."""
        try:
            resp = _requests.get(
                'https://api.stripe.com/v1/charges?limit=1',
                auth=(key, ''),
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid Stripe key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_sendgrid_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a SendGrid API key via scopes endpoint."""
        try:
            resp = _requests.get(
                'https://api.sendgrid.com/v3/scopes',
                headers={'Authorization': f'Bearer {key}'},
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code in (401, 403):
                return False, "Invalid SendGrid key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_twilio_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Twilio API key — needs SID:Token pair or standalone key check."""
        try:
            # Twilio API keys (SK...) can be tested against the keys endpoint
            resp = _requests.get(
                'https://api.twilio.com/2010-04-01/Accounts.json',
                auth=(key, ''),
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid Twilio key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_mailgun_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Mailgun API key via domains endpoint."""
        try:
            resp = _requests.get(
                'https://api.mailgun.net/v3/domains',
                auth=('api', key),
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code in (401, 403):
                return False, "Invalid Mailgun key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_gitlab_token(self, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a GitLab personal access token."""
        try:
            resp = _requests.get(
                'https://gitlab.com/api/v4/user',
                headers={'PRIVATE-TOKEN': token},
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid GitLab token"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_digitalocean_token(self, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a DigitalOcean personal access token."""
        try:
            resp = _requests.get(
                'https://api.digitalocean.com/v2/account',
                headers={'Authorization': f'Bearer {token}'},
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid DigitalOcean token"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_heroku_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Heroku API key."""
        try:
            resp = _requests.get(
                'https://api.heroku.com/account',
                headers={
                    'Authorization': f'Bearer {key}',
                    'Accept': 'application/vnd.heroku+json; version=3'
                },
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid Heroku key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_npm_token(self, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify an NPM publish token."""
        try:
            resp = _requests.get(
                'https://registry.npmjs.org/-/whoami',
                headers={'Authorization': f'Bearer {token}'},
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid NPM token"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_cloudflare_token(self, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Cloudflare API token."""
        try:
            resp = _requests.get(
                'https://api.cloudflare.com/client/v4/user/tokens/verify',
                headers={'Authorization': f'Bearer {token}'},
                timeout=VERIFICATION_TIMEOUT
            )
            data = resp.json()
            if data.get('success'):
                return True, None
            return False, "Invalid Cloudflare token"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_firebase_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Firebase API key by checking identity toolkit."""
        try:
            resp = _requests.post(
                f'https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={key}',
                json={'idToken': 'test'},
                timeout=VERIFICATION_TIMEOUT
            )
            # A valid API key returns 400 with INVALID_ID_TOKEN (key works, token doesn't)
            # An invalid API key returns 403 with API_KEY_INVALID
            if resp.status_code == 400:
                error_msg = resp.json().get('error', {}).get('message', '')
                if 'API_KEY_INVALID' not in error_msg:
                    return True, None  # Key is valid (got a different error)
                return False, "Invalid Firebase API key"
            elif resp.status_code == 403:
                return False, "Invalid or restricted Firebase API key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_discord_token(self, token: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Discord bot token."""
        try:
            resp = _requests.get(
                'https://discord.com/api/v10/users/@me',
                headers={'Authorization': f'Bot {token}'},
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid Discord token"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_openai_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify an OpenAI API key."""
        try:
            resp = _requests.get(
                'https://api.openai.com/v1/models',
                headers={'Authorization': f'Bearer {key}'},
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid OpenAI key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_gemini_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify a Google Gemini / AI Studio API key."""
        try:
            resp = _requests.get(
                f'https://generativelanguage.googleapis.com/v1beta/models?key={key}',
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 400:
                return False, "Invalid Gemini key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def _verify_anthropic_key(self, key: str) -> Tuple[Optional[bool], Optional[str]]:
        """Verify an Anthropic API key."""
        try:
            resp = _requests.get(
                'https://api.anthropic.com/v1/models',
                headers={
                    'x-api-key': key,
                    'anthropic-version': '2023-06-01'
                },
                timeout=VERIFICATION_TIMEOUT
            )
            if resp.status_code == 200:
                return True, None
            elif resp.status_code == 401:
                return False, "Invalid Anthropic key"
            return None, f"Unexpected response: {resp.status_code}"
        except Exception as e:
            return None, f"Connection error: {e}"

    def entropy_scan(self, text: str, min_length: int = 20, max_length: int = 100) -> List[HighEntropyString]:
        """
        Scan for high-entropy strings (potential secrets)

        Args:
            text: Text to scan
            min_length: Minimum string length to consider
            max_length: Maximum string length to consider

        Returns:
            List of HighEntropyString objects
        """
        high_entropy_strings: List[HighEntropyString] = []

        # Find base64-like strings
        base64_pattern = r'[A-Za-z0-9+/]{20,}={0,2}'
        for match in re.finditer(base64_pattern, text):
            value = match.group(0)
            if min_length <= len(value) <= max_length:
                entropy = self._calculate_entropy(value)
                if entropy >= self.base64_entropy_threshold:
                    high_entropy_strings.append(HighEntropyString(
                        value=value,
                        entropy=entropy,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        string_type='base64'
                    ))

        # Find hex strings
        hex_pattern = r'[a-fA-F0-9]{40,}'
        for match in re.finditer(hex_pattern, text):
            value = match.group(0)
            if min_length <= len(value) <= max_length:
                entropy = self._calculate_entropy(value)
                if entropy >= self.hex_entropy_threshold:
                    high_entropy_strings.append(HighEntropyString(
                        value=value,
                        entropy=entropy,
                        start_pos=match.start(),
                        end_pos=match.end(),
                        string_type='hex'
                    ))

        return high_entropy_strings

    @staticmethod
    def _calculate_entropy(data: str) -> float:
        """Calculate Shannon entropy of a string"""
        if not data:
            return 0.0

        freq = {}
        for char in data:
            freq[char] = freq.get(char, 0) + 1

        entropy = 0.0
        data_len = len(data)

        for count in freq.values():
            probability = count / data_len
            entropy -= probability * math.log2(probability)

        return entropy

    @staticmethod
    def _redact_value(value: str) -> str:
        """Redact a credential value for safe display"""
        if len(value) <= 8:
            return '*' * len(value)
        # Show first 4 and last 4 characters
        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"

    def clear_cache(self):
        """Clear the verification cache"""
        self.verification_cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()

    def get_cache_stats(self) -> Dict:
        """Get statistics about the verification cache"""
        return {
            'total_entries': len(self.verification_cache),
            'cache_file': str(self.cache_file),
            'cache_ttl_hours': self.cache_ttl.total_seconds() / 3600,
            'supported_verifiers': list(self._VERIFIER_MAP.keys()),
            'verifier_count': len(self._VERIFIER_MAP)
        }


# Global instance
_engine = None

def get_engine(enable_verification: bool = False) -> TruffleHogEngine:
    """Get the global TruffleHog engine instance"""
    global _engine
    if _engine is None:
        _engine = TruffleHogEngine(enable_verification=enable_verification)
    return _engine


# Convenience functions
def scan_text(text: str) -> List[TruffleHogFinding]:
    """Scan text for credentials using TruffleHog detectors"""
    return get_engine().scan_text(text)


def entropy_scan(text: str, min_length: int = 20) -> List[HighEntropyString]:
    """Scan for high-entropy strings"""
    return get_engine().entropy_scan(text, min_length=min_length)


def verify_credential(detector_name: str, raw_value: str) -> tuple[Optional[bool], Optional[str]]:
    """Verify if a credential is still active"""
    engine = get_engine(enable_verification=True)
    return engine._verify_credential(detector_name, raw_value)
