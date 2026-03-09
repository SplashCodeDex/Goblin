import time
import logging
import io
import zipfile
import datetime
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import requests

from .config import GITHUB_TOKEN
from .credential_patterns import scan_text as scan_text_patterns
from .trufflehog_engine import get_engine
GITHUB_API = "https://api.github.com"
GITHUB_RATE_LIMIT_PAUSE = 2
GITHUB_REQUEST_TIMEOUT = 15

def _get_headers() -> Dict[str, str]:
    """Build GitHub API request headers."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def _rate_limited_get(url: str, params: Optional[dict] = None, timeout: int = GITHUB_REQUEST_TIMEOUT, stream: bool = False) -> Optional[requests.Response]:
    """GET request with aggressive rate-limit awareness."""
    try:
        resp = requests.get(url, headers=_get_headers(), params=params, timeout=timeout, stream=stream)

        # If we hit secondary rate limit or auth issues
        if resp.status_code == 403 or resp.status_code == 429:
            retry_after = int(resp.headers.get('Retry-After', GITHUB_RATE_LIMIT_PAUSE * 5))
            logger.warning(f"GitHub rate limit hit on {url}. Waiting {retry_after}s...")
            time.sleep(retry_after)
            resp = requests.get(url, headers=_get_headers(), params=params, timeout=timeout, stream=stream)

        return resp
    except Exception as e:
        logger.error(f"GitHub request error on {url}: {e}")
        return None

def find_susceptible_repos(limit: int = 20) -> List[Dict]:
    """
    Identifies repositories that likely have leaky CI logs.
    We target repos pushed recently (to avoid 410 Gone logs) that use GitHub Actions.
    """
    if not GITHUB_TOKEN:
        logger.error("GITHUB_TOKEN required for CI/CD hunting")
        return []

    # Look for repos active in the last 45 days containing workflow files or .env echoes
    cutoff_date = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=45)).strftime("%Y-%m-%d")

    # We look for bad habits in workflow files.
    # We can expand this list over time.
    dorks = [
        f'path:.github/workflows pushed:>{cutoff_date} "echo $\\"',
        f'path:.github/workflows pushed:>{cutoff_date} "env:" "password"',
        f'path:.github/workflows pushed:>{cutoff_date} "curl" "-H" "Authorization: Bearer"'
    ]

    suspicious_repos = {} # Dedup by repo full_name

    for query in dorks:
        resp = _rate_limited_get(
            f"{GITHUB_API}/search/code",
            params={"q": query, "per_page": min(limit, 100), "sort": "indexed"},
        )
        if resp is None or resp.status_code != 200:
            logger.warning(f"Failed to execute CI dork: {query}")
            continue

        for item in resp.json().get("items", []):
            repo = item.get("repository", {})
            full_name = repo.get("full_name")
            if full_name and full_name not in suspicious_repos:
                suspicious_repos[full_name] = {
                    "owner": repo.get("owner", {}).get("login"),
                    "repo": repo.get("name"),
                    "full_name": full_name,
                    "url": repo.get("html_url"),
                    "trigger_file": item.get("path")
                }

        time.sleep(GITHUB_RATE_LIMIT_PAUSE) # Pause between dork queries

    return list(suspicious_repos.values())

def fetch_recent_workflow_runs(owner: str, repo: str, limit: int = 5) -> List[int]:
    """
    Gets the run IDs of recent completed workflows for a repository.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs"
    # We only care about completed runs that might have full logs
    resp = _rate_limited_get(url, params={"per_page": limit, "status": "completed"})

    if resp is None or resp.status_code != 200:
        logger.debug(f"Failed or no permission to fetch actions runs for {owner}/{repo}: {resp.status_code if resp else 'None'}")
        return []

    run_ids = []
    for run in resp.json().get("workflow_runs", []):
        run_ids.append(run.get("id"))

    return run_ids

def download_and_extract_logs(owner: str, repo: str, run_id: int) -> str:
    """
    Downloads the log ZIP archive for a specific workflow run and extracts the text in-memory.
    Returns a massive combined string of all log outputs.
    """
    url = f"{GITHUB_API}/repos/{owner}/{repo}/actions/runs/{run_id}/logs"

    # GitHub API redirects this to an S3 url to download a ZIP archive
    resp = _rate_limited_get(url, stream=True)

    if resp is None or resp.status_code != 200:
        logger.debug(f"Failed to fetch logs for {owner}/{repo}/run/{run_id} - Usually deleted/expired (410) or forbidden (403/401).")
        return ""

    combined_log_text = ""
    try:
        # Read the zip archive into memory
        with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
            for file_name in archive.namelist():
                # Read each .txt file inside the ZIP
                with archive.open(file_name) as f:
                    # decode with errors ignored just in case log output is chaotic
                    combined_log_text += f.read().decode('utf-8', errors='ignore') + "\n"
    except zipfile.BadZipFile:
        logger.error(f"Received bad zip file from GitHub Actions API for {owner}/{repo}/{run_id}")
    except Exception as e:
        logger.error(f"Error processing log archive for {owner}/{repo}/{run_id}: {e}")

    return combined_log_text

def process_cicd_repo(repo_info: Dict) -> Dict:
    """
    Master function for a single repo:
    1. Fetches recent runs
    2. Downloads zipped logs
    3. Streams logs through our scanners
    """
    owner = repo_info["owner"]
    repo = repo_info["repo"]
    full_name = repo_info["full_name"]

    logger.info(f"[*] Targeting CI/CD logs for {full_name}...")

    run_ids = fetch_recent_workflow_runs(owner, repo, limit=3) # Grab latest 3 runs

    if not run_ids:
        return {"repo": full_name, "status": "no_runs", "findings": []}

    all_findings = []
    engine = get_engine()

    for run_id in run_ids:
        logger.debug(f"    - Downloading logs for run {run_id}...")
        log_text = download_and_extract_logs(owner, repo, run_id)

        if not log_text:
            continue

        # 1. Sweep with standard regex
        pattern_hits = scan_text_patterns(log_text)
        for hit in pattern_hits:
            hit["source"] = f"cicd_log_{run_id}"

        # 2. Sweep with TruffleHog backend
        th_hits = engine.scan_text(log_text)
        for hit in th_hits:
            hit["source"] = f"cicd_log_thog_{run_id}"

        # Combine
        deduped = {}
        for hit in pattern_hits + th_hits:
            key = f"{hit['type']}_{hit.get('value', 'unk')}"
            if key not in deduped:
                deduped[key] = hit

        if deduped:
            logger.info(f"[!] [CI/CD Hunter] FOUND {len(deduped)} potential secrets in {full_name} logs!")
        all_findings.extend(list(deduped.values()))

        time.sleep(1) # Breath between downloads

    return {
        "repo": full_name,
        "url": repo_info["url"],
        "status": "success",
        "findings": all_findings,
        "runs_analyzed": len(run_ids)
    }

def start_cicd_sweep(max_repos: int = 10, max_workers: int = 2) -> List[Dict]:
    """
    Triggers a massive concurrent sweep for CI/CD secrets.
    """
    logger.info(f"Starting CI/CD log hunt (Targeting {max_repos} repos)...")
    repos = find_susceptible_repos(limit=max_repos)
    logger.info(f"Identified {len(repos)} highly suspect repos. Beginning deep scans...")

    results = []
    # Keep workers incredibly low to avoid 403 API Abuse
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_repo = {executor.submit(process_cicd_repo, r): r for r in repos}

        for future in as_completed(future_to_repo):
            try:
                res = future.result()
                if res.get("findings"):
                    results.append(res)
            except Exception as e:
                logger.error(f"Executor failed on repo: {e}")

    return results

if __name__ == "__main__":
    # Test script locally
    logging.basicConfig(level=logging.INFO)
    hits = start_cicd_sweep(max_repos=5)
    print(f"Total Repos with leaks: {len(hits)}")
    for repo in hits:
        print(f"[{repo['repo']}] - {len(repo['findings'])} findings")
