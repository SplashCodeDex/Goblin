# Changelog

All notable changes to the Robin OSINT Tool project will be documented in this file.

## [Unreleased]

### Fixed
- **Critical**: Fixed missing summary generation in web UI after scraping completes
  - The `onScrape()` function now properly calls `/api/summary` endpoint
  - Summary, STIX, and MISP data are now correctly populated in the UI
  - Fixed corrupted line formatting with literal `\n` characters
- **Code Quality**: Renamed misleading `dummy` variable to `citation_instruction` in LLM prompt template
- **Configuration**: Frontend now uses `NEXT_PUBLIC_API_BASE_URL` environment variable for API base URL
  - Defaults to `http://localhost:8000/api` instead of hardcoded `8001`
  - Properly respects environment configuration in Docker deployments
- **Logging**: Changed debug log statement from `logger.info` to `logger.debug` in API server
- **Consistency**: Fixed port configuration inconsistency in `debug_search.py` (8001 → 8000)

### Changed
- Migrated from local `ApiKeyManager` implementation to external package `@splashcodex/api-key-manager@^5.0.0`
- Updated `web/package.json` with new dependency

### Documentation
- Updated `README.md` to document frontend environment variables
- Updated `docs/DEPLOYMENT.md` with frontend configuration details
- Added this CHANGELOG.md to track project changes

## [Previous Releases]
See GitHub releases for older version history.
