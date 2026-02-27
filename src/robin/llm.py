import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .llm_utils import _llm_config_map, _common_llm_params
from datetime import datetime as _dt
import uuid as _uuid
from .config import OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY

import warnings

warnings.filterwarnings("ignore")


def missing_model_env(model_choice: str):
    m = model_choice.lower()
    config = _llm_config_map.get(m)
    if not config:
        return []

    missing = []
    for env_var in config.get('required_env', []):
        # We need to check if the env var is set.
        # Since we imported keys from .config, we can check those if they match,
        # or we can check os.environ directly.
        # Checking .config variables is safer as they are loaded via dotenv.
        import os
        if not os.getenv(env_var):
             missing.append(env_var)
    return missing


def get_llm(model_choice):
    model_choice_lower = model_choice.lower()
    # Look up the configuration in the map
    config = _llm_config_map.get(model_choice_lower)

    if config is None:  # Extra error check
        # Provide a helpful error message listing supported models
        supported_models = list(_llm_config_map.keys())
        raise ValueError(
            f"Unsupported LLM model: '{model_choice}'. "
            f"Supported models (case-insensitive match) are: {', '.join(supported_models)}"
        )

    # Validate required environment variables for the selected model
    missing = missing_model_env(model_choice)
    if missing:
        raise ValueError(
            f"Model '{model_choice}' requires environment variable(s): {', '.join(missing)}. "
            f"Please set them in .env or your shell environment."
        )

    # Extract the necessary information from the configuration
    llm_class = config["class"]
    model_specific_params = config["constructor_params"]

    # Combine common parameters with model-specific parameters
    # Model-specific parameters will override common ones if there are any conflicts
    all_params = {**_common_llm_params, **model_specific_params}

    # Create the LLM instance using the gathered parameters
    llm_instance = llm_class(**all_params)

    return llm_instance


def refine_query(llm, user_input):
    system_prompt = """
    You are a Cybercrime Threat Intelligence Expert. Your task is to refine the provided user query that needs to be sent to darkweb search engines.

    Rules:
    1. Analyze the user query and think about how it can be improved to use as search engine query
    2. Refine the user query by adding or removing words so that it returns the best result from dark web search engines
    3. Don't use any logical operators (AND, OR, etc.)
    4. Output just the user query and nothing else

    INPUT:
    """
    prompt_template = ChatPromptTemplate(
        [("system", system_prompt), ("user", "{query}")]
    )
    chain = prompt_template | llm | StrOutputParser()
    return chain.invoke({"query": user_input})


def filter_results(llm, query, results):
    if not results:
        return []

    system_prompt = """
    You are a Cybercrime Threat Intelligence Expert. You are given a dark web search query and a list of search results in the form of index, link and title.
    Your task is select the Top 20 relevant results that best match the search query for user to investigate more.
    Rule:
    1. Output ONLY atmost top 20 indices (comma-separated list) no more than that that best match the input query

    Search Query: {query}
    Search Results:
    """

    final_str = _generate_final_string(results)

    prompt_template = ChatPromptTemplate(
        [("system", system_prompt), ("user", "{results}")]
    )
    chain = prompt_template | llm | StrOutputParser()
    try:
        result_indices = chain.invoke({"query": query, "results": final_str})
    except Exception as e:
        print(
            f"LLM error during filtering: {e}. Retrying with truncated titles only."
        )
        final_str = _generate_final_string(results, truncate=True)
        try:
            result_indices = chain.invoke({"query": query, "results": final_str})
        except Exception as e2:
            print(f"LLM error on retry: {e2}. Falling back to first results.")
            result_indices = ""

    # Safely parse up to 20 indices from the model output
    import re as _re
    nums = []
    if isinstance(result_indices, str):
        nums = [int(n) for n in _re.findall(r"\d+", result_indices)]

    seen = set()
    picked = []
    for n in nums:
        if 1 <= n <= len(results) and n not in seen:
            picked.append(n)
            seen.add(n)
        if len(picked) >= 20:
            break

    if not picked:
        picked = list(range(1, min(20, len(results)) + 1))

    top_results = [results[i - 1] for i in picked]

    return top_results


def _generate_final_string(results, truncate=False):
    """
    Generate a formatted string from the search results for LLM processing.
    """

    if truncate:
        # Use only the first 35 characters of the title
        max_title_length = 30
        # Do not use link at all
        max_link_length = 0

    final_str = []
    for i, res in enumerate(results):
        # Truncate link at .onion for display
        truncated_link = re.sub(r"(?<=\.onion).*", "", res["link"])
        title = re.sub(r"[^0-9a-zA-Z\-\.]", " ", res["title"])
        if truncated_link == "" and title == "":
            continue

        if truncate:
            # Truncate title to max_title_length characters
            title = (
                title[:max_title_length] + "..."
                if len(title) > max_title_length
                else title
            )
            # Truncate link to max_link_length characters
            truncated_link = (
                truncated_link[:max_link_length] + "..."
                if len(truncated_link) > max_link_length
                else truncated_link
            )

        final_str.append(f"{i+1}. {truncated_link} - {title}")

    return "\n".join(s for s in final_str)


def _chunk_text(text: str, max_chars: int = 3000, overlap: int = 200):
    chunks = []
    start = 0
    n = len(text)
    while start < n:
        end = min(n, start + max_chars)
        chunks.append(text[start:end])
        if end == n:
            break
        start = max(0, end - overlap)
    return chunks


def _extract_iocs(text: str):
    # Comprehensive regexes for IOCs and sensitive data
    patterns = {
        "emails": r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
        "btc": r"\b(bc1|[13])[a-zA-HJ-NP-Z0-9]{25,39}\b",
        "eth": r"\b0x[a-fA-F0-9]{40}\b",
        "domains": r"\b(?!-)[A-Za-z0-9-]{1,63}(?<!-)\.[A-Za-z]{2,6}\b",
        "ipv4": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "ipv6": r"\b(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}\b|\b(?:[0-9a-fA-F]{1,4}:){1,7}:\b|\b(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}\b",
        "urls": r"https?://[^\s<>\"{}|\\^`\[\]]+",
        "md5": r"\b[a-fA-F0-9]{32}\b",
        "sha1": r"\b[a-fA-F0-9]{40}\b",
        "sha256": r"\b[a-fA-F0-9]{64}\b",
        "cve": r"\bCVE-\d{4}-\d{4,7}\b",
    }
    out = {}
    import re as _re
    
    # Extract all standard patterns
    for k, pat in patterns.items():
        try:
            out[k] = sorted(set(_re.findall(pat, text, _re.IGNORECASE if k == "cve" else 0)))
        except Exception:
            out[k] = []
    
    # Extract email:password combinations
    try:
        email_pass_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[:;,\s]+\s*([^\s]{4,})"
        matches = _re.findall(email_pass_pattern, text)
        out["email_password"] = sorted(set([f"{email}:{password}" for email, password in matches if len(password) >= 4 and len(password) <= 128]))
    except Exception:
        out["email_password"] = []
    
    # Extract API key patterns (common formats)
    try:
        api_patterns = [
            r"(?:api[_-]?key|apikey|api[_-]?token|access[_-]?token|secret[_-]?key)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
            r"\b[A-Za-z0-9_-]{40,}\b",  # Generic long alphanumeric strings
        ]
        api_keys = set()
        for pat in api_patterns:
            found = _re.findall(pat, text, _re.IGNORECASE)
            api_keys.update(found)
        # Filter out common false positives
        filtered_keys = [k for k in api_keys if len(k) >= 20 and len(k) <= 256 and not _re.match(r'^[0-9]+$', k)]
        out["api_keys"] = sorted(set(filtered_keys))
    except Exception:
        out["api_keys"] = []
    
    return out


def _build_stix_bundle(artifacts: dict, sources: list):
    # Minimal STIX 2.1 bundle with ObservedData for each artifact type
    now = _dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
    bundle = {
        "type": "bundle",
        "id": f"bundle--{_uuid.uuid4()}",
        "objects": []
    }
    # One observed-data per category for simplicity
    for k, values in artifacts.items():
        if not values:
            continue
        obs = {
            "type": "observed-data",
            "spec_version": "2.1",
            "id": f"observed-data--{_uuid.uuid4()}",
            "created": now,
            "modified": now,
            "first_observed": now,
            "last_observed": now,
            "number_observed": len(values),
            "labels": ["robin-artifacts", k],
            "extensions": {
                "x-robin-sources": sources
            },
            "x_robin_values": values,
        }
        bundle["objects"].append(obs)
    return bundle


def generate_summary_and_artifacts(llm, query, content):
    """
    Token-aware summarization with chunking + IOC extraction and synthesis.
    Accepts a dict of {url: text} as `content`.
    """
    if isinstance(content, dict):
        sources = content
        combined = "\n\n".join([f"[{i+1}] {u}\n{text}" for i, (u, text) in enumerate(sources.items())])
    else:
        sources = {}
        combined = str(content)

    # Chunk and summarize each chunk
    chunks = _chunk_text(combined, max_chars=3000, overlap=200)
    partial_summaries = []
    all_iocs = {}
    for idx, ch in enumerate(chunks):
        system_prompt = """
        You are a Cybercrime Threat Intelligence Expert. Summarize the provided chunk focusing on:
        - concrete facts, actors, TTPs, and artifacts
        - preserve source markers like [1], [2] to keep provenance
        Keep it concise but complete.
        """
        prompt_template = ChatPromptTemplate([("system", system_prompt), ("user", "{chunk}")])
        chain = prompt_template | llm | StrOutputParser()
        part = chain.invoke({"chunk": ch})
        partial_summaries.append(part)
        # Extract IOCs from the chunk
        iocs = _extract_iocs(ch)
        for k, vals in iocs.items():
            all_iocs.setdefault(k, set()).update(vals)

    # Synthesize final summary with structure and citations
    synthesis_prompt = """
    You are an Cybercrime Threat Intelligence Expert tasked with generating context-based technical investigative insights from dark web osint search engine results.

    Rules:
    1. Use the partial summaries that already contain provenance markers like [1], [2] to justify claims.
    2. Output the Source Links referenced for the analysis (list all from provided sources).
    3. Provide a detailed, contextual, evidence-based technical analysis.
    4. Provide intelligence artifacts along with their context (use the provided IOC lists as hints).
    5. Generate 3-5 key insights, specific and actionable.
    6. Include suggested next steps and queries for further investigation.
    7. Be objective; ignore NSFW or irrelevant text.

    Output Format:
    1. Input Query: {query}
    2. Source Links Referenced for Analysis
    3. Investigation Artifacts
    4. Key Insights
    5. Next Steps

    INPUT:
    - Partial Summaries:
    {partials}
    - IOC Hints (JSON): {iocs}
    - Source Index Map (JSON): {srcs}
    """
    import json as _json
    prompt_template = ChatPromptTemplate([
        ("system", synthesis_prompt), ("user", "{citation_instruction}")
    ])
    chain = prompt_template | llm | StrOutputParser()
    summary = chain.invoke({
        "query": query,
        "partials": "\n\n".join(partial_summaries),
        "iocs": _json.dumps({k: sorted(list(v)) for k, v in all_iocs.items()}, ensure_ascii=False),
        "srcs": _json.dumps(list(sources.keys()), ensure_ascii=False),
        "citation_instruction": "Generate final report with explicit per-insight citations using [index] markers and add a 'Sources cited' section mapping [index] -> URL."
    })

    # Convert IOC sets to lists for serialization
    artifacts = {k: sorted(list(v)) for k, v in all_iocs.items()}

    # Build a minimal STIX 2.1 bundle for artifacts
    stix_bundle = _build_stix_bundle(artifacts, list(sources.keys()))

    return {"summary": summary, "artifacts": artifacts, "stix": stix_bundle}


def generate_summary(llm, query, content):
    """
    Backward-compatible wrapper for CLI and older code paths.
    Returns only the summary string.
    """
    result = generate_summary_and_artifacts(llm, query, content)
    return result.get("summary", "")
