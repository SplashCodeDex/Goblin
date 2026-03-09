# Specification: The Invisible Scraper

## Overview
"The Invisible Scraper" is a major robustness upgrade for Goblin's Paste Site & Dump Bin module. It introduces an adaptive scraping engine that switches between standard requests and an undetected headless browser when encountering anti-bot measures (Cloudflare, CAPTCHAs). It also implements a sophisticated multi-circuit Tor rotation strategy.

## Functional Requirements
1. **Adaptive Scraping Engine:**
   - Default to high-speed `requests` + `Tor SOCKS` for efficiency.
   - Detect blocking signals: `403 Forbidden`, `429 Too Many Requests`, or Cloudflare "Under Attack" patterns.
   - Automatically trigger an `undetected-chromedriver` session upon block detection to solve/pass JavaScript challenges.

2. **Advanced Tor & Session Management:**
   - **Reactive Rotation:** Rotate Tor identity immediately upon hitting a block.
   - **Frequent Rotation:** Implement a background cycle to rotate Tor circuits every 10-20 successful scrapes to prevent fingerprinting.
   - **Multi-Circuit Capability:** Support parallel sessions through different Tor circuits where infrastructure allows.

3. **Intelligent JS Interactions:**
   - **Wait Conditions:** Use Playwright/Selenium to wait for content to render after Cloudflare challenges.
   - **Action Simulation:** Handle "Click to Reveal," "Expand," and auto-scrolling for lazy-loaded pastes.
   - **User-Agent Masquerade:** Dynamic rotation of high-quality User-Agent strings.

4. **Resilient Error Pipeline:**
   - **Immediate Retry:** On block, retry once with a new Tor circuit and a fresh User-Agent.
   - **Escalation Path:** Log persistent "Hard Walls" for manual investigation and temporarily back-off the source.

## Non-Functional Requirements
- **Efficiency:** The headless browser should only be invoked as a fallback to minimize CPU/Memory overhead.
- **Stealth:** Utilize `undetected-chromedriver` patches to evade common headless detection scripts.
- **Stability:** Ensure browser instances are properly closed/recycled to prevent memory leaks.

## Acceptance Criteria
- [ ] Successfully bypasses a Cloudflare "Wait" page on at least 1 target site.
- [ ] Automatically rotates Tor identity after a 403 error.
- [ ] Correctly interacts with "Click to Reveal" buttons during a scrape.
- [ ] Browser instances are successfully spawned, used for extraction, and terminated.

## Out of Scope
- Solving complex image-based CAPTCHAs (H-Captcha, reCAPTCHA v3) without external APIs.
- Full residential proxy integration (focus remains on Tor).
