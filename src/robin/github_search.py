import requests
import logging
from .config import GITHUB_TOKEN

logger = logging.getLogger(__name__)

def search_github(query, limit=10):
    """
    Searches GitHub for repositories matching the query.
    Returns a list of dictionaries with 'title', 'link', 'snippet', 'source'.
    """
    url = "https://api.github.com/search/repositories"
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    params = {
        "q": query,
        "per_page": limit,
        "sort": "stars"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("items", []):
                results.append({
                    "title": item.get("full_name"),
                    "link": item.get("html_url"),
                    "snippet": item.get("description") or "No description",
                    "source": "github"
                })
            return results
        elif response.status_code == 403:
            logger.warning("GitHub API rate limit exceeded or invalid token.")
            return []
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"GitHub search failed: {e}")
        return []

def search_github_code(query, limit=10):
    """
    Searches GitHub for code matching the query.
    Returns a list of dictionaries with 'title', 'link', 'snippet', 'source'.
    """
    url = "https://api.github.com/search/code"
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"

    params = {
        "q": query,
        "per_page": limit,
        "sort": "indexed"
    }

    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        if response.status_code == 200:
            data = response.json()
            results = []
            for item in data.get("items", []):
                repo = item.get("repository", {})
                results.append({
                    "title": f"{repo.get('full_name')} - {item.get('name')}",
                    "link": item.get("html_url"),
                    "snippet": f"Match in {item.get('path')}",
                    "source": "github_code"
                })
            return results
        elif response.status_code == 403:
            logger.warning("GitHub API rate limit exceeded or invalid token.")
            return []
        else:
            logger.error(f"GitHub API error: {response.status_code} - {response.text}")
            return []
    except Exception as e:
        logger.error(f"GitHub code search failed: {e}")
        return []
