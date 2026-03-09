# Specification: The Immediate Leak Zone Scraper

## Overview
The "Immediate Leak Zone" is a specialized scraping module for Goblin designed to capture real-time credential leaks and sensitive data dumps from paste sites, dump bins, and Telegram log aggregators. This feature bridges the gap between archival breach data and active, "hot" leaks.

## Functional Requirements
1. **Multi-Platform Scraper:**
   - Support for Clear Web sites: Pastebin.com, Paste.ee, ControlC.com, JustPaste.it, Rentry.co, Dump.to.
   - Support for Dark Web sites: DeepPaste, Stronghold, and other Onion-based bins.
   - Specialized Telegram Log Integration: Ability to monitor known "Log" channels (e.g., Moon Cloud, Observer Cloud).

2. **Hybrid Ingestion Engine:**
   - **Watcher Mode:** Background polling of "Recent" or "Latest" feeds for the identified platforms.
   - **Query Mode:** Targeted scraping of these platforms based on specific domains or keywords.

3. **Data Management:**
   - **Full Capture:** Store the complete text content of identified leaks in the `robin.db`.
   - **Deduplication:** Prevent redundant storage of identical leaks across different platforms.

4. **AI-Driven Pipeline:**
   - **Pattern Matching:** Automatic detection of credentials (API Keys, PII, Passwords) using `credential_patterns.py`.
   - **Summarization:** Generate concise LLM summaries for captured leaks.
   - **Scoring:** Assign a relevance/confidence score based on the density of discovered patterns.

## Non-Functional Requirements
- **Anonymity:** All requests to .onion sites and sensitive clear-web targets must route through the existing Tor-SOCKS proxy.
- **Performance:** Asynchronous processing using ThreadPoolExecutor to handle high volume without blocking the main engine.
- **Resilience:** Robust retry logic and error handling for transient site downtime.

## Acceptance Criteria
- [ ] Successfully scrapes recent pastes from at least 3 clear-web targets.
- [ ] Successfully routes Onion-based paste scraping through Tor.
- [ ] Correctly identifies and stores "full capture" data in the database.
- [ ] AI analysis (summarization/patterns) is triggered automatically upon ingestion.
- [ ] Metadata (source, timestamp, relevance) is correctly indexed.

## Out of Scope
- Real-time automated notification systems (e.g., Slack/Email alerts).
- Advanced image-based leak analysis beyond existing OCR capabilities.
