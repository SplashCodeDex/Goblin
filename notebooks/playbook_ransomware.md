# Playbook: Ransomware Payments Investigation

- Query: ransomware payments bitcoin wallet new campaign
- Steps:
  1. Enter query, pick model, tune advanced settings (increase max results).
  2. Use Preview, choose posts with claimed bitcoin wallets.
  3. Scrape selected, generate summary.
  4. Export artifacts and STIX for ingestion into CTI tools.
- Expected artifacts: BTC/ETH addresses, domain IOCs, threat actor mentions.
- Follow-up: enrich crypto addresses using on-chain explorers, pivot on forums.
