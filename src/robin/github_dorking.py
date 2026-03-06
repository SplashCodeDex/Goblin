"""
GitHub Dorking Engine
Advanced credential hunting via GitHub code search dorks and public gist scanning.
"""

import time
import logging
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from .config import GITHUB_TOKEN

logger = logging.getLogger(__name__)

# GitHub API base
GITHUB_API = "https://api.github.com"
GITHUB_RATE_LIMIT_PAUSE = 2  # seconds between requests to avoid 403
GITHUB_REQUEST_TIMEOUT = 15


# ─── Dork categories ────────────────────────────────────────────────────
# Each dork is a raw GitHub code-search query string.
# We split them by category for selective hunting.

DORK_CATEGORIES: Dict[str, List[str]] = {
    "api_keys": [
        '"AKIA" filename:.env',
        '"AKIA" filename:.bash_history',
        '"AKIA" filename:credentials',
        '"sk_live_" filename:.env',
        '"rk_live_" filename:.env',
        '"SG." filename:.env',
        '"xoxb-" filename:.env',
        '"xoxp-" filename:.env',
        '"xoxa-" filename:.env',
        '"ghp_" filename:.env',
        '"gho_" filename:.env',
        '"ghs_" filename:.env',
        '"github_pat_" filename:.env',
        '"glpat-" filename:.env',
        '"sk-ant-" filename:.env',
        '"AIza" filename:.env',
        '"npm_" filename:.npmrc',
        '"_authToken" filename:.npmrc',
        '"dop_v1_" filename:.env',
        '"key-" filename:.env extension:env mailgun',
        '"api_key" filename:.env',
        '"apikey" filename:.env',
        '"access_token" filename:.env',
        '"secret_key" filename:.env',
    ],
    "cloud_credentials": [
        '"AWS_ACCESS_KEY_ID" filename:.env',
        '"AWS_SECRET_ACCESS_KEY" filename:.env',
        '"AZURE_CLIENT_SECRET" filename:.env',
        '"GOOGLE_APPLICATION_CREDENTIALS" filename:.env',
        '"GOOGLE_PRIVATE_KEY" filename:.env',
        '"DefaultEndpointsProtocol" filename:.env',
        '"AccountKey=" filename:.env',
        '"DIGITALOCEAN_ACCESS_TOKEN" filename:.env',
        '"HEROKU_API_KEY" filename:.env',
        '"CLOUDFLARE_API_KEY" filename:.env',
        '"CLOUDFLARE_API_TOKEN" filename:.env',
        '"FIREBASE_API_KEY" filename:.env',
        '"FIREBASE_SERVICE_ACCOUNT" filename:.json',
        '"DO_API_KEY" filename:.env',
        '"LINODE_TOKEN" filename:.env',
        '"VULTR_API_KEY" filename:.env',
    ],
    "database_credentials": [
        '"DB_PASSWORD" filename:.env',
        '"DATABASE_URL" filename:.env',
        '"MYSQL_ROOT_PASSWORD" filename:docker-compose.yml',
        '"POSTGRES_PASSWORD" filename:docker-compose.yml',
        '"MONGO_INITDB_ROOT_PASSWORD" filename:docker-compose.yml',
        '"mongodb+srv://" filename:.env',
        '"postgresql://" filename:.env',
        '"mysql://" filename:.env',
        '"redis://" filename:.env',
        '"REDIS_PASSWORD" filename:.env',
        'password filename:wp-config.php',
        '"DB_PASS" filename:.env',
        '"PGPASSWORD" filename:.env',
    ],
    "private_keys": [
        '"BEGIN RSA PRIVATE KEY" filename:id_rsa',
        '"BEGIN OPENSSH PRIVATE KEY"',
        '"BEGIN PGP PRIVATE KEY BLOCK"',
        '"BEGIN EC PRIVATE KEY"',
        '"BEGIN DSA PRIVATE KEY"',
        'filename:id_rsa -id_rsa.pub',
        'filename:.pem "PRIVATE KEY"',
        'filename:hub oauth_token',
        'filename:robomongo.json',
    ],
    "oauth_tokens": [
        '"client_secret" filename:.json',
        '"client_secret" filename:client_secrets.json',
        '"installed" filename:client_secrets.json',
        '"refresh_token" filename:.json',
        '"access_token" filename:.json',
        '"oauth_token"',
        'filename:.htpasswd',
        'filename:.netrc password',
    ],
    "messaging_webhooks": [
        '"hooks.slack.com/services" filename:.env',
        '"discord.com/api/webhooks" filename:.env',
        '"discordapp.com/api/webhooks" filename:.env',
        '"SLACK_WEBHOOK_URL" filename:.env',
        '"TELEGRAM_BOT_TOKEN" filename:.env',
        '"TWILIO_AUTH_TOKEN" filename:.env',
        '"TWILIO_ACCOUNT_SID" filename:.env',
        '"SENDGRID_API_KEY" filename:.env',
        '"MAILGUN_API_KEY" filename:.env',
    ],
    "payment_credentials": [
        '"sk_live" filename:.env stripe',
        '"pk_live" filename:.env stripe',
        '"PAYPAL_CLIENT_SECRET" filename:.env',
        '"PAYPAL_SECRET" filename:.env',
        '"BRAINTREE_PRIVATE_KEY" filename:.env',
        '"SQUARE_ACCESS_TOKEN" filename:.env',
    ],
    "ci_cd_secrets": [
        'filename:.travis.yml "secure:"',
        'filename:circle.yml "environment"',
        '"DOCKER_PASSWORD" filename:.env',
        '"DOCKER_AUTH_CONFIG"',
        '"JENKINS_USER_ID" filename:.env',
        '"JENKINS_API_TOKEN" filename:.env',
        '"SONAR_TOKEN" filename:.env',
    ],
    "email_credentials": [
        '"SMTP_PASSWORD" filename:.env',
        '"MAIL_PASSWORD" filename:.env',
        '"EMAIL_HOST_PASSWORD" filename:.env',
        '"smtp://" filename:.env',
        '"imap_password" filename:.env',
    ],
    "miscellaneous": [
        'filename:.bash_history "password"',
        'filename:.bashrc "export" "password"',
        'filename:.zsh_history "password"',
        'filename:shadow path:etc',
        'filename:passwd path:etc',
        'filename:credentials.xml',
        'filename:settings.py "SECRET_KEY"',
        'filename:config.py "SECRET"',
        '"JWT_SECRET" filename:.env',
        '"SESSION_SECRET" filename:.env',
        '"ENCRYPTION_KEY" filename:.env',
    ],
}


def _get_headers() -> Dict[str, str]:
    """Build GitHub API request headers."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


def _rate_limited_get(url: str, params: dict, timeout: int = GITHUB_REQUEST_TIMEOUT) -> Optional[requests.Response]:
    """GET request with rate-limit awareness."""
    try:
        resp = requests.get(url, headers=_get_headers(), params=params, timeout=timeout)
        # If we hit the secondary rate limit, back off
        if resp.status_code == 403:
            retry_after = int(resp.headers.get('Retry-After', GITHUB_RATE_LIMIT_PAUSE * 5))
            logger.warning(f"GitHub rate limit hit. Waiting {retry_after}s...")
            time.sleep(retry_after)
            resp = requests.get(url, headers=_get_headers(), params=params, timeout=timeout)
        return resp
    except Exception as e:
        logger.error(f"GitHub request error: {e}")
        return None


# ─── Core search functions ───────────────────────────────────────────────

def search_single_dork(dork: str, limit: int = 10) -> List[Dict]:
    """
    Execute a single GitHub code-search dork.

    Returns:
        List of result dicts with 'title', 'link', 'snippet', 'source', 'dork'.
    """
    results = []
    resp = _rate_limited_get(
        f"{GITHUB_API}/search/code",
        params={"q": dork, "per_page": min(limit, 100), "sort": "indexed"},
    )
    if resp is None or resp.status_code != 200:
        return results

    for item in resp.json().get("items", []):
        repo = item.get("repository", {})
        results.append({
            "title": f"{repo.get('full_name', '?')} — {item.get('name', '?')}",
            "link": item.get("html_url", ""),
            "snippet": f"Match in {item.get('path', '?')}",
            "source": "github_dorks",
            "dork": dork,
            "repo_url": repo.get("html_url", ""),
            "file_path": item.get("path", ""),
        })

    return results


def search_dorks(
    categories: Optional[List[str]] = None,
    custom_dorks: Optional[List[str]] = None,
    limit_per_dork: int = 5,
    max_workers: int = 3,
) -> Dict[str, List[Dict]]:
    """
    Run multiple GitHub dorks concurrently.

    Args:
        categories: List of category names to search (None = all).
        custom_dorks: Additional custom dork strings.
        limit_per_dork: Max results per dork query.
        max_workers: Concurrent worker threads (keep low to avoid rate limits).

    Returns:
        Dict mapping dork string → list of result dicts.
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN required for GitHub dorking")
        return {}

    # Collect dorks to run
    dorks: List[str] = []
    selected_cats = categories or list(DORK_CATEGORIES.keys())
    for cat in selected_cats:
        if cat in DORK_CATEGORIES:
            dorks.extend(DORK_CATEGORIES[cat])
    if custom_dorks:
        dorks.extend(custom_dorks)

    # De-duplicate
    dorks = list(dict.fromkeys(dorks))

    results: Dict[str, List[Dict]] = {}

    def _run_dork(dork: str) -> tuple:
        time.sleep(GITHUB_RATE_LIMIT_PAUSE)  # respect rate limits
        return dork, search_single_dork(dork, limit=limit_per_dork)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(_run_dork, d): d for d in dorks}
        for future in as_completed(futures):
            try:
                dork, hits = future.result()
                if hits:
                    results[dork] = hits
            except Exception as e:
                logger.error(f"Dork execution error: {e}")

    return results


# ─── Gist search ─────────────────────────────────────────────────────────

def search_gists(query: str, limit: int = 20) -> List[Dict]:
    """
    Search public GitHub Gists for credential leaks.

    Args:
        query: Search term (e.g. "password", "api_key", a domain, etc.)
        limit: Maximum results to return.

    Returns:
        List of gist result dicts.
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN required for gist search")
        return []

    results = []
    resp = _rate_limited_get(
        f"{GITHUB_API}/gists/public",
        params={"per_page": min(limit, 100)},
    )
    if resp is None or resp.status_code != 200:
        return results

    query_lower = query.lower()
    for gist in resp.json():
        # Check description and filenames for relevance
        description = (gist.get("description") or "").lower()
        files = gist.get("files", {})
        file_names = " ".join(files.keys()).lower()

        if query_lower in description or query_lower in file_names:
            file_info = []
            for fname, fdata in files.items():
                file_info.append({
                    "filename": fname,
                    "language": fdata.get("language"),
                    "raw_url": fdata.get("raw_url"),
                    "size": fdata.get("size"),
                })

            results.append({
                "title": gist.get("description") or f"Gist {gist.get('id', '?')}",
                "link": gist.get("html_url", ""),
                "snippet": f"{len(files)} file(s): {', '.join(files.keys())}",
                "source": "github_gists",
                "gist_id": gist.get("id"),
                "owner": (gist.get("owner") or {}).get("login", "anonymous"),
                "files": file_info,
                "created_at": gist.get("created_at"),
                "updated_at": gist.get("updated_at"),
            })

    return results[:limit]


# ─── Convenience / statistics ────────────────────────────────────────────

def get_dork_categories() -> Dict[str, int]:
    """Return available dork categories and their query counts."""
    return {cat: len(dorks) for cat, dorks in DORK_CATEGORIES.items()}


def get_total_dork_count() -> int:
    """Total number of dork queries available."""
    return sum(len(d) for d in DORK_CATEGORIES.values())
