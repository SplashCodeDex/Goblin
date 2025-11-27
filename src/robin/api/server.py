from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import logging

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

# CORS for local dev with Next.js
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
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
    logger.info(f"DEBUG: api_refine called with {req}")
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
    threads: int = 5
    max_results: int = 50
    request_timeout: int = 30
    use_cache: bool = True
    load_cached_only: bool = False


class SearchResp(BaseModel):
    results: List[Dict[str, Any]]


@app.post("/api/search", response_model=SearchResp)
async def api_search(req: SearchReq):
    results = get_search_results(
        req.refined.replace(" ", "+"),
        max_workers=req.threads,
        max_results=req.max_results,
        request_timeout=req.request_timeout,
        use_cache=req.use_cache,
        load_cached_only=req.load_cached_only
    )
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
    scraped = scrape_multiple(
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
    url, content = scrape_single(req.item)
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
    result = generate_summary_and_artifacts(llm, req.query, req.scraped)

    summary_text = result.get("summary", "")
    artifacts = result.get("artifacts", {})
    stix = result.get("stix", {})

    # Generate MISP event
    import uuid
    import pandas as pd
    attrs = []
    cat_map = {"ipv4": "ip-src", "domains": "domain", "emails": "email-src", "btc": "btc", "eth": "eth"}
    for k, vals in artifacts.items():
        for v in vals:
            attrs.append({"type": cat_map.get(k, "text"), "value": v, "category": "External analysis"})

    misp = {
        "Event": {
            "uuid": str(uuid.uuid4()),
            "info": f"Dark web OSINT for: {req.query}",
            "date": str(pd.Timestamp.utcnow().date()),
            "Attribute": attrs
        }
    }

    # Save run to database
    try:
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "query": req.query,
            "refined": "",
            "results": [],
            "filtered": [],
            "scraped": req.scraped,
            "summary": summary_text,
            "artifacts": artifacts, # Save artifacts too
        }
        save_run(entry)
    except Exception as e:
        print(f"Failed to save run: {e}")

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
    email_re = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
    btc_re = re.compile(r"\b[13][a-km-zA-HJ-NP-Z1-9]{25,34}\b")
    domain_re = re.compile(r"\b(?!www\.)[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b")
    for url, content in req.scraped.items():
        for m in email_re.findall(content):
            artifacts.append({"type": "email", "value": m, "context": url})
        for m in btc_re.findall(content):
            artifacts.append({"type": "btc", "value": m, "context": url})
        for m in domain_re.findall(content):
            artifacts.append({"type": "domain", "value": m, "context": url})
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
