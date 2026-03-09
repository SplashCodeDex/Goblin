from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import logging
import re
from uuid import uuid4
from sse_starlette.sse import EventSourceResponse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
from robin.llm import get_llm, refine_query, filter_results, generate_summary, missing_model_env, suggest_playbooks
from robin.search import get_search_results, stream_search_results, is_tor_running
from robin.scrape import scrape_multiple, scrape_single
from robin.database import (
    save_run, load_runs,
    load_scheduled_queries, save_scheduled_query, delete_scheduled_query,
    update_scheduled_query_status, get_active_queries
)
from datetime import datetime

# Import credential hunting engines
try:
    from robin import credential_patterns, trufflehog_engine, breach_lookup, ml_filter, leaklooker_engine
    from robin.config import ENABLE_LIVE_VERIFICATION, ENABLE_BREACH_LOOKUP, ENABLE_DB_DISCOVERY, ENABLE_GITHUB_DORKING
    CREDENTIAL_ENGINES_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Credential hunting engines not available: {e}")
    CREDENTIAL_ENGINES_AVAILABLE = False
    ENABLE_LIVE_VERIFICATION = False
    ENABLE_BREACH_LOOKUP = False
    ENABLE_DB_DISCOVERY = False
    ENABLE_GITHUB_DORKING = False

# Import GitHub dorking engine (optional, enhances GitHub search)
try:
    from robin import github_dorking
    GITHUB_DORKING_AVAILABLE = True
except ImportError as e:
    logger.warning(f"GitHub dorking engine not available: {e}")
    GITHUB_DORKING_AVAILABLE = False

# Import CI/CD hunter engine
try:
    from robin import cicd_hunter
    CICD_HUNTER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"CI/CD Hunter not available: {e}")
    CICD_HUNTER_AVAILABLE = False

# Import Auto-Pilot engine
try:
    from robin.auto_pilot import scout_instance
    AUTOPILOT_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Auto-Pilot engine not available: {e}")
    AUTOPILOT_AVAILABLE = False

app = FastAPI(title="Robin API", version="1.0.0")

@app.on_event("startup")
async def startup_event():
    from robin.database import initialize_database
    try:
        initialize_database()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")

# Simple in-memory cache for streaming summary
_SUMMARY_CACHE: Dict[str, Dict[str, str]] = {}

# CORS configuration from environment (comma-separated), defaults to * for dev
from robin.config import CORS_ALLOW_ORIGINS
allow_origins = [o.strip() for o in CORS_ALLOW_ORIGINS.split(",") if o.strip()] if CORS_ALLOW_ORIGINS else ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RefineReq(BaseModel):
    model: str
    query: str


class RefineResp(BaseModel):
    refined: str


@app.get("/api/health")
async def health() -> Dict[str, Any]:
    return {"tor": is_tor_running()}


@app.get("/api/model_status")
async def model_status(model: str) -> Dict[str, Any]:
    missing = missing_model_env(model)
    return {"ready": len(missing) == 0, "missing": missing}


@app.post("/api/refine", response_model=RefineResp)
async def api_refine(req: RefineReq):
    logger.debug(f"api_refine called with {req}")
    try:
        missing = missing_model_env(req.model)
        if missing:
            raise HTTPException(status_code=400, detail=f"Missing env: {', '.join(missing)}")
        llm = get_llm(req.model)
        refined = refine_query(llm, req.query)
        return {"refined": refined}
    except HTTPException as he:
        logger.info(f"Caught HTTPException: {he}")
        raise he
    except Exception as e:
        logger.error(f"Error in api_refine: {type(e)} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class SearchReq(BaseModel):
    refined: str
    results: List[Dict[str, Any]]
    sources: List[str] = ["darkweb", "github"]
    max_results: int = 50
    min_stars: int = 0
    min_forks: int = 0
    source_weights: Dict[str, float] = None  # Will use DEFAULT_SOURCE_WEIGHTS if None

    def __init__(self, **data):
        super().__init__(**data)
        if self.source_weights is None:
            from robin.config import DEFAULT_SOURCE_WEIGHTS
            self.source_weights = DEFAULT_SOURCE_WEIGHTS.copy()


@app.post("/api/search")
async def api_search(req: SearchReq):
    import asyncio

    # Validate and normalize source weights
    weights = req.source_weights.copy()

    # Only keep weights for sources that are actually requested
    active_weights = {k: v for k, v in weights.items() if k in req.sources}

    # Normalize weights to sum to 1.0
    total_weight = sum(active_weights.values())
    if total_weight > 0:
        normalized_weights = {k: v / total_weight for k, v in active_weights.items()}
    else:
        # Equal distribution if no weights specified
        normalized_weights = {k: 1.0 / len(req.sources) for k in req.sources}

    # Calculate per-source result limits based on weights
    per_source_limits = {}
    for source in req.sources:
        weight = normalized_weights.get(source, 0)
        limit = max(1, int(req.max_results * weight))  # At least 1 result per source
        per_source_limits[source] = limit

    logger.info(f"Search distribution for {req.max_results} total results: {per_source_limits}")

    results = []

    # Dark Web Search
    if "darkweb" in req.sources:
        darkweb_limit = per_source_limits.get("darkweb", req.max_results)
        dw_results = await asyncio.get_running_loop().run_in_executor(
            None,
            __import__('functools').partial(get_search_results, req.refined, max_results=darkweb_limit)
        )
        results.extend(dw_results[:darkweb_limit])  # Ensure we don't exceed limit

    # GitHub Search
    if "github" in req.sources:
        from robin.github_search import search_github
        github_limit = min(per_source_limits.get("github", req.max_results), 100)  # GitHub API max is 100
        gh_results = await asyncio.get_running_loop().run_in_executor(
            None,
            search_github,
            req.refined,
            github_limit,
            req.min_stars,
            req.min_forks
        )
        results.extend(gh_results[:github_limit])

    # GitHub Code Search
    if "github_code" in req.sources:
        from robin.github_search import search_github_code
        github_code_limit = min(per_source_limits.get("github_code", req.max_results), 100)  # GitHub API max is 100
        gh_code_results = await asyncio.get_running_loop().run_in_executor(
            None,
            search_github_code,
            req.refined,
            github_code_limit
        )
        results.extend(gh_code_results[:github_code_limit])

    # GitHub Commit Search
    if "github_commits" in req.sources:
        from robin.github_search import search_github_commits
        github_commits_limit = min(per_source_limits.get("github_commits", req.max_results), 100)  # GitHub API max is 100
        gh_commit_results = await asyncio.get_running_loop().run_in_executor(
            None,
            search_github_commits,
            req.refined,
            github_commits_limit
        )
        results.extend(gh_commit_results[:github_commits_limit])

    logger.info(f"Search completed: {len(results)} total results from {len(req.sources)} sources")
    return {"results": results}


@app.get("/api/search_stream")
async def api_search_stream(
    query: str,
    sources: str = "darkweb,github",
    max_results: int = 50,
    min_stars: int = 0,
    min_forks: int = 0
):
    import asyncio
    import json
    source_list = [s.strip() for s in sources.split(",") if s.strip()]

    async def event_generator():
        try:
            yield {
                "event": "status",
                "data": json.dumps({"message": f"Initializing tactical scan for: {query}"})
            }

            # Dark Web Search
            if "darkweb" in source_list:
                yield {
                    "event": "status",
                    "data": json.dumps({"message": "Deploying SOCKS5 proxies to Onion space..."})
                }

                loop = asyncio.get_running_loop()
                # Run the sync generator in a loop using run_in_executor
                gen = stream_search_results(query, max_results=max_results)

                while True:
                    try:
                        # We use a wrapper function to call next(gen)
                        res = await loop.run_in_executor(None, next, gen)
                        yield {
                            "event": "result",
                            "data": json.dumps(res)
                        }
                    except StopIteration:
                        break
                    except Exception as e:
                        logger.error(f"Darkweb stream item error: {e}")
                        break

            # GitHub Search (Batch yielded as stream)
            if "github" in source_list:
                yield {
                    "event": "status",
                    "data": json.dumps({"message": "Querying GitHub Intelligence..."})
                }
                from robin.github_search import search_github
                gh_results = await asyncio.get_running_loop().run_in_executor(
                    None,
                    search_github,
                    query,
                    max_results,
                    min_stars,
                    min_forks
                )
                for res in gh_results:
                    yield {
                        "event": "result",
                        "data": json.dumps(res)
                    }

            # GitHub Code Search
            if "github_code" in source_list:
                yield {
                    "event": "status",
                    "data": json.dumps({"message": "Checking GitHub Code snippets..."})
                }
                from robin.github_search import search_github_code
                gh_code_results = await asyncio.get_running_loop().run_in_executor(
                    None,
                    search_github_code,
                    query,
                    max_results
                )
                for res in gh_code_results:
                    yield {
                        "event": "result",
                        "data": json.dumps(res)
                    }

            yield {
                "event": "status",
                "data": json.dumps({"message": "Tactical scan complete."})
            }
            yield {
                "event": "done",
                "data": json.dumps({"status": "complete"})
            }
        except Exception as e:
            logger.error(f"Search stream fatal error: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            }

    return EventSourceResponse(event_generator())


class FilterReq(BaseModel):
    model: str
    refined: str
    results: List[Dict[str, Any]]
    maintain_diversity: bool = True  # New: maintain source balance in filtered results
    max_results: int = 20  # New: configurable filter limit


class FilterResp(BaseModel):
    filtered: List[Dict[str, Any]]


@app.post("/api/filter", response_model=FilterResp)
async def api_filter(req: FilterReq):
    missing = missing_model_env(req.model)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing env: {', '.join(missing)}")
    llm = get_llm(req.model)
    filtered = filter_results(
        llm,
        req.refined,
        req.results,
        maintain_diversity=req.maintain_diversity,
        max_results=req.max_results
    )
    logger.info(f"Filtered {len(req.results)} results to {len(filtered)} (diversity={req.maintain_diversity}, max={req.max_results})")
    return {"filtered": filtered}


class ScrapeReq(BaseModel):
    filtered: List[Dict[str, Any]]
    threads: int = 5
    request_timeout: int = 30
    use_cache: bool = True
    load_cached_only: bool = False
    translate_non_english: bool = True


class ScrapeResp(BaseModel):
    scraped: Dict[str, str]


@app.post("/api/scrape", response_model=ScrapeResp)
async def api_scrape(req: ScrapeReq):
    scraped, _meta = scrape_multiple(
        req.filtered,
        max_workers=req.threads,
        request_timeout=req.request_timeout,
        use_cache=req.use_cache,
        load_cached_only=req.load_cached_only,
        translate_non_english=req.translate_non_english
    )
    return {"scraped": scraped}


class ScrapeOneReq(BaseModel):
    item: Dict[str, Any]


class ScrapeOneResp(BaseModel):
    url: str
    content: str


@app.post("/api/scrape_one", response_model=ScrapeOneResp)
async def api_scrape_one(req: ScrapeOneReq):
    url, content, _meta = scrape_single(req.item)
    return {"url": url, "content": content}


class SummaryReq(BaseModel):
    model: str
    query: str
    scraped: Dict[str, str]


class SummaryResp(BaseModel):
    summary: str
    artifacts: Dict[str, List[str]] = {}
    stix: Dict[str, Any] = {}
    misp: Dict[str, Any] = {}


@app.post("/api/summary", response_model=SummaryResp)
async def api_summary(req: SummaryReq):
    missing = missing_model_env(req.model)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing env: {', '.join(missing)}")
    llm = get_llm(req.model)

    # Use generate_summary_and_artifacts instead of generate_summary
    from robin.llm import generate_summary_and_artifacts

    # Safety: Truncate scraped content if it's too large to prevent context overflow
    # This is a rough safety net; the LLM function might do its own chunking,
    # but we want to avoid sending massive payloads.
    safe_scraped = {}
    MAX_TOTAL_CHARS = 100000 # 100k chars approx 25k tokens, safe for most large context models
    current_chars = 0
    for k, v in req.scraped.items():
        if current_chars >= MAX_TOTAL_CHARS:
            break
        limit = min(len(v), MAX_TOTAL_CHARS - current_chars)
        safe_scraped[k] = v[:limit]
        current_chars += limit

    result = generate_summary_and_artifacts(llm, req.query, safe_scraped)

    summary_text = result.get("summary", "")
    artifacts = result.get("artifacts", {})
    stix = result.get("stix", {})

    # Generate a minimal MISP event structure from artifacts
    import uuid
    attrs = []
    cat_map = {
        "ipv4": "ip-src",
        "ipv6": "ip-src",
        "domains": "domain",
        "emails": "email-src",
        "btc": "btc",
        "eth": "btc",
        "urls": "url",
        "md5": "md5",
        "sha1": "sha1",
        "sha256": "sha256",
        "cve": "vulnerability",
        "email_password": "email-src",
        "api_keys": "text"
    }
    for k, vals in artifacts.items():
        for v in vals:
            attrs.append({
                "type": cat_map.get(k, "text"),
                "value": v,
                "category": "External analysis"
            })

    misp = {
        "Event": {
            "uuid": str(uuid.uuid4()),
            "info": f"Robin OSINT Summary for '{req.query}'",
            "date": datetime.utcnow().strftime("%Y-%m-%d"),
            "threat_level_id": 1,
            "analysis": 2,
            "Attribute": attrs,
        }
    }

    return {"summary": summary_text, "artifacts": artifacts, "stix": stix, "misp": misp}


class CacheReq(BaseModel):
    scraped: Dict[str, str]


@app.post("/api/cache_scraped")
async def cache_scraped(req: CacheReq) -> Dict[str, Any]:
    key = str(uuid4())
    _SUMMARY_CACHE[key] = req.scraped
    return {"id": key}


@app.get("/api/summary_stream")
async def api_summary_stream(model: str, query: str, id: str):
    missing = missing_model_env(model)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing env: {', '.join(missing)}")
    scraped = _SUMMARY_CACHE.get(id)
    if scraped is None:
        raise HTTPException(status_code=404, detail="Unknown cache id")
    llm = get_llm(model)

    async def event_generator():
        # Offload synchronous LLM task to thread pool to avoid blocking the event loop
        import asyncio
        loop = asyncio.get_running_loop()
        text = await loop.run_in_executor(None, generate_summary, llm, query, scraped)

        for line in text.splitlines(True):
            yield {"event": "message", "data": line}
            await asyncio.sleep(0)
    return EventSourceResponse(event_generator())


class ExtractReq(BaseModel):
    scraped: Dict[str, str]


@app.post("/api/extract")
async def api_extract(req: ExtractReq) -> Dict[str, Any]:
    """
    Enhanced artifact extraction using unified credential pattern engine.
    Falls back to basic regex if credential engines not available.
    """
    artifacts = []

    # Use enhanced extraction if available
    if CREDENTIAL_ENGINES_AVAILABLE:
        try:
            for url, content in req.scraped.items():
                # Use credential pattern engine for comprehensive detection
                matches = credential_patterns.scan_text(content)

                for match in matches:
                    artifacts.append({
                        "type": match.category,
                        "value": match.value,
                        "context": url,
                        "pattern_name": match.pattern_name,
                        "confidence": match.confidence,
                        "provider": match.provider,
                        "entropy": match.entropy,
                        "source_tool": match.source_tool
                    })

                # Also use TruffleHog for verification
                trufflehog_findings = trufflehog_engine.scan_text(content)
                for finding in trufflehog_findings:
                    artifacts.append({
                        "type": finding.detector_type,
                        "value": finding.redacted_value,
                        "context": url,
                        "detector": finding.detector_name,
                        "verified": finding.verified,
                        "entropy": finding.entropy,
                        "source_tool": finding.source_tool
                    })

            return {"artifacts": artifacts, "enhanced": True}

        except Exception as e:
            logger.error(f"Enhanced extraction failed: {e}. Falling back to basic extraction.")
            # Fall through to basic extraction

    # Fallback: Basic regex extraction
    patterns = {
        "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        "btc": re.compile(r"\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b"),
        "eth": re.compile(r"\b0x[a-fA-F0-9]{40}\b"),
        "domain": re.compile(r"\b(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.[A-Za-z]{2,6}\b"),
        "ipv4": re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"),
        "ipv6": re.compile(r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b"),
        "url": re.compile(r"https?://[^\s<>\"{}|\\^`\[\]]+"),
        "md5": re.compile(r"\b[a-fA-F0-9]{32}\b"),
        "sha1": re.compile(r"\b[a-fA-F0-9]{40}\b"),
        "sha256": re.compile(r"\b[a-fA-F0-9]{64}\b"),
        "cve": re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE),
    }

    for url, content in req.scraped.items():
        for artifact_type, pattern in patterns.items():
            for match in pattern.findall(content):
                artifacts.append({"type": artifact_type, "value": match, "context": url})

        email_pass_pattern = re.compile(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[:;,\s]+\s*([^\s]{4,})")
        for email, password in email_pass_pattern.findall(content):
            if len(password) >= 4 and len(password) <= 128:
                artifacts.append({"type": "email_password", "value": f"{email}:{password}", "context": url})

        api_pattern = re.compile(r"(?:api[_-]?key|apikey|api[_-]?token|access[_-]?token|secret[_-]?key)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,256})['\"]?", re.IGNORECASE)
        for api_key in api_pattern.findall(content):
            if len(api_key) >= 20 and len(api_key) <= 256 and not re.match(r'^[0-9]+$', api_key):
                artifacts.append({"type": "api_key", "value": api_key, "context": url})

    return {"artifacts": artifacts, "enhanced": False}


@app.get("/api/history")
async def api_history():
    runs = load_runs(max_items=50)
    return {"runs": runs}


class ScheduleReq(BaseModel):
    name: str
    query_text: str
    schedule: str
    search_engines: List[str] = []


@app.post("/api/schedule")
async def api_schedule(req: ScheduleReq):
    from croniter import croniter
    if not croniter.is_valid(req.schedule):
        raise HTTPException(status_code=400, detail="Invalid cron schedule format")
    save_scheduled_query(req.name, req.query_text, req.schedule, req.search_engines)
    return {"status": "ok"}


@app.get("/api/scheduled_queries")
async def api_get_scheduled():
    queries = load_scheduled_queries()
    return {"queries": queries}


@app.delete("/api/schedule/{query_id}")
async def api_delete_schedule(query_id: int):
    delete_scheduled_query(query_id)
    return {"status": "ok"}

@app.get("/api/config")
async def api_get_config():
    from robin.config import get_config
    return get_config()

class ConfigUpdateReq(BaseModel):
    updates: Dict[str, Any]

@app.post("/api/config")
async def api_update_config(req: ConfigUpdateReq):
    from robin.config import update_config
    try:
        update_config(req.updates)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Failed to update config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class PlaybookSuggestReq(BaseModel):
    model: str
    context_query: str = ""
    max_suggestions: int = 5


class PlaybookSuggestResp(BaseModel):
    suggestions: List[Dict[str, str]]


@app.post("/api/suggest_playbooks", response_model=PlaybookSuggestResp)
async def api_suggest_playbooks(req: PlaybookSuggestReq):
    """
    Generate AI-suggested investigation playbooks based on optional context query.
    Returns a list of playbook suggestions with 'name' and 'query' fields.
    """
    missing = missing_model_env(req.model)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing env: {', '.join(missing)}")

    try:
        llm = get_llm(req.model)
        suggestions = suggest_playbooks(
            llm,
            context_query=req.context_query,
            max_suggestions=min(req.max_suggestions, 10)  # Cap at 10 for safety
        )
        return {"suggestions": suggestions}
    except Exception as e:
        logger.error(f"Error in api_suggest_playbooks: {type(e)} - {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== NEW CREDENTIAL HUNTING ENDPOINTS ==========

class VerifyCredentialsReq(BaseModel):
    credentials: List[Dict[str, str]]  # List of {detector_name, value}


@app.post("/api/verify_credentials")
async def api_verify_credentials(req: VerifyCredentialsReq) -> Dict[str, Any]:
    """
    Verify if extracted credentials are still active (requires ENABLE_LIVE_VERIFICATION=true).
    Uses batch concurrent verification for speed.
    WARNING: This makes live API calls to verify credentials. Use with caution.
    """
    if not CREDENTIAL_ENGINES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Credential engines not available")

    if not ENABLE_LIVE_VERIFICATION:
        raise HTTPException(status_code=403, detail="Live verification is disabled. Set ENABLE_LIVE_VERIFICATION=true to enable.")

    engine = trufflehog_engine.get_engine(enable_verification=True)
    results = engine.verify_batch(req.credentials, max_workers=5)

    return {"verification_results": results, "supported_verifiers": list(engine._VERIFIER_MAP.keys())}


class BreachLookupReq(BaseModel):
    emails: List[str]


@app.post("/api/breach_lookup")
async def api_breach_lookup(req: BreachLookupReq) -> Dict[str, Any]:
    """
    Lookup breach history for email addresses (requires ENABLE_BREACH_LOOKUP=true).
    Checks multiple breach databases: HIBP, Snusbase, Dehashed, IntelX, etc.
    """
    if not CREDENTIAL_ENGINES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Credential engines not available")

    if not ENABLE_BREACH_LOOKUP:
        raise HTTPException(status_code=403, detail="Breach lookup is disabled. Set ENABLE_BREACH_LOOKUP=true and configure API keys.")

    # Limit to 50 emails per request to avoid rate limiting
    emails_to_check = req.emails[:50]

    try:
        results = breach_lookup.lookup_emails_bulk(emails_to_check)

        # Convert to serializable format
        breach_data = {}
        for email, summary in results.items():
            breach_data[email] = {
                'pwned': summary.pwned,
                'total_breaches': summary.total_breaches,
                'breach_names': [r.breach_name for r in summary.breach_records],
                'data_classes': list(summary.data_classes_summary),
                'sources': list(summary.sources),
                'leaked_passwords_count': len(summary.leaked_passwords)
            }

        return {"breach_data": breach_data}

    except Exception as e:
        logger.error(f"Breach lookup error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class ScanDatabasesReq(BaseModel):
    query: str
    max_results: int = 100


@app.post("/api/scan_databases")
async def api_scan_databases(req: ScanDatabasesReq) -> Dict[str, Any]:
    """
    Scan for exposed databases and services (requires ENABLE_DB_DISCOVERY=true and BINARYEDGE_API_KEY).
    Searches for exposed MongoDB, Elasticsearch, Redis, S3 buckets, etc.
    """
    if not CREDENTIAL_ENGINES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Credential engines not available")

    if not ENABLE_DB_DISCOVERY:
        raise HTTPException(status_code=403, detail="Database discovery is disabled. Set ENABLE_DB_DISCOVERY=true and BINARYEDGE_API_KEY.")

    try:
        results = leaklooker_engine.scan_exposed_databases(req.query, req.max_results)

        # Convert to serializable format
        exposed_dbs = []
        for db in results:
            exposed_dbs.append({
                'ip': db.ip,
                'port': db.port,
                'service_type': db.service_type,
                'country': db.country,
                'organization': db.organization,
                'database_name': db.database_name,
                'collections': db.collections,
                'size_mb': db.size_mb,
                'discovered_at': db.discovered_at
            })

        return {"exposed_databases": exposed_dbs, "count": len(exposed_dbs)}

    except Exception as e:
        logger.error(f"Database scanning error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/credential_stats")
async def api_credential_stats() -> Dict[str, Any]:
    """
    Get statistics about the credential pattern engine and loaded patterns.
    """
    if not CREDENTIAL_ENGINES_AVAILABLE:
        raise HTTPException(status_code=503, detail="Credential engines not available")

    try:
        pattern_stats = credential_patterns.get_pattern_stats()
        trufflehog_stats = trufflehog_engine.get_engine().get_cache_stats()
        breach_stats = breach_lookup.get_engine().get_cache_stats()
        ml_stats = ml_filter.get_engine().get_stats()
        leaklooker_stats = leaklooker_engine.get_engine().get_stats()

        dorking_stats = {}
        if GITHUB_DORKING_AVAILABLE:
            dorking_stats = {
                'categories': github_dorking.get_dork_categories(),
                'total_dorks': github_dorking.get_total_dork_count(),
            }

        return {
            "patterns": pattern_stats,
            "trufflehog_cache": trufflehog_stats,
            "breach_cache": breach_stats,
            "ml_stats": ml_stats,
            "leaklooker_stats": leaklooker_stats,
            "dorking": dorking_stats,
            "autopilot_supported": AUTOPILOT_AVAILABLE
        }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return {"error": str(e)}

# ========== AUTOPILOT ENDPOINTS ==========

@app.post("/api/autopilot/start")
async def start_autopilot():
    if not AUTOPILOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auto-Pilot engine not available")

    if scout_instance.is_running:
        return {"status": "already_running"}

    # Start the background tasks
    # Note: In a real production app, we'd use a background task manager like Celery,
    # but for this tactical tool, we'll use the AsyncGenerator pattern.
    scout_instance.is_running = True
    logger.info("Auto-Pilot Engage: Engine started via API.")
    return {"status": "started"}

@app.post("/api/autopilot/stop")
async def stop_autopilot():
    if not AUTOPILOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auto-Pilot engine not available")

    scout_instance.stop()
    logger.info("Auto-Pilot Disengage: Engine stopped via API.")
    return {"status": "stopped"}

@app.get("/api/autopilot/stream")
async def autopilot_stream():
    """Real-time SSE stream of findings from the Auto-Pilot."""
    if not AUTOPILOT_AVAILABLE:
        raise HTTPException(status_code=503, detail="Auto-Pilot engine not available")

    async def event_generator():
        try:
            # We already have start_engine which is an async generator
            async for data in scout_instance.start_engine():
                yield {
                    "event": "finding",
                    "data": data
                }
        except Exception as e:
            logger.error(f"Autopilot stream error: {e}")
            yield {
                "event": "error",
                "data": json.dumps({"message": str(e)})
            }

    return EventSourceResponse(event_generator())
            "ml_filter": ml_stats,
            "leaklooker": leaklooker_stats,
            "github_dorking": dorking_stats,
            "features_enabled": {
                "live_verification": ENABLE_LIVE_VERIFICATION,
                "breach_lookup": ENABLE_BREACH_LOOKUP,
                "db_discovery": ENABLE_DB_DISCOVERY,
                "github_dorking": ENABLE_GITHUB_DORKING
            }
        }

    except Exception as e:
        logger.error(f"Error getting credential stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ========== GITHUB DORKING ENDPOINTS ==========

class GithubDorkReq(BaseModel):
    categories: List[str] = []  # Empty = all categories
    custom_dorks: List[str] = []
    limit_per_dork: int = 5
    max_workers: int = 3


@app.post("/api/github_dorks")
async def api_github_dorks(req: GithubDorkReq) -> Dict[str, Any]:
    """
    Run targeted GitHub credential dorking against public repositories.
    Requires ENABLE_GITHUB_DORKING=true and GITHUB_TOKEN.
    """
    if not GITHUB_DORKING_AVAILABLE:
        raise HTTPException(status_code=503, detail="GitHub dorking engine not available")

    if not ENABLE_GITHUB_DORKING:
        raise HTTPException(status_code=403, detail="GitHub dorking disabled. Set ENABLE_GITHUB_DORKING=true")

    try:
        results = github_dorking.search_dorks(
            categories=req.categories or None,
            custom_dorks=req.custom_dorks or None,
            limit_per_dork=req.limit_per_dork,
            max_workers=min(req.max_workers, 5),
        )

        # Flatten all results for summary
        total_hits = sum(len(v) for v in results.values())
        return {
            "results": results,
            "dorks_executed": len(results),
            "total_hits": total_hits,
            "categories_available": github_dorking.get_dork_categories(),
        }
    except Exception as e:
        logger.error(f"GitHub dorking error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class GistSearchReq(BaseModel):
    query: str
    limit: int = 20


@app.post("/api/github_gists")
async def api_github_gists(req: GistSearchReq) -> Dict[str, Any]:
    """
    Search public GitHub Gists for credential leaks.
    Requires GITHUB_TOKEN.
    """
    if not GITHUB_DORKING_AVAILABLE:
        raise HTTPException(status_code=503, detail="GitHub dorking engine not available")

    try:
        results = github_dorking.search_gists(req.query, limit=min(req.limit, 100))
        return {"gists": results, "count": len(results)}
    except Exception as e:
        logger.error(f"GitHub gist search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# ========== CI/CD HUNTER ENDPOINTS ==========

class CICDHuntReq(BaseModel):
    max_repos: int = 5
    max_workers: int = 2


@app.post("/api/hunt_cicd")
async def api_hunt_cicd(req: CICDHuntReq):
    """
    Start a CI/CD build logs hunt across GitHub repositories.
    Streams results back to the client using Server-Sent Events (SSE).
    """
    if not CICD_HUNTER_AVAILABLE:
        raise HTTPException(status_code=503, detail="CI/CD Hunter engine not available")

    async def event_generator():
        try:
            for event in cicd_hunter.start_cicd_sweep(
                max_repos=req.max_repos,
                max_workers=req.max_workers
            ):
                yield {
                    "event": "message",
                    "data": __import__("json").dumps(event)
                }
        except Exception as e:
            logger.error(f"Error during CI/CD sweep: {e}", exc_info=True)
            yield {
                "event": "error",
                "data": __import__("json").dumps({"error": str(e)})
            }

    return EventSourceResponse(event_generator())
