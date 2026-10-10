# 2026-09-05 — mild pullback + early reclaim

Goal: respond to the prior sparse pullback setup by testing one deliberately simpler, higher-frequency mechanism without parameter searching.

Frozen rule before split inspection: prior close > prior MA60; trailing 20-day return > 0; trailing 5-day return <= -2%; by 09:35 price is >= +0.3% from the open; enter at 09:35; fixed hold 5 trading days; charge 0.685% round-trip cost. No sector, gap, or RVOL filter. Same cached 25-stock universe and same chronological split.

Results:

- IS (through 2025-03-31): 148 trades, win rate 53.38%, average net **-0.17%**, median +0.73%, PF **0.93**.
- OOS (2025-04-01 to 2026-04-01): 131 trades, win rate 50.38%, average net +0.79%, median +0.19%, PF 1.38.

Decision: **rejected**. The mechanism fails the predeclared IS gate (positive expectancy and PF > 1.2), so the attractive OOS result is not promoted to a strategy claim and must not be used to tune thresholds after the fact.

Implication: loosening the prior pullback/reclaim setup solves sample sparsity but not stability. A future run should test a genuinely different mechanism or expand the universe/history rather than optimize this family around the OOS outcome.
