# 2026-08-25 RVOL robustness check

Using the existing 2025-04-01~2026-04-01 5-minute backtest trades, I tested whether simply tightening RVOL rescues the prior strong-sector/momentum idea. This is exploratory only; it is not a new validated strategy.

## Result

For fixed 5-day holds across the existing three 09:30 gain bands, requiring RVOL >= 2.0 produced 443 unique signals, average net return +0.635%, median -0.685%, win rate 42.2%, PF 1.296 after the existing 0.685% round-trip cost assumption.

However, removing 2408 Nanya Technology reduced the result to 427 signals, average net return +0.078%, PF 1.036. Therefore the apparent improvement still depends heavily on one stock and fails the pre-declared robustness requirement.

Monthly results after removing 2408 were also unstable: strongly negative months included 2025-04 (-4.13% average), 2025-08 (-2.41%), 2025-11 (-4.47%), 2025-12 (-1.77%), and 2026-03 (-3.24%), while positive performance was concentrated in several other months.

## Decision

Reject `strong sector + 09:30 momentum + RVOL >= 2 + 5-day hold` as a standalone edge. Do not notify or promote it as actionable. Continue with the separately frozen first-breakout/OOS research path rather than parameter-tuning this failed family.