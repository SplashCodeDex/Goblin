<div align="center">
   <img src=".github/assets/logo.png" alt="Logo" width="300">
   <br><a href="https://github.com/apurvsinghgautam/robin/actions/workflows/binary.yml"><img alt="Build" src="https://github.com/apurvsinghgautam/robin/actions/workflows/binary.yml/badge.svg"></a> <a href="https://github.com/apurvsinghgautam/robin/releases"><img alt="GitHub Release" src="https://img.shields.io/github/v/release/apurvsinghgautam/robin"></a> <a href="https://hub.docker.com/r/apurvsg/robin"><img alt="Docker Pulls" src="https://img.shields.io/docker/pulls/apurvsg/robin"></a>
   <h1>Robin: AI-Powered Dark Web OSINT Tool</h1>

   <p>Robin is an AI-powered tool for conducting dark web OSINT investigations. It leverages LLMs to refine queries, filter search results from dark web search engines, and provide an investigation summary.</p>
   <a href="#installation">Installation</a> &bull; <a href="#usage">Usage</a> &bull; <a href="#contributing">Contributing</a> &bull; <a href="#acknowledgements">Acknowledgements</a><br><br>
</div>

![Demo](.github/assets/screen.png)
![Demo](.github/assets/screen-ui.png)


---

## How it works

Data flow: refine -> search -> filter -> select -> preview -> scrape -> summarize -> export

- Refine: LLM refines your plain query for dark web search engines.
- Search: queries multiple onion search engines over Tor.
- Filter: LLM selects the most relevant results.
- Select: you pick which results to investigate further.
- Preview: optional one-click previews of selected pages to see early snippets.
- Scrape: fetch and extract text (Tor for .onion, clearnet otherwise).
- Summarize: token-aware chunked summarization with provenance and IOC hints.
- Export: download sources (CSV/JSON) and the summary (Markdown).

## Features

- ⚙️ **Modular Architecture** – Clean separation between search, scrape, and LLM workflows.
- 🤖 **Multi-Model Support** – Easily switch between OpenAI, Claude, Gemini or local models like Ollama.
- 💻 **CLI-First Design** – Built for terminal warriors and automation ninjas.
- 🐳 **Docker-Ready** – API server for integrations and optional Next.js frontend.
- 📝 **Custom Reporting** – Save investigation output to file for reporting or further analysis.
- 🧩 **Extensible** – Easy to plug in new search engines, models, or output formats.

---

## ⚠️ Disclaimer
> This tool is intended for educational and lawful investigative purposes only. Accessing or interacting with certain dark web content may be illegal depending on your jurisdiction. The author is not responsible for any misuse of this tool or the data gathered using it.
>
> Use responsibly and at your own risk. Ensure you comply with all relevant laws and institutional policies before conducting OSINT investigations.
>
> Additionally, Robin leverages third-party APIs (including LLMs). Be cautious when sending potentially sensitive queries, and review the terms of service for any API or model provider you use.

## Installation
> [!NOTE]
> The tool needs Tor to do the searches. You can install Tor using `apt install tor` on Linux/Windows(WSL) or `brew install tor` on Mac. Once installed, confirm if Tor is running in the background.

> [!TIP]
> You can provide OpenAI or Anthropic or Google API key by either creating .env file (refer to sample env file in the repo) or by setting env variables in PATH.
>
> For Ollama, provide `http://host.docker.internal:11434` as Ollama URL if running using docker image method or `http://127.0.0.1:11434` for other methods.

### Docker (API Server)

```bash
docker compose up --build
# FastAPI: http://localhost:8000/api/health
# Next.js (optional web shell): http://localhost:3000
```

### Release Binary (CLI Mode)

- Download the appropriate binary for your system from the [latest release](https://github.com/apurvsinghgautam/robin/releases/latest)
- Unzip the file, make it executable 
```bash
chmod +x robin
```

- Run the binary as:
```bash
robin cli --model gpt-4.1 --query "ransomware payments"
```

### Using Python (Development Version)

- With `Python 3.10+` installed, run the following:

```bash
pip install -r requirements.txt
# Linux/Mac
PYTHONPATH=src python -m robin.cli cli -m gemini-2.5-flash -q "ransomware payments" -t 12
# Windows PowerShell
$env:PYTHONPATH = "$PWD/src"; python -m robin.cli cli -m gemini-2.5-flash -q "ransomware payments" -t 12
# Windows cmd
set PYTHONPATH=%CD%\src && python -m robin.cli cli -m gemini-2.5-flash -q "ransomware payments" -t 12
```

#### Run the API server (no Streamlit UI)

```bash
# Linux/Mac
PYTHONPATH=src python -m uvicorn robin.api.server:app --reload --port 8000
# Windows PowerShell
$env:PYTHONPATH = "$PWD/src"; python -m uvicorn robin.api.server:app --reload --port 8000
# Windows cmd
set PYTHONPATH=%CD%\src && python -m uvicorn robin.api.server:app --reload --port 8000
```

#### Environment variables
Create a `.env` from `.env.example` or export them in your shell:

- OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY (set the one(s) you plan to use)
- OLLAMA_BASE_URL (e.g., http://127.0.0.1:11434)
- TOR_SOCKS_HOST and TOR_SOCKS_PORT (default 127.0.0.1:9050)
- MAX_SCRAPE_CHARS (default 1200)

Note: The app will warn if Tor SOCKS is not detected; searches may return empty without Tor.

Troubleshooting
- ModuleNotFoundError: Use module path robin.api.server:app and ensure PYTHONPATH=src.
- Tor not detected: Start Tor with SOCKS at 127.0.0.1:9050 or set TOR_SOCKS_HOST/PORT.
- GitHub API rate limit: Set GITHUB_TOKEN in .env.
- Removed Streamlit UI: use the CLI or FastAPI endpoints instead.


Model requirements
- gpt4o, gpt-4.1: requires OPENAI_API_KEY
- claude-3-5-sonnet-latest: requires ANTHROPIC_API_KEY
- gemini-2.5-flash: requires GOOGLE_API_KEY
- llama3.1: requires OLLAMA_BASE_URL

---

## Usage [Updated]

```bash
Robin: AI-Powered Dark Web OSINT Tool

options:
  -h, --help            show this help message and exit
  --model {gpt4o,gpt-4.1,claude-3-5-sonnet-latest,llama3.1,gemini-2.5-flash}, -m {gpt4o,gpt-4.1,claude-3-5-sonnet-latest,llama3.1,gemini-2.5-flash}
                        Select LLM model (e.g., gpt4o, claude sonnet 3.5, ollama models, gemini 2.5 flash)
  --query QUERY, -q QUERY
                        Dark web search query
  --threads THREADS, -t THREADS
                        Number of threads to use for scraping (Default: 5)
  --output OUTPUT, -o OUTPUT
                        Filename to save the final intelligence summary. If not provided, a filename based on the
                        current date and time is used.

Example commands:
 - robin -m gpt4o -q "ransomware payments" -t 12
 - robin --model claude-3-5-sonnet-latest --query "sensitive credentials exposure" --threads 8 --output filename
 - robin -m llama3.1 -q "zero days"
 - robin -m gemini-2.5-flash -q "zero days"
```

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

- Fork the repository
- Create your feature branch (git checkout -b feature/amazing-feature)
- Commit your changes (git commit -m 'Add some amazing feature')
- Push to the branch (git push origin feature/amazing-feature)
- Open a Pull Request

Open an Issue for any of these situations:
- If you spot a bug or bad code
- If you have a feature request idea
- If you have questions or doubts about usage

---

## Acknowledgements

- Idea inspiration from [Thomas Roccia](https://x.com/fr0gger_) and his demo of [Perplexity of the Dark Web](https://x.com/fr0gger_/status/1908051083068645558).
- Tools inspiration from my [OSINT Tools for the Dark Web](https://github.com/apurvsinghgautam/dark-web-osint-tools) repository.
- LLM Prompt inspiration from [OSINT-Assistant](https://github.com/AXRoux/OSINT-Assistant) repository.
- Logo Design by my friend [Tanishq Rupaal](https://github.com/Tanq16/)

