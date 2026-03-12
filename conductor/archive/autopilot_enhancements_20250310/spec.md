# Specification: AutoPilot Enhancements (20250310)

## Overview
Elevate the `AutoPilot` module from a memory-based volatile service to a robust, persistent, and high-fidelity discovery engine. This includes adding database persistence for state, implementing real-time Telegram monitoring, and integrating `Credential Digger` via a Docker-based microservice.

## Functional Requirements
- **State Persistence (SQLite):**
    - Migrate `_seen_ids` and `_scanned_hashes` from memory to `robin.db`.
    - Create new tables `autopilot_state` and `scanned_hashes` in `robin.db`.
    - Ensure `AutoPilotScout` resumes from its last known state upon restart.
- **Telegram Integration (Telethon):**
    - Implement the `TelegramHandler` in `src/robin/paste_scraper.py` using the `Telethon` library.
    - Configure monitoring for a list of known log-aggregator channels.
    - Handle session management and API authentication using existing configuration.
- **ML Filter (Credential Digger Microservice):**
    - Deploy `Credential Digger` in a separate Docker container.
    - Update `MLFilterEngine` to call the Credential Digger API for high-fidelity filtering.
    - Maintain rule-based filtering as a local, fast fallback.

## Acceptance Criteria
- `AutoPilot` state persists after service restarts.
- `TelegramHandler` successfully fetches messages from specified channels.
- `MLFilterEngine` correctly communicates with the `Credential Digger` microservice.
- All existing tests pass.

## Tech Stack Changes
- Add `telethon` to dependencies.
- Update `docker-compose.yml` to include `credential-digger` service.
- New database tables in `robin.db`.
