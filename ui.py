import base64
import streamlit as st
import streamlit_shadcn_ui as ui
from datetime import datetime
from scrape import scrape_multiple
from search import get_search_results, is_tor_running
from llm_utils import BufferedStreamingHandler
from llm import get_llm, refine_query, filter_results, generate_summary_and_artifacts

# Apply dark theme
st.set_page_config(layout="wide", initial_sidebar_state="expanded", page_title="Robin: AI-Powered Dark Web OSINT Tool", page_icon="🕵️‍♂️")



# Cache expensive backend calls
@st.cache_data(ttl=200, show_spinner=False)
def cached_search_results(refined_query: str, threads: int, max_results: int | None, request_timeout: int, use_cache: bool):
    return get_search_results(refined_query.replace(" ", "+"), max_workers=threads, max_results=max_results, request_timeout=request_timeout, use_cache=use_cache)


@st.cache_data(ttl=200, show_spinner=False)
def cached_scrape_multiple(filtered: list, threads: int, request_timeout: int, use_cache: bool):
    return scrape_multiple(filtered, max_workers=threads, request_timeout=request_timeout, use_cache=use_cache)

# Sidebar
with st.sidebar:
    import json, os
    from search import get_tor_proxies
    import requests

    from llm import missing_model_env

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

    st.divider()
    st.subheader("History")

    HISTORY_FILE = "history.jsonl"

    def load_history(max_items: int = 20):
        items = []
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    try:
                        items.append(json.loads(line))
                    except Exception:
                        continue
        items.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        return items[:max_items]

    def save_history(entry: dict):
        try:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            st.warning(f"Failed to save history: {e}")

    hist_items = load_history()
    if hist_items:
        labels = [f"{i['timestamp']} — {i['query'][:40]}" for i in hist_items]
        picked = st.selectbox("Past Runs", options=labels, index=0)
        if picked:
            idx = labels.index(picked)
            chosen = hist_items[idx]
            if ui.button("Load Selected Run", key="load_history"):
                st.session_state.query = chosen.get("query", "")
                st.session_state.streamed_summary = chosen.get("summary", "")
                st.session_state.refined = chosen.get("refined", "")
                st.session_state.scraped = chosen.get("scraped", {})
                st.session_state.results = chosen.get("results", [])
                st.session_state.filtered = chosen.get("filtered", [])
                st.success("Loaded run into session. Switch to Summary/Sources tabs to view.")
    else:
        st.caption("No history yet. Run an investigation to save history.")

# Main UI - logo and input
_, logo_col, _ = st.columns(3)
with logo_col:
    st.image(".github/assets/robin_logo.png", width=200)

# Display text box and button
query = st.text_input(label="Enter Dark Web Search Query", placeholder="Enter Dark Web Search Query")
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
                st.session_state.refined, threads, max_results, request_timeout, use_cache
            )
    with p2:
        ui.card(title="Search Results", content=f"{len(st.session_state.results)} results found")
    stage_progress.progress(40, text="Search completed")

    # Stage 4 - Filter results
    with status_slot.container():
        with st.spinner("🗂️ Filtering results..."):
            st.session_state.filtered = filter_results(
                llm, st.session_state.refined, st.session_state.results
            )
    with p3:
        ui.card(title="Filtered Results", content=f"{len(st.session_state.filtered)} results filtered")
    stage_progress.progress(55, text="Results filtered")

    # New: let the user select which results to scrape
    options = [f"{i+1}. {item['title'][:60]}" for i, item in enumerate(st.session_state.filtered)]
    idx_map = {f"{i+1}. {item['title'][:60]}": i for i, item in enumerate(st.session_state.filtered)}
    
    with st.expander("Select results to scrape", expanded=True):
        import pandas as pd
        table_df = pd.DataFrame([{"title": item['title'], "url": item['link']} for item in st.session_state.filtered])
        st.dataframe(table_df)
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
        import pandas as pd
        st.dataframe(pd.DataFrame(st.session_state.previews))

    # Stage 5 - Scrape content
    if proceed_btn and selected:
        with status_slot.container():
            with st.spinner("📜 Scraping content..."):
                st.session_state.scraped = cached_scrape_multiple(
                    selected, threads, request_timeout, use_cache
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

        # Persist run to history
        try:
            from datetime import datetime as _dt
            import json as _json
            entry = {
                "timestamp": _dt.utcnow().isoformat() + "Z",
                "query": query,
                "refined": st.session_state.get("refined", ""),
                "results": st.session_state.get("results", []),
                "filtered": st.session_state.get("filtered", []),
                "scraped": st.session_state.get("scraped", {}),
                "summary": st.session_state.get("streamed_summary", ""),
            }
            with open("history.jsonl", "a", encoding="utf-8") as _hf:
                _hf.write(_json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            st.warning(f"Failed to save history: {e}")

        stage_progress.progress(100, text="Done")
        status_slot.success("✔️ Pipeline completed successfully!")
