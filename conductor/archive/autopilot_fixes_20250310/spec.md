# Specification: AutoPilot Bug Fixes (20250310)

## Overview
Resolve several regression errors in the `AutoPilot` module (`src/robin/auto_pilot.py`) discovered during recent runs. This track focuses on fixing `TypeErrors` and an `AttributeError` while proactively reviewing the module for similar issues.

## Functional Requirements
- **Fix `PasteWatcher` Initialization:** Update `get_paste_stream` in `auto_pilot.py` to correctly initialize `Watcher` with the required `scraper` argument.
- **Correct Method Calls:** 
    - Fix `start_cicd_sweep()` call to correctly handle or remove the `limit` keyword argument.
    - Fix `scan_exposed_databases()` call to correctly handle or remove the `limit` keyword argument.
- **Repair ML Integration:** 
    - Investigate why `MLFilterEngine` is missing the `is_sensitive` attribute.
    - Update `src/robin/ml_filter.py` or the call site in `auto_pilot.py` to ensure findings are filtered correctly.
- **Proactive Audit:** Review `src/robin/auto_pilot.py` for other potential `TypeError` or `AttributeError` regressions.

## Acceptance Criteria
- `AutoPilot` service initializes and runs background watchers without `TypeError`.
- CI/CD and Database sweepers execute successfully.
- Findings are processed through the ML filter without `AttributeError`.
- Existing tests in `tests/` pass without regressions.

## Out of Scope
- Adding new scraping modules or data sources.
- Large-scale refactoring of the `MLFilterEngine` architecture.
