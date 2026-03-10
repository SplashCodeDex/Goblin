# Implementation Plan: AutoPilot Bug Fixes (20250310)

## Phase 1: Research and Reproduction
- [ ] **Task: Research and Analysis**
    - [ ] Locate `Watcher` class definition and check `__init__` signature in `src/robin/scrape.py` or similar.
    - [ ] Locate `start_cicd_sweep` and `scan_exposed_databases` definitions (likely in `cicd_hunter.py` and `leaklooker_engine.py`).
    - [ ] Locate `MLFilterEngine` in `src/robin/ml_filter.py` and check for the `is_sensitive` method.
    - [ ] Map all call sites in `src/robin/auto_pilot.py` for these methods.
- [ ] **Task: Empirical Reproduction**
    - [ ] Create a minimal reproduction script `tests/repro_autopilot_crash.py` that triggers the reported errors.
- [ ] **Task: Conductor - User Manual Verification 'Research and Reproduction' (Protocol in workflow.md)**

## Phase 2: Execution - Fixing TypeErrors
- [ ] **Task: Fix `PasteWatcher` Initialization**
    - [ ] Plan: Update `PasteWatcher` instantiation in `auto_pilot.py` to include the required `scraper` argument.
    - [ ] Act: Modify `src/robin/auto_pilot.py`.
    - [ ] Validate: Run `tests/repro_autopilot_crash.py` to confirm the fix.
- [ ] **Task: Fix Sweeper Call Signatures**
    - [ ] Plan: Update `start_cicd_sweep` and `scan_exposed_databases` calls to match their definitions or update definitions to accept the `limit` keyword.
    - [ ] Act: Apply surgical fixes to `src/robin/auto_pilot.py` or respective engines.
    - [ ] Validate: Run reproduction script.
- [ ] **Task: Conductor - User Manual Verification 'Fixing TypeErrors' (Protocol in workflow.md)**

## Phase 3: Execution - ML Filter Fix and Proactive Review
- [ ] **Task: Repair `MLFilterEngine` Integration**
    - [ ] Plan: Restore or implement `is_sensitive` in `MLFilterEngine` (or update calls to the correct method name).
    - [ ] Act: Modify `src/robin/ml_filter.py` or `src/robin/auto_pilot.py`.
    - [ ] Validate: Verify processing of a sample finding.
- [ ] **Task: Proactive Audit and Final Validation**
    - [ ] Plan: Conduct a final audit of `src/robin/auto_pilot.py` for similar signature mismatches.
    - [ ] Act: Finalize all fixes.
    - [ ] Validate: Run `pytest tests/test_paste_scraper.py` and other relevant existing tests.
- [ ] **Task: Conductor - User Manual Verification 'ML Filter and Final Audit' (Protocol in workflow.md)**
