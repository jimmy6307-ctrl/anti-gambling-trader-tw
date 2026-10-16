# 2026-09-02 — breadth-gated weekly momentum

Goal: follow the prior weekly relative-strength failure with a mechanism that explicitly turns the long-only signal off in weak market regimes, without tuning the old breakout parameters.

Frozen rule before inspecting split results: on the first trading day of each week at 09:35, compute market breadth as the fraction of the 25-stock research universe whose prior close is above its prior 60-day moving average. Trade only when breadth >= 60%. Among eligible stocks, require prior 20-day return > 0 and prior close > MA60, rank by trailing 60-day return, buy top 3 equal-weight, and exit after 5 trading sessions. Charge 0.685% round-trip cost per position. The 60% gate was chosen ex ante as a simple majority-plus confirmation threshold; no alternate thresholds/top-N/lookbacks were searched in this run.

Split remains IS through 2025-03-31 and OOS from 2025-04-01. Cached 5-minute data starts in 2024-02, so the 60-day lookback makes the effective IS start later.

Results:

- IS: 72 stock-weeks / 24 portfolio weeks, win rate 43.1%, average net return -1.23%, median -0.91%, PF 0.66. **Fail.**
- OOS diagnostic only after IS fail: 78 stock-weeks / 26 portfolio weeks, win rate 50.0%, average +0.14%, median -0.01%, PF 1.04. Also fails the requested PF > 1.2 bar even before robustness removal.

Decision: **rejected**. A simple breadth-on/cash gate does not rescue the weekly long-only momentum mechanism. It materially reduces participation but leaves IS clearly negative and OOS roughly flat after costs.

Implication: stop tuning breadth thresholds on this short split. The repeated pattern now suggests the main bottleneck is limited history/regime coverage rather than a missing intraday filter. Next useful work should either (a) expand history/universe before making long-only momentum claims, or (b) test a genuinely different payoff mechanism such as cross-sectional relative/market-neutral ranking if the available data supports a realistic short-side implementation.