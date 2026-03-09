# Implementation Plan: The Immediate Leak Zone Scraper

## Phase 1: Foundation & Base Module
- [ ] **Task: Module Scaffolding**
  - [ ] Create `src/robin/paste_scraper.py` with base `PasteScraper` class.
  - [ ] Define the `PasteSource` abstract base class to standardize site handlers.
  - [ ] Implement shared utility methods for Tor-routing and rate-limiting.
- [ ] **Task: Database Schema Enhancement**
  - [ ] Update `src/robin/database.py` to support "Full Capture" for leaks.
  - [ ] Add `paste_metadata` table for tracking source-specific fields (e.g., paste ID, expiration).
- [ ] **Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)**

## Phase 2: Site-Specific Handlers (The Best 7)
- [ ] **Task: Clear-Web Handlers (Part A)**
  - [ ] Implement `PastebinHandler` with robust retry/rotation logic.
  - [ ] Implement `PasteeeHandler` (utilizing public API if available, or scraping).
  - [ ] Implement `ControlCHandler` and `JustPasteItHandler`.
- [ ] **Task: Clear-Web Handlers (Part B)**
  - [ ] Implement `RentryHandler` and `DumpToHandler`.
- [ ] **Task: Dark-Web (Onion) Handlers**
  - [ ] Implement `DeepPasteHandler` and `StrongholdHandler`.
  - [ ] Verify Tor-routing for all .onion requests.
- [ ] **Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)**

## Phase 3: Hybrid Ingestion & Monitoring Engine
- [ ] **Task: Watcher Engine Implementation**
  - [ ] Create a `Watcher` class to poll "Recent" feeds of all handlers.
  - [ ] Implement an asynchronous loop for continuous background monitoring.
- [ ] **Task: Query-Driven Integration**
  - [ ] Update `src/robin/search.py` to include paste sites in the unified search flow.
  - [ ] Ensure keywords/domains are correctly passed to site-specific search functions.
- [ ] **Task: Telegram Log Scraper (Advanced)**
  - [ ] Implement basic Telegram scraper for identified "Log" channels using `Telethon`.
  - [ ] Map Telegram message data to the standard leak format.
- [ ] **Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)**

## Phase 4: AI Pipeline & Verification
- [ ] **Task: Automated Analysis Integration**
  - [ ] Hook `src/robin/credential_patterns.py` into the ingestion pipeline.
  - [ ] Implement automatic `LLM` summarization for captured leaks.
  - [ ] Add confidence/relevance scoring logic based on discovered patterns.
- [ ] **Task: Final Integration & Tests**
  - [ ] Create `tests/test_paste_scraper.py` for unit testing handlers.
  - [ ] Perform end-to-end integration tests (Scrape -> Analyze -> Store).
- [ ] **Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)**
