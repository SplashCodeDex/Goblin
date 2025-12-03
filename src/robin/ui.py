import streamlit as st
from robin.search import get_search_results, is_tor_running
from robin.scrape import scrape_multiple
from robin.llm import get_llm, refine_query, filter_results, generate_summary

st.set_page_config(page_title="Robin OSINT", layout="wide")
st.title("Robin: Dark Web OSINT (Minimal UI)")

with st.sidebar:
    st.header("Settings")
    model = st.selectbox(
        "Model",
        ["gpt4o", "gpt-4.1", "claude-3-5-sonnet-latest", "llama3.1", "gemini-2.5-flash", "gemini-2.5-flash-preview-09-2025", "gemini-2.5-flash-lite"],
        index=4,
    )
    threads = st.slider("Threads", 1, 16, 5)
    st.caption("Ensure Tor is running at 127.0.0.1:9050 for .onion access.")

query = st.text_input("Search query", placeholder="e.g., ransomware payments")
run = st.button("Run Investigation")

if run and query:
    if not is_tor_running():
        st.warning("Tor SOCKS proxy not detected at 127.0.0.1:9050. Searches may return empty.")

    try:
        llm = get_llm(model)
    except ValueError as e:
        st.error(str(e))
        st.stop()

    st.write("Refining query...")
    refined = refine_query(llm, query)
    st.code(refined, language="text")

    st.write("Searching...")
    results = get_search_results(refined.replace(" ", "+"), max_workers=threads)
    st.write(f"Found {len(results)} results")

    st.write("Filtering results...")
    filtered = filter_results(llm, refined, results)
    st.write(f"Selected {len(filtered)} results")

    st.write("Scraping selected results...")
    scraped, errors = scrape_multiple(filtered, max_workers=threads)
    if errors:
        with st.expander("Scrape errors"):
            for e in errors:
                st.write(e)

    st.write("Generating summary...")
    summary = generate_summary(llm, query, scraped)
    st.subheader("Summary")
    st.markdown(summary)

    with st.expander("Sources"):
        for item in scraped:
            st.markdown(f"- [{item.get('title') or item.get('link')}]({item.get('link')})")

else:
    st.info("Enter a query and click Run Investigation. For the full shadcn UI, use the Docker image as documented in README.")