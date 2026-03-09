# Specification: Big Data Ingestion

## Overview
"Big Data Ingestion" optimizes Goblin's handling of massive credential dumps and "combolists" that exceed typical memory limits. It introduces fuzzy content hashing for intelligent deduplication across multiple platforms and a streaming architecture for memory-efficient extraction and storage.

## Functional Requirements
1. **Fuzzy Content Hashing (Deduplication):**
   - Implement **SimHash** to detect near-duplicate pastes (e.g., same dump with different headers).
   - Generate a `content_hash` for every ingested leak.
   - Prevent redundant AI analysis and full-content storage if a near-duplicate (>90% match) already exists in the database.

2. **Universal Streaming Architecture:**
   - Refactor handlers to support **Streaming GET** requests.
   - Process data in 1MB chunks to maintain a low, constant memory footprint.
   - Automatically switch to disk-based processing for any download.

3. **High-Performance Pattern Detection:**
   - **Windowed Scanning:** Slide a 1MB window over the stream to detect credentials across chunk boundaries.
   - **Heuristic Scanning Scatter:** Prioritize scanning the beginning and end of large files where headers and summaries typically reside.
   - **Parallel Chunk Scan:** Utilize `ThreadPoolExecutor` to scan multiple chunks of a large file simultaneously for patterns.

4. **Optimized Blob Storage:**
   - Store content exceeding 5MB as compressed `.gz` files in a dedicated `data/blobs/` directory.
   - Store only the file path and metadata in the `leaks` table for large entries.
   - Implement transparent retrieval (reading from DB if small, decompressing from disk if large).

## Non-Functional Requirements
- **Stability:** Prevent `MemoryError` and database lock-ups during 100MB+ ingestions.
- **Scalability:** Ensure deduplication remains fast even as the database grows to thousands of leaks.
- **Data Integrity:** Ensure compressed blobs are correctly linked to their metadata.

## Acceptance Criteria
- [ ] Correctly identifies a near-duplicate paste (e.g., 95% similarity) and avoids redundant storage.
- [ ] Successfully ingests a 50MB test "dump" with < 100MB peak RAM usage.
- [ ] Parallel chunk scanning correctly identifies patterns across a large file.
- [ ] Large leaks are successfully compressed, stored on disk, and retrievable via the UI/API.

## Out of Scope
- Global deduplication across multiple Goblin instances (Single-node focus).
- Advanced database sharding for TB-scale data.
