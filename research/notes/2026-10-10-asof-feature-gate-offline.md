# 2026-10-10 — as-of corporate-action feature contract (offline only)

## Why this matters
The previous 25-stock 5-minute source is not reliable for official close and therefore cannot establish previous close, MA20/MA60 or ex-right-adjusted breakout levels. Previously reviewed 2025-04–2026-04 is not a sealed holdout. No legacy strategy was rerun and no P&L is claimed.

## Offline prototype and result
A pure-stdlib Python contract prototype was built and exercised locally, with **20/20 synthetic unit tests passing**. It requires a prior-day official close published before the signal, a caller-attested complete official action interval, verified prior trading day, official previous close and ex-reference-price anchors, valid Taiwan timezone, no duplicate event/day, and no future announcement or not-yet-effective ex-date. It rejects unsupported capital reductions and unofficial source labels. On an effective ex-date it uses the official reference price as the signal baseline and adjusts only earlier historical closes by the reference/previous-close factor. It always returns `strategy_gate=BLOCKED` and explicitly does **not** calculate dividend-inclusive shareholder returns.

This is **only a software-contract test using synthetic values**. No live corporate-action records, independent minute/tick data, full historical universe or real fills were validated. The code upload to the research branch was **blocked by connector safety checks**, so the prototype and tests are **not committed or CI-wired**. Do not describe them as a GitHub CI success.

## Remaining risk
The caller's `attested_complete` flag cannot prove the official event tape is actually complete. Historical official data need an externally auditable manifest with original bytes, SHA256, source, retrieval/publication timestamps, and explicit stock/date coverage. A day with no action must be backed by verified coverage, not assumed from a missing row. The previous trading day must be checked against an independently verified trading calendar, not inferred from an incomplete stock CSV. Reference-price normalization is not a shareholder total-return model.

## Next mandatory gate
Secure authorized complete TWSE/TPEx historical ex-right/dividend calculation records and an independent minute/tick source. Verify predeclared actual events (official previous close, reference price, effective date, publication time), 13:30 auction anchor and timestamp semantics, then construct a PIT universe and sealed holdout. Until then: **DATA GATE BLOCKED; NO CONFIRMED EDGE; no user notification**.
