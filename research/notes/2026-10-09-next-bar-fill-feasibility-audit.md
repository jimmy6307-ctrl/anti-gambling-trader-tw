# 2026-10-09 — Next-bar fill feasibility audit (data-only)

No strategy backtest was rerun; no previously inspected period is promoted to clean OOS. Existing 25-stock Yahoo-derived 5-minute data remain unfit for executable strategy certification.

## Newly formalized failure mode

Even if a signal is observed at the completed 09:35 bar and the simulator uses the **next bar's opening price**, a check such as `order_shares <= 2% * next_bar_total_volume` uses volume that was **not known when the order was sent**. It may serve as an ex-post participation *diagnostic*, never as evidence the order filled at the bar's opening print. Likewise, an OHLC bar's open price is a print, not a guaranteed fill for a new market order. Do not upgrade a backtest to executable based solely on those two numbers.

## Conservative offline contract

A prototype validator and 11 synthetic tests were executed locally and passed. These do **not** constitute live-data validation. Rules:

- Require independently established Taiwan-local timezone and **bar-start / bar-end semantics**; reject naive timestamps, duplicate/overlapping bars, impossible OHLC, negative volume, unverified provenance.
- Model the 13:30 closing auction as a **point print**, not a 13:30–13:35 continuous trading bar. For an official-close anchor, require one independently verified 13:30 print with positive traded volume and price equal to the exchange's daily close. Missing auction print is BLOCKED, not silently replaced by 13:20/13:25.
- Only a continuous-session bar strictly after signal observation is a candidate for an indicative entry. Zero-volume, limit-up buys, unknown exchange price limits, insufficient cash or participation are blocked. An accepted candidate must still be labeled `INDICATIVE_ONLY_NOT_A_PROVEN_FILL`.
- Reserve full estimated purchase cash plus commission, enforce board-lot sizing and a cap on simultaneous positions; reject repeated same-stock signals until the prior position is closed. A later price and actual execution must be independently verified before calculating P&L.
- Keep after-2026-04 data quarantined; preserve true future holdout. Do not certify any edge until independent minute/tick data, corporate actions, historical universe, and realized fills are validated.

## Source work and blockers

Prior official TWSE MI_INDEX four-date quality gate passed (4,221 listed security-day observations, verified against 2330 STOCK_DAY). TPEx historical daily parser exists with synthetic tests but no confirmed live response. A workflow wiring attempt was rejected by the GitHub connector's safety checks; no new TPEx artifact was produced. Local direct TPEx access failed DNS and web fetch returned 403. Fugle historical minute data still require valid API access and independent timestamp verification.

**DATA GATE BLOCKED. NO CONFIRMED EDGE. No user notification.**
