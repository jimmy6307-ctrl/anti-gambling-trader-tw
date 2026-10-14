# Automated Taiwan Strategy Research Journal

## 2026-08-28

Research discipline: include 0.685% round-trip cost; use 2024-03-01~2025-03-31 as IS and 2025-04-01~2026-04-01 as OOS; reject hypotheses that only become attractive after seeing OOS; require robustness after removing the largest contributing stock.

### Existing frozen tests

- 09:30 sector-strength + RVOL + gain-band approach: apparent best OOS-like one-year result (+2%~+7%, hold 5d) was heavily dependent on 2408; removing it reduced average net return to roughly flat. Rejected as a standalone entry rule.
- First 20-day breakout + trend + RVOL + sector breadth + <=2% extension, 09:35 entry: OOS was very strong (41 trades, avg +3.20%, PF 4.49; after dropping top contributor 1504: 39 trades, avg +2.42%, PF 3.51), but IS was negative (55 trades, avg -0.62%, PF 0.69). This is regime-sensitive / unconfirmed, not a valid strategy claim.
- Compression-breakout version: too few observations (IS 4, OOS 2), rejected.
- Intraday-confirmation version (gap <=1.5%, 09:00→09:35 gain >=0.5%): IS 39 trades, avg -0.31%, PF 0.81. Rejected before using OOS.
- Market-regime breakout versions using prior market trend thresholds: no version with adequate evidence passed IS; rejected.

### Additional hypotheses screened this run

Using the same 25-stock cached 5-minute universe, screened simple interpretable long-only families: 20/60-day relative-strength leaders, pullback-and-reclaim, MA20 reclaim, simple 20-day breakout, oversold rebound, uptrend dip, and market-breadth-filtered breakouts. The common pattern was poor/negative IS performance and much stronger OOS performance. This indicates a material regime shift between the two windows and means OOS strength must not be used to retrofit the rule.

Notable rejected example: market-breadth-filtered 20-day breakout with >=70% of the universe above MA60 and 5-day hold passed IS superficially (46 trades, avg about +1.01%, PF about 1.81) but failed OOS (24 trades, avg about -0.71%, PF about 0.71). This is a useful falsification: simply adding a strong-market filter does not solve regime dependence.

## 2026-08-29

Tested a distinct post-breakout continuation hypothesis to avoid re-tuning the same-day breakout rule: prior session must itself close at a fresh 20-day high while in `close > MA20 > MA60`; next session at 09:35 must still hold above the prior breakout level, 09:35 RVOL >= 0.8, and the 09:35 price must be between -1% and +2% versus the prior close. Entry at 09:35, fixed 5-day hold, 0.685% round-trip cost.

Result on the same 25-stock universe: IS 102 trades, win rate 43.1%, average net -0.71%, median -0.685%, PF 0.68. OOS was much stronger (116 trades, win rate 51.7%, average net +1.69%, median +0.24%, PF 2.01), but because the frozen IS result failed badly, the OOS result is treated only as further evidence of regime dependence and is not a valid strategy. Rejected.

## 2026-09-01

Tested a distinct uptrend pullback-and-09:35-reclaim family using the same cached universe, fixed 5-day hold and 0.685% round-trip cost. Three predeclared variants covered: (A) above MA60 with a 5-day -3%~-8% pullback and 09:35 reclaim of prior close; (B) `prev_close > MA20 > MA60` with a 5-day -2%~-6% pullback and a limited early reclaim; (C) above MA60, 5%~12% below the prior 20-day high, then +0.3%~+2% versus prior close by 09:35.

All three failed IS before OOS could be used for selection: A 107 trades, avg -0.31%, PF 0.86; B 42 trades, avg -0.41%, PF 0.84; C 219 trades, avg -0.82%, PF 0.72. For diagnostic purposes only, OOS again improved materially (A avg +1.43%, PF 1.69; B +0.66%, PF 1.29; C +0.44%, PF 1.19), reinforcing the already-observed regime dependence rather than validating the family. Rejected.

## 2026-09-21

Tested one predeclared regime-adaptation hypothesis rather than tuning the prior OOS winners: permit a 09:35 20-day breakout only when the stock is already in `prev_close > MA20 > MA60`, RVOL >= 1.5, and at least 60% of the 25-stock universe had been above its MA60 on every one of the prior 10 sessions. Fixed 5-day hold; 0.685% round-trip cost. The market-persistence filter uses only information available before entry.

Result: IS 71 trades, win rate 49.3%, average net +0.13%, median -0.03%, PF 1.06. Removing the largest contributing stock (2881) turned IS negative: 63 trades, average -0.39%, PF 0.84. OOS also failed outright: 24 trades, average -0.23%, median +0.37%, PF 0.89; removing top contributor 3017 worsened average to -0.74%, PF 0.69. Monthly OOS results were concentrated in June (20/24 trades) with November materially negative. Rejected.

This falsifies the specific idea that a simple 10-session persistent breadth gate can stabilize 20-day breakouts across both regimes. Do not tune the 60% or 10-session thresholds on the same OOS window.

## 2026-09-22

Screened a genuinely different long-term-trend/deep-pullback recovery mechanism on the cached universe: prior close above MA120, prior five-session return between -5% and -12%, then by 09:35 price recovers to between prior close and +2%; cost remains 0.685%. The unconstrained 10-day hold initially looked promising (IS 43 trades, avg +1.68%, PF 1.60; OOS 88 trades, avg +2.02%, PF 1.56; OOS after removing top stock 3665 still avg +1.30%, PF 1.33).

However, those raw signals can overlap heavily in the same stock while a prior position would still be open. After applying a conservative no-overlap/cooldown check, the 10-day version fell to 28 IS trades, avg +0.98%, PF 1.28; removing the largest IS contributor 2615 turned it negative (26 trades, avg -0.26%, PF 0.93). The 20-day version also failed the no-overlap IS check outright (25 trades, avg -0.27%, PF 0.93), despite strong OOS. IS monthly concentration was weak: only 4 of 8 active months positive for the 10-day version. Rejected under the concentration-robustness rule.

Also screened simple cross-sectional 20/60-day relative-strength leader variants with trend filters. They again showed the familiar pattern: clearly negative IS and much stronger OOS at longer holds, so they are rejected as regime-sensitive rather than treated as evidence.

### Current conclusion

No strategy has yet met the notification standard across IS + OOS + concentration robustness. Continue searching, but prioritize mechanisms that can survive both the weaker 2024~early-2025 regime and the stronger 2025~2026 regime rather than optimizing for the latter. The repeated IS-negative/OOS-positive pattern across breakouts, continuation, pullback/reclaim, relative-strength, and persistent-breadth filters suggests the next useful step is broader/earlier data or a mechanism explicitly designed for both trend and non-trend regimes—not further threshold tuning on the same two-year sample.

## 2026-10-12 — Auction execution regression guards (data quality only)

Re-read latest branch and raw GitHub Actions quality_audit log at head `0b58a817036ecb1e4cdcc9a03f741f8a975301ad` (run `38194632671`). The quality job passed, with 18/18 offline auction tests and 10/10 independent-minute contract tests; legacy_exploration was skipped. TWSE four-date 4,221-row and TPEx four-date official daily snapshots remain **daily-only**. Neither a passing CI job nor synthetic unit tests establish independent minute/tick history or executable fills.

The head code excludes 09:00 opening auction and 13:30 closing auction from continuous-session signal eligibility. Added three targeted offline regression tests in `research/test_tw_auction_execution_gate.py` (commit `3cabc6d21e792732d660d5c73e1e08e75645b82f`): (1) opening+closing auctions alone must not satisfy continuous-trading activity; (2) 09:00 auction must not be an executable signal; (3) 13:30 auction must not be an executable signal. The CI run for this commit was in progress when the tests were submitted; no pass claimed until raw log is checked.

No new strategy backtest was run. No Fugle/Shioaji credentials, independent authenticated raw responses, verified bar labels, order-book/queue/fill evidence, or genuinely untouched OOS have been obtained. Old 25-stock minute CSV remains quarantined. **DATA GATE = BLOCKED; STRATEGY GATE = BLOCKED; no user notification.**

### 2026-10-12 — Follow-up CI verification (no strategy result)

Rechecked branch head `bee88fa7bf8eefabaa96ef8c5249aba5be9a0c98` and **raw** GitHub Actions job log for run `38206559488`, job `114671218715` (quality_audit success; legacy_exploration skipped). The three auction regression guards submitted in commit `3cabc6d21e792732d660d5c73e1e08e75645b82f` are now confirmed in CI: **21/21 auction tests passed**, including opening/closing auction ineligibility and zero-volume signal rejection. Independent-minute **10/10 synthetic tests passed**. This resolves the prior journal's *CI pending* observation; it does not establish genuine exchange-minute coverage or fills.

The same raw job log still reports archive close discrepancies **241/320** stock-days and volume differences over 10% **315/320**; the TWSE marketwide **4/4 daily dates, 4,221 rows** and TPEx daily snapshots pass daily checks only. Artifact `tw-data-quality-evidence` was uploaded. There are still no authenticated independent Fugle/Shioaji raw minute/tick responses, verified timestamp-label semantics, executable fill evidence, point-in-time universe, or untouched holdout. No strategy P&L test performed. **DATA GATE = BLOCKED; STRATEGY GATE = BLOCKED; no user notification.**


### 2026-10-13 — Verified latest CI; documentation-only Shioaji lot/auction sanity

Checked branch head `d3a18d808fbc784cc52d74d96ff65255a05622d0` and **raw** Actions run `38340989761`, quality job `115111684352`: quality_audit success; auction **21/21**, independent-minute **10/10**, Shioaji clock ambiguity **6/6** synthetic tests passed; legacy_exploration skipped. The archive remains untrustworthy (**241/320** close mismatches; **315/320** volume deviations >10%). Official 30/30 stock-months, 620 stock-days, and 4,221 marketwide rows pass **daily-only**, not intraday/fill verification.

New documented cross-field sanity: Shioaji's 2330 first 09:01 Kbar (`Volume=2565`, `Amount=5,708,965,000`, OHLC range 2225–2235) implies VWAP **2225.72** only if the volume unit is **1,000-share lots**. The documented 09:00:08 tick has volume **2166** (84.44% of that first Kbar if included), showing why opening auction volume must not be treated as ordinary continuous-session RVOL. These are documentation inferences, **not verified live feed facts**; the eight-hour epoch/display discrepancy remains unresolved. Details and source links: `research/notes/2026-10-13-shioaji-first-minute-volume-sanity.md`.

No authenticated Fugle/Shioaji raw responses, minute/tick reconciliation, executable fills, PIT universe, or untouched holdout. **DATA GATE = BLOCKED; STRATEGY GATE = BLOCKED. No backtest or user notification.**


### 2026-10-15 — Latest branch / raw CI recheck; expanded offline contracts only

Read branch head `ffe821024e716f8fdebfe04d17581c8e5ee7dfe8` (2026-10-14 14:40 UTC; commit adds previously omitted offline volume/session/PIT/daily parser tests). Verified the actual GitHub Actions run `38582669848`, `quality_audit` job `115916351785` **success**, `legacy_exploration` **skipped**, and inspected its raw job log (not just the green badge). The expanded offline suites total **98 passing synthetic/contract tests**: auction 21, independent-minute 10, tick/bar labels 11, Shioaji clock 6, TPEx parser 10, amount/volume 8, session separation 14, PIT membership 5, marketwide daily 5, TPEx individual monthly parser 8. These are code-path tests, **not evidence of authenticated historical tick/minute coverage**.

The same raw log still reports old archive-vs-TWSE discrepancies **241/320 stock-days closing price** and **315/320 >10% volume discrepancy**. Official crosschecks: **30/30 stock-months, 620 stock-days** are daily-only; TWSE marketwide **4/4 sessions, 4,221 rows** and TPEx **4 dates (821/837/864/873 daily rows)** likewise establish daily parsing only. The official-marketwide/TPEx steps use `continue-on-error: true`; their log contents must be inspected independently of the overall green job status. There is no authenticated Fugle/Shioaji raw minute/tick response, timestamp/volume unit reconciliation on live data, executable next-bar fill, verified PIT universe, or genuinely untouched OOS. No strategy backtest was run. **DATA GATE = BLOCKED; STRATEGY GATE = BLOCKED; no user notification.**
