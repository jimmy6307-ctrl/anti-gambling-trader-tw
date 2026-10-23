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


### 2026-10-15 — Latest head 5193d25 / raw CI 38617488622 verified

Verified branch head `5193d25a242d9b0c8662f3b6dc6ea4af0b9bb838` (2026-10-14 18:42:47 UTC) and latest GitHub Actions pull-request run `38617488622`: `quality_audit` job `116036212524` succeeded, `legacy_exploration` skipped. Read the actual raw job log, not just its green status. The 10 offline suites still total **98 passing tests** (21+10+11+6+10+8+14+5+5+8); these are synthetic contracts, not authenticated market-minute data. Archive-vs-official closing mismatch remains **241/320**, volume >10% discrepancy **315/320**. Official 30/30 stock-months / 620 stock-days, TWSE marketwide 4/4 dates / 4,221 rows, and TPEx four dates (821/837/864/873) remain **daily-only** evidence. `daily_close_gate=FAIL`, `strategy_gate=BLOCKED`; no authenticated independent minute/tick source, next-bar fills, or untouched OOS. No strategy backtest performed and no user notification. Raw log: https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/38617488622 ; note the green CI does not overturn data quarantine.


### 2026-10-18 — Rechecked latest branch, raw CI, and corrected minute-boundary contracts (no strategy run)

Verified branch head `3b8de8937a02d351d79314aa23c7550b1c3ba440` (2026-10-16 11:04:05 UTC), and latest PR Actions run `38891339336`, `quality_audit` job `116941311209` **success**, `legacy_exploration` **skipped**. Read the **raw job log**. Ten offline suites report **99 passing synthetic/contract tests** (21+10+12+6+10+8+14+5+5+8). The extra tick/bar semantics test checks exact-minute boundaries: the END candle label L represents [L-1m,L), so a trade exactly at L-1m belongs to the next END label. Source and tests at this head now encode `end_label = floor(tick_timestamp) + 1 minute`, including an explicit END_BOUNDARY fixture. This is a *code-level regression check only*, not evidence of actual vendor tick completeness or independent minute-feed agreement.

Raw quality audit **still fails** `daily_close_gate=FAIL`, `strategy_gate=BLOCKED`; old archive closing-price mismatches **241/320** and >10% volume discrepancies **315/320**. Official stock-month **30/30**, stock-day **620**, TWSE marketwide 4 days **4,221 rows**, TPEx daily 4 days **821/837/864/873** remain **daily-only** checks. No authenticated Fugle/Shioaji raw minute/tick pairs, documented upstream independence, 09:00/13:30 auction reconciliation, true next-bar execution, PIT universe or genuinely untouched OOS. **DATA GATE = BLOCKED; STRATEGY GATE = BLOCKED.** No strategy test or user notification.

Evidence: https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/38891339336 and https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/commit/3b8de8937a02d351d79314aa23c7550b1c3ba440 .


### 2026-10-21 — Latest PR head and raw quality CI recheck (documentation only)

Verified PR #1 head `7b3f106dcb068b525858463fd5453b52bd4f673d` (2026-10-18 09:05 UTC) and latest PR run `39113973481`, raw `quality_audit` job log `117635831612`: job **success**, `legacy_exploration` **skipped**. Ten offline contract suites total **99 passing tests** (21+10+12+6+10+8+14+5+5+8). Raw quality status remains `daily_close_gate=FAIL`, `minute_gate=NOT_TESTED`, `strategy_gate=BLOCKED`; legacy archive mismatch **241/320** closing prices and **315/320** volume discrepancies >10%. Official **30/30 stock-months, 620 stock-days**, TWSE **4 dates / 4,221 daily rows**, TPEx **4 dates / 821, 837, 864, 873 daily rows** validate daily parsing only. This CI success is not a data-quality pass or strategy edge.

The latest commit adds `research/notes/2026-10-18-shioaji-wall-clock-and-session-risk.md` (documentation only). Independently read Sinotrade's primary-source `MARKET_DATA.md`: historical Shioaji Python ticks/kbars `ts` encode Taiwan **wall-clock** nanoseconds; decode directly with `pd.to_datetime(ts)` and, if needed, `tz_localize("Asia/Taipei")`, **not** UTC conversion or adding eight hours. This resolves the *documented interpretation* of the eight-hour discrepancy, not actual feed authentication or per-version verification. The 2026-10-16 END-labelled minute-boundary fix and its twelfth regression test remain already fixed and CI-tested.

**Unresolved blocker:** `tw_session_separation_gate.py` still treats 09:00:xx after exactly 09:00:00 as normal continuous-trading candidates, even though official Shioaji historical examples include opening auction-like 09:00:08.306075 prints without a native auction flag. Fail closed on ambiguous 09:00:xx only if an authorized future code change is permitted; earlier attempted code edit was blocked by a safety check, and no workaround was attempted. No authenticated Fugle/Shioaji minute/tick raw bytes, independent feed reconciliation, verified fills, PIT historical universe, or genuinely untouched OOS were acquired. **DATA GATE=BLOCKED; STRATEGY GATE=BLOCKED.** No strategy backtest and no user notification.

Evidence: https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/39113973481 ; https://github.com/Sinotrade/Shioaji/blob/master/plugins/shioaji/skills/shioaji/references/MARKET_DATA.md .

### 2026-10-22 — PR head 64bbe9c; raw CI verified, no eligible minute-data advance

Rechecked PR #1 head `64bbe9c522590d8e28336def333d225469a85861` and both most recent completed Actions runs `39466106021` (quality job `118777813386`) and `39466098982` (quality job `118777789901`); both quality jobs **success**, legacy_exploration **skipped**. Read **raw job logs**, not green check alone. Latest quality log: ten offline test suites **99/99** (21+10+12+6+10+8+14+5+5+8). But `daily_close_gate=FAIL`, `minute_gate=NOT_TESTED`, `strategy_gate=BLOCKED`. Archive vs official remains **241/320** stock-days with wrong close and **315/320** with >10% volume deviation. Official **30/30 stock-months / 620 stock-days**, TWSE marketwide **4 dates / 4,221 daily rows**, TPEx **4 dates / 821, 837, 864, 873 daily rows** are **daily-only** validations. Latest artifact `tw-data-quality-evidence` id `12285261759` exists but does not certify minute ticks or execution.

Re-read `tw_session_separation_gate.py` at this head: exact `09:00:00` is `OPENING_AUCTION_CANDIDATE`, but ambiguous `09:00:08.306075` still falls through to `NORMAL_CONTINUOUS_CANDIDATE`. Current `test_tw_session_separation_gate.py` has 14 tests, none rejects 09:00:xx ambiguous ticks. This remains an **unfixed source-quality risk**; no code edit attempted (earlier write safety-blocked). The tick/bar END boundary fix with its twelfth regression test remains **already fixed**. Shioaji's historical market-data wall-clock timestamp interpretation was documented earlier; this does not authenticate a live response.

No legally authorized independent raw Fugle minute + Shioaji tick pair, original bytes/hashes, verified auction partition or next-bar fills, PIT universe, or genuinely unseen OOS was available in this run. **DATA=BLOCKED; STRATEGY=BLOCKED; no strategy P&L, no user notification.** Evidence: https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/39466106021 and https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/pull/1 .


### 2026-10-23 — Verified latest opening-minute fix and raw CI (no strategy P&L)

Rechecked PR #1 head `4963ec29f2b53620e1fb9585ea228ca1012faf2a` (commit 2026-10-22 08:17 UTC) and the associated completed Actions run `39746669208`, `quality_audit` job `119716723095` **success**, `legacy_exploration` **skipped**. Read the **raw 130,265-character job log**. Ten offline suites now total **102 passing contract tests** (21+10+12+6+10+8+17+5+5+8), including 17/17 session-separation tests.

**Correction to earlier outstanding issue:** `research/tw_session_separation_gate.py` now rejects ambiguous 09:00:xx ticks with a ValueError, while preserving 09:00:00 as an opening-auction candidate and 09:01:00 onward as continuous candidates. Commit `4963ec29` added three regression tests (09:00:00.000001, 09:00:08.306075, 09:00:59; 09:01 preserved; `separate_ticks` rejects ambiguous auction tick). The raw CI log confirms all three and the full 17-test suite pass. Thus the *code-level 09:00:xx classification issue is fixed*; do not repeat it as unresolved. The previously fixed END-labelled minute-boundary issue remains fixed (12/12 offline tests).

However, CI still prints `daily_close_gate=FAIL`, `minute_gate=NOT_TESTED`, `strategy_gate=BLOCKED`. Quarantined archive-vs-official TWSE data remain **241/320** closing-price mismatches and **315/320** >10% volume discrepancies. Official **30/30 stock-months / 620 stock-days**, TWSE marketwide **4/4 days / 4,221 daily rows**, and TPEx **four daily snapshots (821/837/864/873 rows)** establish **daily-only** parsing. The 102 passing tests are offline contracts, not authenticated minute/tick validation, verified exchange-session partition on raw vendor data, executable next-bar fills, PIT universe, or genuinely unseen OOS. No independent licensed Fugle minute + Shioaji tick raw pair or associated provenance/sha256 is available; no new strategy backtest or P&L claim. **DATA GATE=BLOCKED; STRATEGY GATE=BLOCKED; no user notification.**

Evidence: https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/39746669208 ; https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/commit/4963ec29f2b53620e1fb9585ea228ca1012faf2a .


### 2026-10-24 — Latest PR/CI provenance recheck; market-minute evidence still absent

At 2026-10-24 01:43 Asia/Taipei, fetched PR #1 head `3cc327b0fd316511768d91e77146bc98159c0a5f` (prior journal head `4963ec29`). Latest completed PR Actions run `39815617499` on that head: `quality_audit` job `119953317975` **success**, `legacy_exploration` **skipped**. Read the **raw 130,272-character quality job log**, not only the CI status. Ten offline contract suites total **102 tests passed** (21+10+12+6+10+8+17+5+5+8). These tests exercise offline contracts, not independently authenticated minute/tick market data. This head's commit changes only this research journal, not the session classifier.

Raw log explicitly retains `daily_close_gate=FAIL`, `minute_gate=NOT_TESTED`, `strategy_gate=BLOCKED`. The quarantined archive still disagrees with TWSE official close on **241/320** stock-days and differs in volume by >10% on **315/320**. Official daily validation: **30/30 stock-months, 620 stock-days**, TWSE marketwide **4/4 dates, 4,221 daily rows**, TPEx **4 dates with 821/837/864/873 daily rows**. No licensed independent Fugle minute + Shioaji tick raw bytes, per-file hashes/provenance, independently verified auction handling on actual ticks, realistic executable fills, PIT universe, or truly untouched OOS are present. The 09:00:xx fail-closed session classification fix and END-labelled minute boundary fix remain **already implemented and offline-tested** (17 and 12 tests respectively); do not re-open these as unresolved defects. The quality-evidence artifact is `12442491898` but is daily-only and does not clear minute-data gates.

**DATA GATE = BLOCKED; STRATEGY GATE = BLOCKED.** No valid intraday strategy P&L was computed; no claim of a tradable edge or user notification. Next legitimate step is authorized raw independent minute/tick acquisition with timestamp, volume-unit, exchange-session and auction reconciliation, not parameter tuning or contaminated legacy backtesting.

Evidence: https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/39815617499 ; https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/pull/1 .
