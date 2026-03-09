# Implementation Plan: Big Data Ingestion

## Phase 1: Fuzzy Hashing & Deduplication Foundation
- [ ] **Task: SimHash Implementation**
  - [ ] Install `simhash` or implement a custom lightweight SimHash utility.
  - [ ] Create `src/robin/dedup.py` with `calculate_simhash` and `is_duplicate` logic.
- [ ] **Task: Database Schema Update (II)**
  - [ ] Add `content_hash` (BIGINT or TEXT) to the `leaks` table in `src/robin/database.py`.
  - [ ] Implement `check_for_near_duplicates(hash, threshold=0.9)` helper.
- [ ] **Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)**

## Phase 2: Streaming Ingestion Engine
- [ ] **Task: Streaming Requester Implementation**
  - [ ] Update `PasteSource` in `src/robin/paste_scraper.py` to support `_get_request_stream()`.
  - [ ] Implement chunk-by-chunk downloading with memory monitoring.
- [ ] **Task: Blob Management System**
  - [ ] Create `data/blobs/` directory structure.
  - [ ] Implement `src/robin/blob_store.py` for compressed (.gz) storage and retrieval.
  - [ ] Hook `blob_store` into `Watcher._process_new_paste`.
- [ ] **Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)**

## Phase 3: High-Volume Pattern Analysis
- [ ] **Task: Windowed Pattern Scanning**
  - [ ] Update `_analyze_leak` in `src/robin/paste_scraper.py` to support scanning of file handles (streams).
  - [ ] Implement the 1MB sliding window logic to ensure patterns across chunk boundaries are caught.
- [ ] **Task: Parallel Scan Pipeline**
  - [ ] Refactor `credential_patterns.py` to support parallel scanning of discrete text blocks.
  - [ ] Implement `ParallelChunkScan` in `paste_scraper.py` for big files.
- [ ] **Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)**

## Phase 4: Validation & Benchmarking
- [ ] **Task: Stress Testing**
  - [ ] Create `tests/test_big_data.py` with a 50MB synthetic leak generator.
  - [ ] Verify peak RSS memory usage remains under 100MB during ingestion.
- [ ] **Task: End-to-End Dedup Check**
  - [ ] Verify that a near-duplicate paste triggers a "Linked Reference" instead of a new storage entry.
- [ ] **Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)**
