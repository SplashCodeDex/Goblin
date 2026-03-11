# Implementation Plan: AutoPilot Enhancements (20250310)

## Phase 1: Environment & Persistence
- [ ] **Task: Research and Setup**
    - [ ] Locate and review `src/robin/database.py` for existing table structures.
    - [ ] Check `docker-compose.yml` for adding a new service.
    - [ ] Create a feature branch for the enhancements.
- [ ] **Task: Database Schema Migration**
    - [ ] Plan: Add `autopilot_state` and `scanned_hashes` tables to `robin.db`.
    - [ ] Act: Update `src/robin/database.py` with the new schema.
    - [ ] Validate: Run a schema verification script to ensure tables are created correctly.
- [ ] **Task: Logic Update for Persistence**
    - [ ] Plan: Modify `AutoPilotScout.__init__` to load state from the database and `scan_content` to persist new hashes.
    - [ ] Act: Update `src/robin/auto_pilot.py`.
    - [ ] Validate: Restart the AutoPilot engine and verify that `_scanned_hashes` and `_seen_ids` are populated from previous runs.
- [ ] **Task: Conductor - User Manual Verification 'Environment & Persistence' (Protocol in workflow.md)**

## Phase 2: Telegram Integration
- [ ] **Task: Telethon Setup & Handler Implementation**
    - [ ] Plan: Install `telethon` and implement `TelegramHandler` using the existing `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.
    - [ ] Act: Update `src/robin/paste_scraper.py` and potentially `requirements.txt` (if it exists).
    - [ ] Validate: Run a standalone script `tests/test_telegram_handler.py` to fetch a sample message from a public channel.
- [ ] **Task: Conductor - User Manual Verification 'Telegram Integration' (Protocol in workflow.md)**

## Phase 3: ML Filtering Microservice
- [ ] **Task: Docker Microservice Setup**
    - [ ] Plan: Update `docker-compose.yml` to include a `credential-digger` service and configure it to run as an API.
    - [ ] Act: Modify `docker-compose.yml`.
    - [ ] Validate: Run `docker-compose up -d` and verify the service is healthy.
- [ ] **Task: ML Filter API Client**
    - [ ] Plan: Update `MLFilterEngine` in `src/robin/ml_filter.py` to call the `credential-digger` API for validation.
    - [ ] Act: Modify `src/robin/ml_filter.py`.
    - [ ] Validate: Process a sample finding and confirm the `FilterResult` contains ML-backed data.
- [ ] **Task: Conductor - User Manual Verification 'ML Filter Microservice' (Protocol in workflow.md)**
