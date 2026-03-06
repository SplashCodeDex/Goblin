import re
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .llm_utils import _llm_config_map, _common_llm_params
from datetime import datetime as _dt
import uuid as _uuid
from .config import (
    OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY,
    ENABLE_LIVE_VERIFICATION, ENABLE_BREACH_LOOKUP, ENABLE_ML_FILTERING,
    CREDENTIAL_MIN_CONFIDENCE, CREDENTIAL_CATEGORIES
)

# Import credential hunting engines
try:
    from . import credential_patterns
    from . import trufflehog_engine
    from . import breach_lookup
    from . import ml_filter
    CREDENTIAL_ENGINES_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Credential hunting engines not available: {e}")
    CREDENTIAL_ENGINES_AVAILABLE = False

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


def filter_results(llm, query, results, maintain_diversity=True, max_results=20):
    """
    Filter search results using LLM with optional source diversity preservation.

    Args:
        llm: Language model instance
        query: Search query
        results: List of search result dicts
        maintain_diversity: If True, maintains proportional representation from each source
        max_results: Maximum number of results to return (default 20)

    Returns:
        Filtered list of results
    """
    if not results:
        return []

    if maintain_diversity:
        return _filter_with_diversity(llm, query, results, max_results)
    else:
        return _filter_top_n(llm, query, results, max_results)


def _filter_top_n(llm, query, results, max_results=20):
    """Original filter: select top N overall results regardless of source."""
    system_prompt = """
    You are a Cybercrime Threat Intelligence Expert. You are given a search query and a list of search results.
    Each result contains: index, link, title, and optionally a snippet (description or context).
    Your task is to select the Top {max_results} most relevant results that best match the search query for further investigation.

    Rules:
    1. Analyze both the title AND the snippet (when available) to determine relevance
    2. Prioritize results where the snippet provides concrete evidence of relevance
    3. Output ONLY the top {max_results} indices (comma-separated list) that best match the input query
    4. Do not output explanations, just the numbers

    Search Query: {query}
    Search Results:
    """

    final_str = _generate_final_string(results)

    prompt_template = ChatPromptTemplate(
        [("system", system_prompt), ("user", "{results}")]
    )
    chain = prompt_template | llm | StrOutputParser()
    try:
        result_indices = chain.invoke({"query": query, "results": final_str, "max_results": max_results})
    except Exception as e:
        print(
            f"LLM error during filtering: {e}. Retrying with truncated titles only."
        )
        final_str = _generate_final_string(results, truncate=True)
        try:
            result_indices = chain.invoke({"query": query, "results": final_str, "max_results": max_results})
        except Exception as e2:
            print(f"LLM error on retry: {e2}. Falling back to first results.")
            result_indices = ""

    # Safely parse up to max_results indices from the model output
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
        if len(picked) >= max_results:
            break

    if not picked:
        picked = list(range(1, min(max_results, len(results)) + 1))

    top_results = [results[i - 1] for i in picked]

    return top_results


def _filter_with_diversity(llm, query, results, max_results=20):
    """
    Diversity-aware filter: maintains proportional representation from each source.
    This prevents one source from dominating filtered results.
    """
    # Group results by source
    by_source = {}
    for idx, res in enumerate(results):
        source = res.get('source', 'unknown')
        if source not in by_source:
            by_source[source] = []
        by_source[source].append((idx, res))

    # Calculate how many results to pick from each source
    total_results = len(results)
    source_counts = {s: len(items) for s, items in by_source.items()}

    # Proportional allocation based on source representation
    per_source_limit = {}
    for source, count in source_counts.items():
        proportion = count / total_results
        limit = max(1, int(max_results * proportion))  # At least 1 per source
        per_source_limit[source] = limit

    # Adjust if total exceeds max_results due to rounding
    total_allocated = sum(per_source_limit.values())
    if total_allocated > max_results:
        # Reduce from largest allocations first
        sorted_sources = sorted(per_source_limit.items(), key=lambda x: x[1], reverse=True)
        reduction_needed = total_allocated - max_results
        for source, _ in sorted_sources:
            if reduction_needed <= 0:
                break
            if per_source_limit[source] > 1:
                per_source_limit[source] -= 1
                reduction_needed -= 1

    # Filter each source separately
    final_results = []
    for source, items in by_source.items():
        limit = per_source_limit.get(source, 1)
        source_results = [res for idx, res in items]

        if len(source_results) <= limit:
            # If source has fewer results than limit, take all
            final_results.extend(source_results)
        else:
            # Use LLM to filter within this source
            filtered = _filter_top_n(llm, query, source_results, limit)
            final_results.extend(filtered)

    # Sort by original order (optional - could also rank by relevance)
    result_map = {id(res): idx for idx, res in enumerate(results)}
    final_results.sort(key=lambda r: result_map.get(id(r), 99999))

    return final_results[:max_results]


def _generate_final_string(results, truncate=False):
    """
    Generate a formatted string from the search results for LLM processing.
    Now includes snippets for GitHub repos and commits for better filtering accuracy.
    """

    if truncate:
        # Use only the first 35 characters of the title
        max_title_length = 30
        # Do not use link at all
        max_link_length = 0
        # Skip snippets when truncating (fallback mode)
        use_snippets = False
    else:
        use_snippets = True

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

        # Build the result line
        result_line = f"{i+1}. {truncated_link} - {title}"

        # Add snippet for high-quality sources (GitHub repos, commits, and darkweb)
        if use_snippets and 'snippet' in res and res.get('snippet'):
            source = res.get('source', '')
            # Use snippets from:
            # - GitHub repos (repository descriptions)
            # - GitHub commits (commit messages)
            # - Darkweb (extracted descriptions from search results)
            # Skip github_code (just file paths, not useful for filtering)
            if source in ['github', 'github_commits', 'darkweb']:
                snippet = res['snippet']
                # Clean and truncate snippet to avoid token overflow
                snippet_clean = re.sub(r'[^0-9a-zA-Z\-\.\s,;:]', ' ', snippet)
                max_snippet_length = 150
                if len(snippet_clean) > max_snippet_length:
                    snippet_clean = snippet_clean[:max_snippet_length] + "..."
                result_line += f" | {snippet_clean}"

        final_str.append(result_line)

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
    """
    Enhanced IOC extraction using unified credential pattern engine + TruffleHog
    Falls back to basic regex if credential engines not available
    """
    import re as _re

    # Standard IOC patterns (kept from original)
    standard_patterns = {
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

    # Extract standard IOCs
    for k, pat in standard_patterns.items():
        try:
            out[k] = sorted(set(_re.findall(pat, text, _re.IGNORECASE if k == "cve" else 0)))
        except Exception:
            out[k] = []

    # Enhanced credential extraction using credential pattern engine
    advanced_engine_success = False
    if CREDENTIAL_ENGINES_AVAILABLE:
        try:
            # Scan using unified pattern engine (1600+ patterns)
            matches = credential_patterns.scan_text(
                text,
                min_confidence=CREDENTIAL_MIN_CONFIDENCE,
                categories=CREDENTIAL_CATEGORIES
            )

            # Organize by category
            credentials_by_category = {}
            for match in matches:
                category = match.category
                if category not in credentials_by_category:
                    credentials_by_category[category] = []

                credential_info = {
                    'value': match.value,
                    'pattern_name': match.pattern_name,
                    'confidence': match.confidence,
                    'provider': match.provider,
                    'entropy': match.entropy,
                    'source_tool': match.source_tool
                }
                credentials_by_category[category].append(credential_info)

            # Add to output
            for category, creds in credentials_by_category.items():
                out[category] = creds

            # Also scan with TruffleHog for verification and entropy detection
            try:
                trufflehog_findings = trufflehog_engine.scan_text(text)

                if trufflehog_findings:
                    verified_credentials = []
                    for finding in trufflehog_findings:
                        verified_credentials.append({
                            'value': finding.redacted_value,  # Use redacted for safety
                            'detector': finding.detector_name,
                            'verified': finding.verified,
                            'entropy': finding.entropy,
                            'source_tool': finding.source_tool
                        })

                    out['verified_credentials'] = verified_credentials

            except Exception as e:
                print(f"TruffleHog scanning error: {e}")

            # High-entropy string detection
            try:
                high_entropy = trufflehog_engine.entropy_scan(text)
                if high_entropy:
                    out['high_entropy_strings'] = [
                        {
                            'value': s.value[:50] + '...' if len(s.value) > 50 else s.value,
                            'entropy': s.entropy,
                            'type': s.string_type
                        }
                        for s in high_entropy[:20]  # Limit to top 20
                    ]
            except Exception as e:
                print(f"Entropy scanning error: {e}")

            advanced_engine_success = True

        except Exception as e:
            print(f"Credential pattern engine error: {e}. Falling back to basic extraction.")
            # Fall back to basic extraction below

    # Fallback: Basic credential extraction (if engines not available or failed)
    if not advanced_engine_success:
        try:
            email_pass_pattern = r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})\s*[:;,\s]+\s*([^\s]{4,})"
            matches = _re.findall(email_pass_pattern, text)
            out["email_password"] = sorted(set([f"{email}:{password}" for email, password in matches if len(password) >= 4 and len(password) <= 128]))
        except Exception:
            out["email_password"] = []

        try:
            api_patterns = [
                r"(?:api[_-]?key|apikey|api[_-]?token|access[_-]?token|secret[_-]?key)['\"]?\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
                r"\b[A-Za-z0-9_-]{40,}\b",
            ]
            api_keys = set()
            for pat in api_patterns:
                found = _re.findall(pat, text, _re.IGNORECASE)
                api_keys.update(found)
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
    Enhanced with breach lookup and ML filtering.
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
            if isinstance(vals, list) and len(vals) > 0:
                # Handle both simple lists and lists of dicts
                if isinstance(vals[0], dict):
                    # For credential findings (dicts), keep as is
                    all_iocs.setdefault(k, []).extend(vals)
                else:
                    # For simple strings, use set to deduplicate
                    all_iocs.setdefault(k, set()).update(vals)
            elif isinstance(vals, set):
                all_iocs.setdefault(k, set()).update(vals)

    # Apply ML filtering if enabled
    if CREDENTIAL_ENGINES_AVAILABLE and ENABLE_ML_FILTERING:
        try:
            # Filter credential findings to remove false positives
            for category in ['api_keys', 'credentials', 'tokens', 'private_keys',
                           'connection_strings', 'cloud_credentials', 'payment', 'crypto_wallets']:
                if category in all_iocs and isinstance(all_iocs[category], list):
                    findings = all_iocs[category]
                    if findings and isinstance(findings[0], dict):
                        # Apply ML filter
                        real_creds, false_positives = ml_filter.filter_false_positives(findings)
                        all_iocs[category] = real_creds
                        # Store false positives separately for reference
                        if false_positives:
                            all_iocs[f'{category}_filtered_out'] = false_positives
        except Exception as e:
            print(f"ML filtering error: {e}")

    # Perform breach lookup for emails if enabled
    breach_data = {}
    if CREDENTIAL_ENGINES_AVAILABLE and ENABLE_BREACH_LOOKUP:
        try:
            emails = all_iocs.get('emails', [])
            if emails:
                # Convert set to list if needed
                if isinstance(emails, set):
                    emails = list(emails)

                # Limit to first 50 emails to avoid rate limiting
                emails_to_check = emails[:50]
                breach_results = breach_lookup.lookup_emails_bulk(emails_to_check)

                # Add breach data to artifacts
                if breach_results:
                    breach_data = {
                        email: {
                            'pwned': summary.pwned,
                            'breach_count': summary.total_breaches,
                            'leaked_passwords': summary.leaked_passwords[:5],  # Limit to 5
                            'data_classes': list(summary.data_classes_summary)
                        }
                        for email, summary in breach_results.items()
                        if summary.pwned
                    }

                    if breach_data:
                        all_iocs['breach_data'] = breach_data
        except Exception as e:
            print(f"Breach lookup error: {e}")

    # Synthesize final summary with structure and citations
    synthesis_prompt = """
    You are an Cybercrime Threat Intelligence Expert tasked with generating context-based technical investigative insights from dark web osint search engine results.

    Rules:
    1. Use the partial summaries that already contain provenance markers like [1], [2] to justify claims.
    2. Output the Source Links referenced for the analysis (list all from provided sources).
    3. Provide a detailed, contextual, evidence-based technical analysis.
    4. Provide intelligence artifacts along with their context (use the provided IOC lists as hints).
    5. If breach data is available, incorporate it into the analysis (show which emails were found in breaches).
    6. Generate 3-5 key insights, specific and actionable.
    7. Include suggested next steps and queries for further investigation.
    8. Be objective; ignore NSFW or irrelevant text.

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
    - Breach Data (JSON): {breach_data}
    - Source Index Map (JSON): {srcs}
    """
    import json as _json

    # Prepare artifacts for JSON serialization
    artifacts_serializable = {}
    for k, v in all_iocs.items():
        if isinstance(v, set):
            artifacts_serializable[k] = sorted(list(v))
        elif isinstance(v, list):
            artifacts_serializable[k] = v
        else:
            artifacts_serializable[k] = v

    prompt_template = ChatPromptTemplate([
        ("system", synthesis_prompt), ("user", "{citation_instruction}")
    ])
    chain = prompt_template | llm | StrOutputParser()
    summary = chain.invoke({
        "query": query,
        "partials": "\n\n".join(partial_summaries),
        "iocs": _json.dumps(artifacts_serializable, ensure_ascii=False, default=str),
        "breach_data": _json.dumps(breach_data, ensure_ascii=False) if breach_data else "{}",
        "srcs": _json.dumps(list(sources.keys()), ensure_ascii=False),
        "citation_instruction": "Generate final report with explicit per-insight citations using [index] markers and add a 'Sources cited' section mapping [index] -> URL."
    })

    # Convert IOC sets to lists for serialization
    artifacts = {}
    for k, v in all_iocs.items():
        if isinstance(v, set):
            artifacts[k] = sorted(list(v))
        else:
            artifacts[k] = v

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


def suggest_playbooks(llm, context_query: str = "", max_suggestions: int = 5):
    """
    Generate AI-suggested investigation playbooks based on optional context.

    Args:
        llm: The language model instance
        context_query: Optional user query to provide context for suggestions
        max_suggestions: Maximum number of playbooks to suggest (default 5)

    Returns:
        List of dicts with 'name' and 'query' keys
    """
    import json as _json

    system_prompt = """
    You are a Cybercrime Threat Intelligence Expert with deep knowledge of OSINT investigation methodologies.
    Your task is to suggest tactical investigation playbooks for dark web and GitHub threat intelligence gathering.

    Each playbook should be:
    - Specific and actionable
    - Focused on a particular threat scenario or investigation type
    - Include optimized search queries that work well with dark web search engines and GitHub

    Common investigation scenarios include:
    - Ransomware campaigns and leak sites
    - Credential dumps and database leaks
    - Zero-day exploits and vulnerability trading
    - Malware family tracking
    - C2 infrastructure hunting
    - Phishing kit distribution
    - Crypto fraud and scam operations
    - Data broker markets
    - Insider threat indicators
    - APT group activity monitoring

    Rules:
    1. Generate {max_suggestions} diverse playbook suggestions
    2. Each playbook must have a concise name (2-5 words, tactical style)
    3. Each query should be 4-10 keywords optimized for search engines
    4. Queries should NOT use logical operators (AND, OR, NOT)
    5. Focus on current, realistic threat scenarios
    6. If context_query is provided, include related playbooks but also suggest diverse alternatives

    Output Format (JSON array):
    [
        {{"name": "Playbook Name", "query": "search query keywords"}},
        {{"name": "Another Playbook", "query": "other keywords"}}
    ]

    Context Query: {context_query}

    OUTPUT (valid JSON array only, no markdown, no explanations):
    """

    prompt_template = ChatPromptTemplate([
        ("system", system_prompt),
        ("user", "Generate {max_suggestions} tactical playbook suggestions.")
    ])

    chain = prompt_template | llm | StrOutputParser()

    try:
        response = chain.invoke({
            "context_query": context_query or "general threat intelligence",
            "max_suggestions": max_suggestions
        })

        # Try to extract JSON from response (handle cases where LLM adds markdown code blocks)
        response_clean = response.strip()

        # Remove markdown code blocks if present
        if response_clean.startswith("```"):
            # Extract content between ``` markers
            lines = response_clean.split('\n')
            response_clean = '\n'.join(lines[1:-1]) if len(lines) > 2 else response_clean
            response_clean = response_clean.replace("```json", "").replace("```", "").strip()

        # Parse JSON
        playbooks = _json.loads(response_clean)

        # Validate structure
        if not isinstance(playbooks, list):
            raise ValueError("Response is not a list")

        # Ensure each playbook has required fields
        validated = []
        for pb in playbooks[:max_suggestions]:
            if isinstance(pb, dict) and 'name' in pb and 'query' in pb:
                validated.append({
                    'name': str(pb['name']).strip(),
                    'query': str(pb['query']).strip()
                })

        if not validated:
            # Fallback to default suggestions
            return _get_fallback_playbooks(context_query)

        return validated

    except Exception as e:
        print(f"Error generating playbook suggestions: {e}. Using fallback.")
        return _get_fallback_playbooks(context_query)


def _get_fallback_playbooks(context_query: str = ""):
    """
    Fallback playbooks when LLM generation fails.
    Provides context-aware defaults based on query keywords.
    """
    # Default diverse playbooks
    fallback = [
        {"name": "Ransomware Leak Sites", "query": "ransomware gang leak site stolen data credentials"},
        {"name": "Credential Markets", "query": "database dump credentials combo list email password"},
        {"name": "Exploit Trading", "query": "zero day exploit CVE PoC vulnerability sale"},
        {"name": "Malware Infrastructure", "query": "C2 command control malware botnet infrastructure"},
        {"name": "Phishing Campaigns", "query": "phishing kit panel credential harvester scam"},
    ]

    # If context query provided, try to add a context-specific playbook
    if context_query:
        context_lower = context_query.lower()

        # Simple keyword matching for context-aware suggestions
        context_playbooks = {
            "ransomware": {"name": "Ransomware Attribution", "query": "ransomware gang affiliate bitcoin payment wallet"},
            "credential": {"name": "Credential Exposure", "query": "leaked credentials employee corporate database breach"},
            "malware": {"name": "Malware Analysis", "query": "malware sample hash analysis reverse engineering"},
            "phishing": {"name": "Phishing Infrastructure", "query": "phishing domain hosting panel kit distribution"},
            "apt": {"name": "APT Tracking", "query": "APT advanced persistent threat campaign indicators"},
            "crypto": {"name": "Crypto Fraud", "query": "cryptocurrency scam fraud wallet drainer rug pull"},
            "vulnerability": {"name": "Vulnerability Intel", "query": "vulnerability CVE exploit PoC patch bypass"},
        }

        for keyword, playbook in context_playbooks.items():
            if keyword in context_lower:
                # Insert context-specific playbook at the beginning
                fallback.insert(0, playbook)
                break

    return fallback[:5]
