import click
import subprocess
from yaspin import yaspin
from datetime import datetime
from robin.scrape import scrape_multiple
from robin.search import get_search_results, is_tor_running
from robin.llm import get_llm, refine_query, filter_results, generate_summary


@click.group()
@click.version_option()
def robin():
    """Robin: AI-Powered Dark Web OSINT Tool."""
    pass


@robin.command()
@click.option(
    "--model",
    "-m",
    default="gemini-2.5-flash",
    show_default=True,
    type=click.Choice(
        ["gpt4o", "gpt-4.1", "claude-3-5-sonnet-latest", "llama3.1", "gemini-2.5-flash", "gemini-2.5-flash-preview-09-2025", "gemini-2.5-flash-lite"]
    ),
    help="Select LLM model to use (e.g., gpt4o, claude sonnet 3.5, ollama models)",
)
@click.option("--query", "-q", required=True, type=str, help="Dark web search query")
@click.option(
    "--threads",
    "-t",
    default=5,
    show_default=True,
    type=int,
    help="Number of threads to use for scraping (Default: 5)",
)
@click.option(
    "--output",
    "-o",
    type=str,
    help="Filename to save the final intelligence summary. If not provided, a filename based on the current date and time is used.",
)
def cli(model, query, threads, output):
    """Run Robin in CLI mode.\n
    Example commands:\n
    - robin -m gpt4o -q "ransomware payments" -t 12\n
    - robin --model claude-3-5-sonnet-latest --query "sensitive credentials exposure" --threads 8 --output filename\n
    - robin -m llama3.1 -q "zero days"\n
    """
    # Warn if Tor not detected (we still continue; some links may be clearnet)
    if not is_tor_running():
        click.echo("[WARN] Tor SOCKS proxy not detected at 127.0.0.1:9050. Searches may return empty.")

    try:
        llm = get_llm(model)
    except ValueError as e:
        click.echo(f"[ERROR] {e}")
        return

    # Show spinner while processing the query
    with yaspin(text="Processing...", color="cyan") as sp:
        refined_query = refine_query(llm, query)

        search_results = get_search_results(
            refined_query.replace(" ", "+"), max_workers=threads
        )

        search_filtered = filter_results(llm, refined_query, search_results)

        scraped_results, _meta = scrape_multiple(search_filtered, max_workers=threads)
        sp.ok("✔")

    # Generate the intelligence summary.
    summary = generate_summary(llm, query, scraped_results)

    # Save or print the summary
    if not output:
        now = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"summary_{now}.md"
    else:
        # Respect provided extension; default to .md if none
        if any(output.lower().endswith(ext) for ext in [".md", ".markdown", ".txt", ".json"]):
            filename = output
        else:
            filename = output + ".md"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(summary)
        click.echo(f"\n\n[OUTPUT] Final intelligence summary saved to {filename}")



if __name__ == "__main__":
    robin()
