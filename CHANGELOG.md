# Changelog

All notable changes to the Robin OSINT Tool project will be documented in this file.

## [Unreleased]

### Added
- **Streaming Summary Support**: Implemented Server-Sent Events (SSE) streaming for real-time summary generation in web UI
  - Detailed mode now uses `/api/cache_scraped` and `/api/summary_stream` endpoints
  - Provides real-time feedback as summary is generated
  - Falls back to batch mode if streaming fails
  - Non-detailed mode continues to use batch summary generation
- **Enhanced Artifact Extraction**: Significantly expanded IOC and sensitive data detection
  - Added IPv6 address detection
  - Added URL extraction
  - Added file hash detection (MD5, SHA1, SHA256)
  - Added CVE identifier extraction
  - Added email:password combination detection
  - Added API key pattern detection
  - Updated MISP event generation to support all new artifact types
- **Error Logging**: Added proper error logging to 4 empty catch blocks
  - Model status check failures now logged
  - Artifact extraction failures now logged
  - URL parsing failures in charts now logged
  - Playbook localStorage parsing failures now logged

### Fixed
- **Critical**: Fixed missing summary generation in web UI after scraping completes
  - The `onScrape()` function now properly calls `/api/summary` endpoint
  - Summary, STIX, and MISP data are now correctly populated in the UI
  - Fixed corrupted line formatting with literal `\n` characters
- **Critical**: Fixed missing API_BASE export and import
  - Exported API_BASE from `web/lib/api.ts`
  - Imported API_BASE in `web/app/(investigate)/page.tsx`
- **Code Quality**: Renamed misleading `dummy` variable to `citation_instruction` in LLM prompt template
- **Configuration**: Frontend now uses `NEXT_PUBLIC_API_BASE_URL` environment variable for API base URL
  - Defaults to `http://localhost:8000/api` instead of hardcoded `8001`
  - Properly respects environment configuration in Docker deployments
- **Logging**: Changed debug log statement from `logger.info` to `logger.debug` in API server
- **Consistency**: Fixed port configuration inconsistency in `debug_search.py` (8001 → 8000)

### Changed
- Migrated from local `ApiKeyManager` implementation to external package `@splashcodex/api-key-manager@^5.0.0`
- Updated `web/package.json` with new dependency
- Enhanced `_extract_iocs()` function in `src/robin/llm.py` with comprehensive pattern matching
- Enhanced `/api/extract` endpoint with all new artifact types

### Documentation
- Updated `README.md` to document frontend environment variables
- Updated `docs/DEPLOYMENT.md` with frontend configuration details
- Added this CHANGELOG.md to track project changes

## [Previous Releases]
See GitHub releases for older version history.
