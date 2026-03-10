# Implementation Plan: AutoPilot Bug Fixes (20250310)

## Phase 1: Research and Reproduction
- [x] **Task: Research and Analysis**
    - [x] Locate `Watcher` class definition and check `__init__` signature in `src/robin/scrape.py` or similar.
    - [x] Locate `start_cicd_sweep` and `scan_exposed_databases` definitions (likely in `cicd_hunter.py` and `leaklooker_engine.py`).
    - [x] Locate `MLFilterEngine` in `src/robin/ml_filter.py` and check for the `is_sensitive` method.
    - [x] Map all call sites in `src/robin/auto_pilot.py` for these methods.
- [x] **Task: Empirical Reproduction**
    - [x] Create a minimal reproduction script `tests/repro_autopilot_crash.py` that triggers the reported errors.
- [x] **Task: Conductor - User Manual Verification 'Research and Reproduction' (Protocol in workflow.md)**

## Phase 2: Execution - Fixing TypeErrors
- [x] **Task: Fix `PasteWatcher` Initialization**
    - [x] Plan: Update `PasteWatcher` instantiation in `auto_pilot.py` to include the required `scraper` argument.
    - [x] Act: Modify `src/robin/auto_pilot.py`.
    - [x] Validate: Run `tests/repro_autopilot_crash.py` to confirm the fix.
- [x] **Task: Fix Sweeper Call Signatures**
    - [x] Plan: Update `start_cicd_sweep` and `scan_exposed_databases` calls to match their definitions or update definitions to accept the `limit` keyword.
    - [x] Act: Apply surgical fixes to `src/robin/auto_pilot.py` or respective engines.
    - [x] Validate: Run reproduction script.
- [x] **Task: Conductor - User Manual Verification 'Fixing TypeErrors' (Protocol in workflow.md)**

## Phase 3: Execution - ML Filter Fix and Proactive Review
- [x] **Task: Repair `MLFilterEngine` Integration**
    - [x] Plan: Restore or implement `is_sensitive` in `MLFilterEngine` (or update calls to the correct method name).
    - [x] Act: Modify `src/robin/ml_filter.py` or `src/robin/auto_pilot.py`.
    - [x] Validate: Verify processing of a sample finding.
- [x] **Task: Proactive Audit and Final Validation**
    - [x] Plan: Conduct a final audit of `src/robin/auto_pilot.py` for similar signature mismatches.
    - [x] Act: Finalize all fixes.
    - [x] Validate: Run `pytest tests/test_paste_scraper.py` and other relevant existing tests.
- [x] **Task: Conductor - User Manual Verification 'ML Filter and Final Audit' (Protocol in workflow.md)**
