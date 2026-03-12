# Implementation Plan: AutoPilot Enhancements (20250310)

## Phase 1: Environment & Persistence
- [x] **Task: Research and Setup**
    - [x] Locate and review `src/robin/database.py` for existing table structures.
    - [x] Check `docker-compose.yml` for adding a new service.
    - [x] Create a feature branch for the enhancements.
- [x] **Task: Database Schema Migration**
    - [x] Plan: Add `autopilot_state` and `scanned_hashes` tables to `robin.db`.
    - [x] Act: Update `src/robin/database.py` with the new schema.
    - [x] Validate: Run a schema verification script to ensure tables are created correctly.
- [x] **Task: Logic Update for Persistence**
    - [x] Plan: Modify `AutoPilotScout.__init__` to load state from the database and `scan_content` to persist new hashes.
    - [x] Act: Update `src/robin/auto_pilot.py`.
    - [x] Validate: Restart the AutoPilot engine and verify that `_scanned_hashes` and `_seen_ids` are populated from previous runs.
- [x] **Task: Conductor - User Manual Verification 'Environment & Persistence' (Protocol in workflow.md)**

## Phase 2: Telegram Integration
- [x] **Task: Telethon Setup & Handler Implementation**
    - [x] Plan: Install `telethon` and implement `TelegramHandler` using the existing `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`.
    - [x] Act: Update `src/robin/paste_scraper.py` and potentially `requirements.txt` (if it exists).
    - [x] Validate: Run a standalone script `tests/test_telegram_handler.py` to fetch a sample message from a public channel.
- [x] **Task: Conductor - User Manual Verification 'Telegram Integration' (Protocol in workflow.md)**

## Phase 3: ML Filtering Microservice
- [x] **Task: Docker Microservice Setup**
    - [x] Plan: Update `docker-compose.yml` to include a `credential-digger` service and configure it to run as an API.
    - [x] Act: Modify `docker-compose.yml`.
    - [x] Validate: Run `docker-compose up -d` and verify the service is healthy.
- [x] **Task: ML Filter API Client**
    - [x] Plan: Update `MLFilterEngine` in `src/robin/ml_filter.py` to call the `credential-digger` API for validation.
    - [x] Act: Modify `src/robin/ml_filter.py`.
    - [x] Validate: Process a sample finding and confirm the `FilterResult` contains ML-backed data.
- [x] **Task: Conductor - User Manual Verification 'ML Filter Microservice' (Protocol in workflow.md)**
