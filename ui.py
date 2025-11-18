import base64
import streamlit as st
import streamlit_shadcn_ui as ui
from datetime import datetime
from scrape import scrape_multiple
from search import get_search_results, is_tor_running
from llm_utils import BufferedStreamingHandler
from llm import get_llm, refine_query, filter_results, generate_summary

# Apply dark theme
st.set_page_config(layout="wide", initial_sidebar_state="expanded", page_title="Robin: AI-Powered Dark Web OSINT Tool", page_icon="🕵️‍♂️")



# Cache expensive backend calls
@st.cache_data(ttl=200, show_spinner=False)
def cached_search_results(refined_query: str, threads: int):
    return get_search_results(refined_query.replace(" ", "+"), max_workers=threads)


@st.cache_data(ttl=200, show_spinner=False)
def cached_scrape_multiple(filtered: list, threads: int):
    return scrape_multiple(filtered, max_workers=threads)

# Sidebar
with st.sidebar:
    st.title("Robin")
    st.text("AI-Powered Dark Web OSINT Tool")
    st.markdown(
        """Made by [Apurv Singh Gautam](https://www.linkedin.com/in/apurvsinghgautam/)"""
    )
    st.subheader("Settings")
    from llm import missing_model_env

    model = ui.select(
        options=["gpt4o", "gpt-4.1", "claude-3-5-sonnet-latest", "llama3.1", "gemini-2.5-flash", "gemini-2.5-flash-preview-09-2025", "gemini-2.5-flash-lite"],
        default="gpt4o",
        label="Select LLM Model",
    )
    missing = missing_model_env(model)
    if missing:
        st.warning(f"Missing: {', '.join(missing)}")
    else:
        st.info("Model ready")

    threads = ui.slider(default=[4], min_value=1, max_value=16, step=1, label="Scraping Threads")

# Main UI - logo and input
_, logo_col, _ = st.columns(3)
with logo_col:
    st.image(".github/assets/robin_logo.png", width=200)

# Display text box and button
query = ui.text_input(placeholder="Enter Dark Web Search Query", label="Enter Dark Web Search Query")
run_button = ui.button("Run", key="run_button")

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
                st.session_state.refined, threads
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
        ui.table(data=[{"title": item['title'], "url": item['link']} for item in st.session_state.filtered], checkbox=True, key="selection")
    
    selected = []
    if "selection" in st.session_state and st.session_state.selection is not None:
        selected = [st.session_state.filtered[i] for i in st.session_state.selection['selection']]

    # Stage 5 - Scrape content
    with status_slot.container():
        with st.spinner("📜 Scraping content..."):
            st.session_state.scraped = cached_scrape_multiple(
                selected, threads
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
                _ = generate_summary(llm, query, st.session_state.scraped)
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
        exp_col1, exp_col2 = st.columns(2)
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

    stage_progress.progress(100, text="Done")
    status_slot.success("✔️ Pipeline completed successfully!")
