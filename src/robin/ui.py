import base64
import streamlit as st
import streamlit_shadcn_ui as ui
from datetime import datetime
from robin.scrape import scrape_multiple
from robin.search import get_search_results, is_tor_running
from robin.llm_utils import BufferedStreamingHandler
from robin.llm import get_llm, refine_query, filter_results, generate_summary_and_artifacts
from robin.database import (
    initialize_database, save_run, load_runs,
    load_scheduled_queries, save_scheduled_query, delete_scheduled_query,
    update_scheduled_query_status
)

# Initialize the database at the start of the script
initialize_database()

# Apply dark theme
st.set_page_config(layout="wide", initial_sidebar_state="expanded", page_title="Robin: AI-Powered Dark Web OSINT Tool", page_icon="🕵️‍♂️")



# Cache expensive backend calls
@st.cache_data(ttl=200, show_spinner=False)
def cached_search_results(refined_query: str, threads: int, max_results: int | None, request_timeout: int, use_cache: bool, load_cached_only: bool):
    return get_search_results(refined_query.replace(" ", "+"), max_workers=threads, max_results=max_results, request_timeout=request_timeout, use_cache=use_cache, load_cached_only=load_cached_only)


@st.cache_data(ttl=200, show_spinner=False)
def cached_scrape_multiple(filtered: list, threads: int, request_timeout: int, use_cache: bool, load_cached_only: bool, translate_non_english: bool):
    return scrape_multiple(filtered, max_workers=threads, request_timeout=request_timeout, use_cache=use_cache, load_cached_only=load_cached_only, translate_non_english=translate_non_english)

# Sidebar
with st.sidebar:
    import json, os
    from robin.search import get_tor_proxies
    import requests

    from robin.llm import missing_model_env

    model_options = ["gpt4o", "gpt-4.1", "claude-3-5-sonnet-latest", "llama3.1", "gemini-2.5-flash", "gemini-2.5-flash-preview-09-2025", "gemini-2.5-flash-lite"]
    model = st.selectbox("Select LLM Model", options=model_options, index=0)
    missing = missing_model_env(model)
    if missing:
        st.error(f"Missing required environment: {', '.join(missing)}")
    else:
        st.info("Model ready")

    threads = st.slider("Scraping Threads", min_value=1, max_value=16, value=4, step=1)

    # Advanced settings
    with st.expander("Advanced settings", expanded=False):
        max_results = st.slider("Max search results", min_value=10, max_value=200, value=50, step=10)
        request_timeout = st.slider("Request timeout (seconds)", min_value=5, max_value=90, value=30, step=5)
        use_cache = st.checkbox("Use disk cache", value=True)
        load_cached_only = st.checkbox("Load cached only (offline mode)", value=False)
        translate_non_english = st.checkbox("Auto-translate non-English content", value=True)
        compact_mode = st.checkbox("Compact results view", value=False)

    st.divider()
    st.subheader("History")

    HISTORY_FILE = "history.jsonl"

    hist_items = load_runs()
    if hist_items:
        # Format timestamp for display
        for i in hist_items:
            # Handle potential ISO format with 'Z' or microseconds
            ts_str = i['timestamp'].replace("Z", "+00:00")
            try:
                i['display_ts'] = datetime.fromisoformat(ts_str).strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                i['display_ts'] = i['timestamp'] # fallback

        labels = [f"{i['display_ts']} — {i['query'][:40]}" for i in hist_items]
        picked = st.selectbox("Past Runs", options=labels, index=0, help="Load a previous investigation run from the database.")
        if picked:
            idx = labels.index(picked)
            chosen = hist_items[idx]
            if ui.button("Load Selected Run", key="load_history"):
                st.session_state.query = chosen.get("query", "")
                st.session_state.streamed_summary = chosen.get("summary", "")
                st.session_state.refined = chosen.get("refined_query", "")
                st.session_state.scraped = chosen.get("scraped_content", {})
                st.session_state.results = chosen.get("results", [])
                st.session_state.filtered = chosen.get("filtered_results", [])
                st.success("Loaded run into session. Switch to Summary/Sources tabs to view.")
    else:
        st.caption("No history yet. Run an investigation to save history.")

# Main UI - logo and input
_, logo_col, _ = st.columns(3)
with logo_col:
    st.image(".github/assets/robin_logo.png", width=160)

# Playbooks and search input with right-aligned button
playbooks = {
    "Ransomware investigation": "ransomware gang leak site credentials logs",
    "Credential leak": "database dump credentials password email combo leak",
    "Zero-day chatter": "zero day exploit sale PoC CVE leak"
}
# Subtle styling for the Playbook button
st.markdown(
    """
    <style>
    .playbook-btn > button {
        background: linear-gradient(135deg, #1f2937 0%, #0f172a 100%);
        color: #e5e7eb !important;
        border: 1px solid #334155;
        box-shadow: 0 2px 8px rgba(0,0,0,0.25);
        transition: transform 120ms ease, box-shadow 200ms ease, background 300ms ease;
        border-radius: 10px;
        padding: 0.55rem 0.9rem;
    }
    .playbook-btn > button:hover { transform: translateY(-1px); box-shadow: 0 6px 16px rgba(0,0,0,0.35); }
    .playbook-btn > button:active { transform: translateY(0); box-shadow: 0 2px 8px rgba(0,0,0,0.25); }
    </style>
    """,
    unsafe_allow_html=True,
)

if 'query' not in st.session_state:
    st.session_state.query = ""
if 'show_playbooks' not in st.session_state:
    st.session_state.show_playbooks = False

inp_col, btn_col = st.columns([10, 2])
with inp_col:
    query = st.text_input(
        label="Enter Dark Web Search Query",
        placeholder="Enter Dark Web Search Query",
        key="query_input",
        value=st.session_state.query,
    )
    st.session_state.query = query
with btn_col:
    if st.button("Playbook", key="playbook_button", help="Open playbook presets", type="secondary"):
        st.session_state.show_playbooks = not st.session_state.show_playbooks
    # Apply class to style above via HTML block
    st.markdown('<div class="playbook-btn"></div>', unsafe_allow_html=True)

if st.session_state.show_playbooks:
    with st.expander("Playbooks", expanded=True):
        pick = st.radio("Choose a playbook", options=["(none)"] + list(playbooks.keys()), index=0, horizontal=False)
        if pick and pick != "(none)":
            st.session_state.query = playbooks[pick]
            st.session_state.query_input = playbooks[pick]
            st.success(f"Loaded playbook: {pick}")
        st.caption("You can edit the prefilled query before running.")

run_button = st.button("Run", key="run_button")

# Display a status message
status_slot = st.empty()
# Pre-allocate three placeholders-one per card
cols = st.columns(3)
p1, p2, p3 = [col.empty() for col in cols]
# Stage progress
stage_progress = st.progress(0, text="Idle")
# Summary placeholders
summary_container_placeholder = st.empty()


# Process the query
if run_button and query:
    # Enforce required envs for selected model before proceeding
    if missing_model_env(model):
        st.error("Missing required API keys/URL for the selected model. Please set env vars in .env or environment.")
        st.stop()

    # clear old state
    for k in ["refined", "results", "filtered", "scraped", "streamed_summary"]:
        st.session_state.pop(k, None)

    # Stage 1 - Load LLM
    with status_slot.container():
        with st.spinner("🔄 Loading LLM..."):
            try:
                llm = get_llm(model)
            except ValueError as e:
                st.error(str(e))
                st.stop()
            if not is_tor_running():
                st.warning("Tor SOCKS proxy not detected at 127.0.0.1:9050. Searches may return empty.")

    # Stage 2 - Refine query
    with status_slot.container():
        with st.spinner("🔄 Refining query..."):
            st.session_state.refined = refine_query(llm, query)
    with p1:
        ui.card(title="Refined Query", content=st.session_state.refined)
    stage_progress.progress(20, text="Query refined")

    # Stage 3 - Search dark web
    with status_slot.container():
        with st.spinner("🔍 Searching dark web..."):
            st.session_state.results = cached_search_results(
                st.session_state.refined, threads, max_results, request_timeout, use_cache, load_cached_only
            )
    with p2:
        ui.card(title="Search Results", content=f"{len(st.session_state.results)} results found")
        if load_cached_only and not st.session_state.results:
            st.info("Offline mode is ON and no cached search for this query was found.")
    stage_progress.progress(40, text="Search completed")

    # Stage 4 - Filter results
    with status_slot.container():
        with st.spinner("🗂️ Filtering results..."):
            st.session_state.filtered = filter_results(
                llm, st.session_state.refined, st.session_state.results
            )
    with p3:
        ui.card(title="Filtered Results", content=f"{len(st.session_state.filtered)} results filtered")
        if compact_mode:
            st.caption("Compact view enabled.")
    stage_progress.progress(55, text="Results filtered")

    # New: let the user select which results to scrape
    options = [f"{i+1}. {item['title'][:60]}" for i, item in enumerate(st.session_state.filtered)]
    idx_map = {f"{i+1}. {item['title'][:60]}": i for i, item in enumerate(st.session_state.filtered)}

    with st.expander("Select results to scrape", expanded=True):
        import pandas as pd
        table_df = pd.DataFrame([{"title": item['title'], "url": item['link']} for item in st.session_state.filtered])
        st.dataframe(table_df, use_container_width=True, height=300 if compact_mode else 500)
        selected = st.multiselect("Select result indices to scrape", options=list(range(len(table_df))), format_func=lambda i: table_df.iloc[i]["title"])
        prev_col, act_col = st.columns([1,1])
        with prev_col:
            preview_btn = st.button("Preview selected", key="preview_btn")
        with act_col:
            proceed_btn = st.button("Proceed to scrape", key="proceed_btn")


    # Optional: preview snippets for selected links before scraping
    if 'previews' not in st.session_state:
        st.session_state.previews = []
    if 'preview_ready' not in st.session_state:
        st.session_state.preview_ready = False

    if preview_btn and selected:
        with status_slot.container():
            with st.spinner("🧪 Fetching previews..."):
                import requests
                from bs4 import BeautifulSoup
                from search import get_tor_proxies

                previews = []
                for item in selected:
                    url = item['link']
                    use_tor = ".onion" in url
                    proxies = get_tor_proxies() if use_tor else None
                    try:
                        r = requests.get(url, proxies=proxies, timeout=10)
                        txt = BeautifulSoup(r.text, 'html.parser').get_text(" ")
                        snippet = (txt.strip()[:400] + '...') if len(txt.strip()) > 400 else txt.strip()
                        previews.append({"title": item['title'], "url": url, "preview": snippet})
                    except Exception:
                        previews.append({"title": item['title'], "url": url, "preview": "(preview failed)"})
                st.session_state.previews = previews
                st.session_state.preview_ready = True

    if st.session_state.preview_ready:
        st.subheader("Selected previews")
        st.caption("Previews may omit media. Blocked/CAPTCHA pages are flagged in scrape metadata.")
        import pandas as pd
        st.dataframe(pd.DataFrame(st.session_state.previews))

    # Stage 5 - Scrape content
    if proceed_btn and selected:
        with status_slot.container():
            with st.spinner("📜 Scraping content..."):
                st.session_state.scraped, st.session_state.scrape_meta = cached_scrape_multiple(
                    selected, threads, request_timeout, use_cache, load_cached_only, translate_non_english
                )
        stage_progress.progress(75, text="Scraping complete")

        # Stage 6 - Summarize
        # 6a) Prepare session state for streaming text
        st.session_state.streamed_summary = ""

        # 6c) UI callback for each chunk
        def ui_emit(chunk: str):
            st.session_state.streamed_summary += chunk
            summary_slot.markdown(st.session_state.streamed_summary)

        chosen_tab = ui.tabs(options=['Summary', 'Sources'], default_value='Summary', key='tabs')

        if chosen_tab == 'Summary':
            # Diagnostics card
            with st.expander("Diagnostics", expanded=False):
                st.caption(f"Tor running: {'Yes' if is_tor_running() else 'No'} | Offline mode: {'Yes' if load_cached_only else 'No'} | Translate: {'Yes' if translate_non_english else 'No'}")
            hdr_col, btn_col = st.columns([4, 1], vertical_alignment="center")
            with hdr_col:
                st.subheader(":red[Investigation Summary]", anchor=None, divider="gray")
            summary_slot = st.empty()

            # 6d) Inject your two callbacks and invoke exactly as before
            with status_slot.container():
                with st.spinner("✍️ Generating summary..."):
                    stream_handler = BufferedStreamingHandler(ui_callback=ui_emit)
                    llm.callbacks = [stream_handler]
                    result = generate_summary_and_artifacts(llm, query, st.session_state.scraped)
                    st.session_state.streamed_summary = result.get("summary", "")
                    st.session_state.artifacts = result.get("artifacts", {})
                    st.session_state.stix = result.get("stix", {})
            stage_progress.progress(95, text="Summary generated")

            with btn_col:
                now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                fname = f"summary_{now}.md"
                st.download_button(
                    label="Download Summary",
                    data=st.session_state.streamed_summary,
                    file_name=fname,
                    mime="text/markdown",
                )

        if chosen_tab == 'Sources':
            # Show scrape metadata table
            import pandas as pd, json
            meta_list = list(st.session_state.get('scrape_meta', {}).values())
            if meta_list:
                st.subheader("Scrape metadata")
                st.dataframe(pd.DataFrame(meta_list))
            import json, pandas as pd
            sources_df = pd.DataFrame([
                {"url": url, "excerpt": text} for url, text in st.session_state.scraped.items()
            ])
            st.dataframe(sources_df)
            exp_col1, exp_col2, exp_col3 = st.columns(3)
            with exp_col1:
                st.download_button(
                    label="Download sources (CSV)",
                    data=sources_df.to_csv(index=False).encode("utf-8"),
                    file_name="sources.csv",
                    mime="text/csv",
                )
            with exp_col2:
                st.download_button(
                    label="Download sources (JSON)",
                    data=json.dumps(sources_df.to_dict(orient="records"), ensure_ascii=False, indent=2),
                    file_name="sources.json",
                    mime="application/json",
                )
            with exp_col3:
                st.download_button(
                    label="Download STIX 2.1 (JSON)",
                    data=json.dumps(st.session_state.get("stix", {}), ensure_ascii=False, indent=2),
                    file_name="artifacts_stix.json",
                    mime="application/json",
                )

            # MISP export
            def build_misp_event(artifacts: dict, info: str):
                import uuid, time
                attrs = []
                cat_map = {"ipv4": "ip-src", "domains": "domain", "emails": "email-src", "btc": "btc", "eth": "eth"}
                for k, vals in artifacts.items():
                    for v in vals:
                        attrs.append({"type": cat_map.get(k, "text"), "value": v, "category": "External analysis"})
                return {
                    "Event": {
                        "uuid": str(uuid.uuid4()),
                        "info": info,
                        "date": str(pd.Timestamp.utcnow().date()),
                        "Attribute": attrs
                    }
                }
            with st.expander("MISP export", expanded=False):
                misp_json = build_misp_event(artifacts, f"Dark web OSINT for: {query}")
                st.download_button(
                    label="Download MISP Event (JSON)",
                    data=json.dumps(misp_json, ensure_ascii=False, indent=2),
                    file_name="misp_event.json",
                    mime="application/json",
                )

            # Artifacts export
            st.subheader("Artifacts")
            artifacts = st.session_state.get("artifacts", {})
            art_df = pd.DataFrame([
                {"type": k, "value": v} for k, vals in artifacts.items() for v in vals
            ])
            st.dataframe(art_df)
            a1, a2 = st.columns(2)
            with a1:
                st.download_button(
                    label="Download artifacts (CSV)",
                    data=art_df.to_csv(index=False).encode("utf-8"),
                    file_name="artifacts.csv",
                    mime="text/csv",
                )
            with a2:
                st.download_button(
                    label="Download artifacts (JSON)",
                    data=json.dumps(artifacts, ensure_ascii=False, indent=2),
                    file_name="artifacts.json",
                    mime="application/json",
                )

        # Simple Watchlists and Alerts
        if 'watchlists' not in st.session_state:
            st.session_state.watchlists = {"keywords": []}
        with st.expander("Watchlists & Alerts", expanded=False):
            new_kw = st.text_input("Add keyword to watchlist", value="")
            if st.button("Add keyword") and new_kw:
                st.session_state.watchlists["keywords"].append(new_kw)
            if st.session_state.watchlists["keywords"]:
                st.write("Current keywords:", st.session_state.watchlists["keywords"])
                # Alert: show hits in scraped content
                hits = []
                for url, txt in st.session_state.scraped.items():
                    for kw in st.session_state.watchlists["keywords"]:
                        if kw.lower() in txt.lower():
                            hits.append({"keyword": kw, "url": url})
                if hits:
                    st.success(f"Alerts: {len(hits)} hits found")
                    st.dataframe(pd.DataFrame(hits))

        # Persist run to history database
        try:
            from datetime import datetime as _dt
            entry = {
                "timestamp": _dt.utcnow().isoformat() + "Z",
                "query": query,
                "refined": st.session_state.get("refined", ""),
                "results": st.session_state.get("results", []),
                "filtered": st.session_state.get("filtered", []),
                "scraped": st.session_state.get("scraped", {}),
                "summary": st.session_state.get("streamed_summary", ""),
            }
            save_run(entry)
            st.toast("Run saved to history database.", icon="💾")
        except Exception as e:
            st.warning(f"Failed to save history to database: {e}")

        stage_progress.progress(100, text="Done")
        status_slot.success("✔️ Pipeline completed successfully!")
