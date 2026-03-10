# Implementation Plan: Big Data Ingestion

## Phase 1: Fuzzy Hashing & Deduplication Foundation
- [x] **Task: SimHash Implementation**
  - [x] Install `simhash` or implement a custom lightweight SimHash utility.
  - [x] Create `src/robin/dedup.py` with `calculate_simhash` and `is_duplicate` logic.
- [x] **Task: Database Schema Update (II)**
  - [x] Add `content_hash` (BIGINT or TEXT) to the `leaks` table in `src/robin/database.py`.
  - [x] Implement `check_for_near_duplicates(hash, threshold=0.9)` helper.
- [x] **Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)**

## Phase 2: Streaming Ingestion Engine
- [x] **Task: Streaming Requester Implementation**
  - [x] Update `PasteSource` in `src/robin/paste_scraper.py` to support `_get_request_stream()`.
  - [x] Implement chunk-by-chunk downloading with memory monitoring.
- [x] **Task: Blob Management System**
  - [x] Create `data/blobs/` directory structure.
  - [x] Implement `src/robin/blob_store.py` for compressed (.gz) storage and retrieval.
  - [x] Hook `blob_store` into `Watcher._process_new_paste`.
- [x] **Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)**

## Phase 3: High-Volume Pattern Analysis
- [x] **Task: Windowed Pattern Scanning**
  - [x] Update `_analyze_leak` in `src/robin/paste_scraper.py` to support scanning of file handles (streams).
  - [x] Implement the 1MB sliding window logic to ensure patterns across chunk boundaries are caught.
- [x] **Task: Parallel Scan Pipeline**
  - [x] Refactor `credential_patterns.py` to support parallel scanning of discrete text blocks.
  - [x] Implement `ParallelChunkScan` in `paste_scraper.py` for big files.
- [x] **Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)**

## Phase 4: Validation & Benchmarking
- [x] **Task: Stress Testing**
  - [x] Create `tests/test_big_data.py` with a 50MB synthetic leak generator.
  - [x] Verify peak RSS memory usage remains under 100MB during ingestion.
- [x] **Task: End-to-End Dedup Check**
  - [x] Verify that a near-duplicate paste triggers a "Linked Reference" instead of a new storage entry.
- [x] **Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)**
