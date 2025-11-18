# Playbook: Credential Leak Investigation

- Query: leaked database credentials companyX
- Steps:
  1. Enter query, pick model, threads, and (optionally) advanced settings.
  2. Review search results, use Preview to choose high-signal sources.
  3. Scrape selected, generate summary.
  4. Export sources, artifacts (JSON/CSV), and STIX.
- Expected artifacts: email addresses, domains, sample credentials.
- Follow-up: pivot on specific domains/emails and rerun.
