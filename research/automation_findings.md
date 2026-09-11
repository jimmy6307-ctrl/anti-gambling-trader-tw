# Automation research findings

## 2026-08-25 — breakout hypothesis is not confirmed

Reviewed the latest successful research artifact after transaction costs (0.685% round trip).

### First-breakout family

The 09:35 trend + 20/60-day breakout + RVOL family shows a sharp regime split:

- IS 2024-03-01 to 2025-03-31: every frozen variant in `tw_breakout_oos/summary.csv` has negative mean return and PF < 1.0. Example B20_SECTOR_LOWEXT / 5d: 55 trades, mean -0.62%, PF 0.69.
- OOS 2025-04-01 to 2026-04-01: the same B20_SECTOR_LOWEXT / 5d rule has 41 trades, mean +3.20%, PF 4.49; after removing top-contributing stock 1504 it still has 39 trades, mean +2.42%, PF 3.51.

This is **not** a confirmed edge because the development period is negative. The strong later year is evidence of regime dependence, not evidence that the rule was prospectively selectable.

### Compression add-on

Adding a five-day compression condition makes the sample too small and still fails IS:

- IS: 4 trades, mean -1.33%, PF 0.31.
- OOS: 2 trades, mean +7.45%.
- CONFIRMED=False.

Reject this branch as too sparse / unstable.

### Next hypothesis to test

Do not tune breakout/RVOL thresholds against the already-seen OOS year. Treat 2025-04 to 2026-04 as contaminated for future parameter selection. Next research should test a pre-specified **market-regime gate** (broad market trend/breadth) with rolling or walk-forward validation, because the sign flip between the two years suggests the breakout effect may depend on market regime. Require positive performance across multiple folds rather than one development year and one favorable year.
