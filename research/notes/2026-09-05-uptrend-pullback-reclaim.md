# 2026-09-05 — uptrend pullback + 09:35 reclaim

Goal: after repeated breakout/momentum failures, test a genuinely different long-only payoff mechanism: buy a short-term pullback inside an established uptrend only after early-session recovery confirms demand.

Frozen rule before inspecting split results: prior close > prior MA60; trailing 20-day return > 0; trailing 5-day return <= -3%; opening gap between -3% and -0.5%; by 09:35 price has bounced at least +0.5% from the open; 09:35 cumulative-volume RVOL >= 1.2 versus prior 20 sessions; enter at 09:35 and hold 3 trading days. Charge 0.685% round-trip cost. No alternate thresholds/lookbacks/holding periods were searched in this run.

Split remains IS through 2025-03-31 and OOS from 2025-04-01 to 2026-04-01, using the same cached 25-stock research universe.

Results:

- IS: only **1 trade**, net +1.54%. Sample is far below any acceptable evidence threshold.
- OOS: **0 trades**.

Decision: **rejected as unusably sparse**, regardless of the lone IS winner. No strategy claim is allowed and no parameter loosening will be done after seeing this result.

Implication: the available 25-stock / roughly two-year cache is now the dominant research constraint for conditional long-only setups. Before spending more runs on threshold variants, expand history/universe or use a mechanism that naturally produces enough independent observations under the current data.