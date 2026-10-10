# 2026-09-02 — weekly cross-sectional relative strength

Goal: change the economic mechanism after the failed intraday-breakout regime gates. Test slower cross-sectional leadership rather than tuning the prior signal.

Frozen exploratory rule before inspecting the split results: on the first trading day of each week at 09:35, among the 25-stock research universe, require prior 20-day return > 0 and prior close above its 60-day moving average; rank survivors by trailing 60-trading-day return; buy the top 3 equal-weight; rebalance/exit after 5 trading sessions. Charge 0.685% round-trip cost per position. No sector or RVOL tuning was added.

Because the cached source starts in 2024-02, the 60-day lookback makes the effective IS start about 2024-05. Split remains IS through 2025-03-31 and OOS from 2025-04-01.

Results:

- IS: 129 stock-weeks / 43 portfolio-weeks, stock-level win rate 48.1%, avg -0.95%, median -0.18%, PF 0.69. Equal-weight portfolio-week avg -0.95%, PF 0.61. **Fail.**
- IS removing largest contributing stock (3665): 105 stock-weeks, avg -1.32%, PF 0.58.
- OOS diagnostic only after IS fail: 138 stock-weeks / 46 portfolio-weeks, win rate 58.7%, avg +1.41%, median +1.42%, PF 1.54; portfolio-week PF 1.95.
- OOS removing largest contributing stock (2408): 115 stock-weeks, avg +1.04%, PF 1.45.

Decision: **rejected**. The slower relative-strength mechanism still shows the same regime asymmetry as the breakout family: weak/negative in 2024~early-2025 and positive in 2025~2026. The attractive OOS result is not admissible confirmation because the frozen rule failed IS first.

Implication: do not tune 20/60-day windows or top-N on this split. Next useful work should target a mechanism that can plausibly survive both regimes (for example, explicit long/relative or defensive allocation using only contemporaneously observable breadth), or expand the history/universe before drawing conclusions about a regime-dependent long-only momentum edge.
