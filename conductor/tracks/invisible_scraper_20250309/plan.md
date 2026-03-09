# Implementation Plan: The Invisible Scraper

## Phase 1: Robust Infrastructure Integration
- [ ] **Task: Browser Scaffolding**
  - [ ] Install `undetected-chromedriver` and `selenium`.
  - [ ] Create `src/robin/browser_engine.py` to manage headless browser lifecycle.
  - [ ] Implement a singleton `BrowserManager` to handle instance pooling and cleanup.
- [ ] **Task: Tor Rotation Enhancement**
  - [ ] Update `src/robin/scrape.py` to include `force_rotate_identity()` method.
  - [ ] Implement a circuit health monitor that tracks success/failure rates per IP.
- [ ] **Task: Conductor - User Manual Verification 'Phase 1' (Protocol in workflow.md)**

## Phase 2: Adaptive Handler Refactoring
- [ ] **Task: Base Class Evolution**
  - [ ] Update `PasteSource` in `src/robin/paste_scraper.py` to support `self.use_browser` flag.
  - [ ] Implement `_get_request_adaptive()` that switches to browser on block detection.
- [ ] **Task: Source-Specific Browser Logic**
  - [ ] Update `PastebinHandler` to handle Cloudflare 'Wait' pages.
  - [ ] Update `ControlCHandler` and `JustPasteItHandler` to handle "Click to Reveal" interactions.
- [ ] **Task: Conductor - User Manual Verification 'Phase 2' (Protocol in workflow.md)**

## Phase 3: Advanced Automation & Stealth
- [ ] **Task: Multi-Circuit Engine**
  - [ ] (Optional/Experimental) Implement support for mapping specific sources to dedicated Tor ports.
- [ ] **Task: Stealth Optimization**
  - [ ] Implement dynamic Canvas/WebGL fingerprint randomization in `BrowserManager`.
  - [ ] Integrate a high-quality User-Agent rotation service (e.g., using `fake-useragent`).
- [ ] **Task: Conductor - User Manual Verification 'Phase 3' (Protocol in workflow.md)**

## Phase 4: Validation & Final Integration
- [ ] **Task: Resilience Testing**
  - [ ] Create `tests/test_invisible_scraper.py` to simulate 403 blocks and verify auto-rotation.
  - [ ] Perform live test against a known Cloudflare-protected paste site.
- [ ] **Task: Final Integration**
  - [ ] Hook the new `BrowserManager` into the main `Watcher` loop.
- [ ] **Task: Conductor - User Manual Verification 'Phase 4' (Protocol in workflow.md)**
