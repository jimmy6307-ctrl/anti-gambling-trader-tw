# 2026-10-08 — B20 portfolio overlap + period-boundary audit

Frozen signal: 09:35 B20_SECTOR_LOWEXT, 09:45 next-bar open, hold 5 trading sessions, cost 0.685%. Source: successful Actions run 37713051939 artifact `tw_breakout_alpha_diagnostic/signals_and_controls.csv` and cached 5-minute CSVs. No retuning.

Reconstructed each signal's exit date from its own stock's observed sessions; excluded IS entries whose exits cross 2025-03-31 and OOS entries whose exits cross 2026-04-01. Enforced at most ONE position across the entire portfolio, and no new entry until the next session after exit.

| Period | Trades | Mean net | PF | Market-matched excess | Remove top stock: mean / PF | Positive months |
|---|---:|---:|---:|---:|---:|---:|
| IS (2024-03 to 2025-03) | 20 | -1.532% | 0.219 | -0.546% | -1.742% / 0.156 | 5 / 11 |
| OOS (2025-04 to 2026-04) | 18 | +2.589% | 3.109 | +2.472% | +1.279% / 1.984 | 7 / 10 |

OOS remains positive, but IS is materially negative and both periods have fewer than 30 nonoverlapping positions. **Not confirmed; do not notify user as a trading strategy.** OOS has already been inspected many times and cannot be considered pristine for new parameter tuning. Per-trade equity MDD is not actual intratrade/portfolio drawdown.

**Data-quality finding:** 10,826 of 11,322 09:00 bars across the selected stocks had reported zero volume (95.62%). This makes any strategy using the 09:00 opening bar's volume or opening price especially suspect until vendor bar semantics are validated. The B20 09:35 RVOL ratio uses a consistently sampled window but still requires external verification. The limited universe is nonrandom and survivorship-prone; bar timestamp convention and corporate-action adjustment remain unverified.

Next priority: establish timestamp/volume semantics against an independent exchange-grade source; expand to a historically point-in-time stock universe; use fresh out-of-time data and account-level execution simulation. Do not optimize against 2025-26 results.
