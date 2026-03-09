# Tech Stack: Goblin

## Core Infrastructure
- **Python (Backend):** Core OSINT engine for scraping, searching, and analysis.
- **FastAPI:** High-performance REST API for backend-frontend communication.
- **Next.js (Frontend):** React-based framework for the dashboard and search interface.
- **Tailwind CSS & Shadcn/UI:** Responsive and modern UI/UX design.
- **SQLite:** Local database (robin.db) for storing search history and discovered leaks.

## OSINT & Intelligence
- **Tor integration:** Native SOCKS proxy routing for all dark-web requests.
- **Scraping Engine:** BeautifulSoup4, Requests (with retry logic), and specialized handlers.
- **OCR & Document Extraction:** Pytesseract (for images) and pdfplumber (for PDFs).
- **ML & AI Integration:** Support for OpenAI, Anthropic, and local Ollama models for analyzing data.

## Identity & API Management
- **GitHub Dorking:** Integration via GitHub search API.
- **Breach Repositories:** HIBP, IntelX, Snusbase, and DeHashed API support.

## Development & Deployment
- **Docker & Docker Compose:** Containerization for both backend and frontend.
- **PowerShell Scripts:** Local environment management (`start_backend.ps1`, `start_frontend.ps1`).
- **Pytest:** Backend unit and integration testing.
