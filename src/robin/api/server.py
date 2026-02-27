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
from robin.llm import get_llm, refine_query, filter_results, generate_summary, missing_model_env
from robin.search import get_search_results, is_tor_running
from robin.scrape import scrape_multiple, scrape_single
from robin.database import (
    save_run, load_runs,
    load_scheduled_queries, save_scheduled_query, delete_scheduled_query,
    update_scheduled_query_status, get_active_queries
)
from datetime import datetime

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
import os
_origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [o.strip() for o in _origins.split(",") if o.strip()] if _origins else ["*"]
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


@app.post("/api/search")
async def api_search(req: SearchReq):
    import asyncio
    results = []

    # Dark Web Search
    if "darkweb" in req.sources:
        dw_results = await asyncio.get_running_loop().run_in_executor(
            None,
            __import__('functools').partial(get_search_results, req.refined, max_results=req.max_results)
        )
        results.extend(dw_results)

    # GitHub Search
    if "github" in req.sources:
        from robin.github_search import search_github
        gh_results = await asyncio.get_running_loop().run_in_executor(
            None,
            search_github,
            req.refined,
            req.max_results,
            req.min_stars,
            req.min_forks
        )
        results.extend(gh_results)

    # GitHub Code Search
    if "github_code" in req.sources:
        from robin.github_search import search_github_code
        gh_code_results = await asyncio.get_running_loop().run_in_executor(
            None,
            search_github_code,
            req.refined,
            req.max_results
        )
        results.extend(gh_code_results)

    # GitHub Commit Search
    if "github_commits" in req.sources:
        from robin.github_search import search_github_commits
        gh_commit_results = await asyncio.get_running_loop().run_in_executor(
            None,
            search_github_commits,
            req.refined,
            req.max_results
        )
        results.extend(gh_commit_results)

    return {"results": results}


class FilterReq(BaseModel):
    model: str
    refined: str
    results: List[Dict[str, Any]]


class FilterResp(BaseModel):
    filtered: List[Dict[str, Any]]


@app.post("/api/filter", response_model=FilterResp)
async def api_filter(req: FilterReq):
    missing = missing_model_env(req.model)
    if missing:
        raise HTTPException(status_code=400, detail=f"Missing env: {', '.join(missing)}")
    llm = get_llm(req.model)
    filtered = filter_results(llm, req.refined, req.results)
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
    artifacts = []
    
    # Comprehensive regex patterns for artifact extraction
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
        # Extract standard patterns
        for artifact_type, pattern in patterns.items():
            for match in pattern.findall(content):
                artifacts.append({"type": artifact_type, "value": match, "context": url})
        
        # Extract email:password combinations
        email_pass_pattern = re.compile(r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[:;,\s]+\s*([^\s]{4,})")
        for email, password in email_pass_pattern.findall(content):
            if len(password) >= 4 and len(password) <= 128:
                artifacts.append({"type": "email_password", "value": f"{email}:{password}", "context": url})
        
        # Extract API keys (common patterns)
        api_pattern = re.compile(r"(?:api[_-]?key|apikey|api[_-]?token|access[_-]?token|secret[_-]?key)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,256})['\"]?", re.IGNORECASE)
        for api_key in api_pattern.findall(content):
            if len(api_key) >= 20 and len(api_key) <= 256 and not re.match(r'^[0-9]+$', api_key):
                artifacts.append({"type": "api_key", "value": api_key, "context": url})
    
    return {"artifacts": artifacts}


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
