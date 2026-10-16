# 2026-10-10 — CI zero-volume blocker and Shioaji timestamp contract (data QA only)

**Research status: BLOCKED. No trading signal, no new backtest, no confirmed edge.**

## Latest CI and repository state

- At the time of this check, branch head was `b9c4bda8571923eb6593eec62f96349b048fbcba` (2026-10-10 05:45:03 UTC).
- GitHub Actions run `38028569751` was the newest run and **failed**; the auction execution gate unit tests are already wired into CI, so do not claim they are absent.
- `research/test_tw_auction_execution_gate.py::test_zero_volume_signal_bar_rejected` expects `ValueError` matching `signal bar.*volume` when the 09:35 signal candle has zero trades. The current `research/tw_auction_execution_gate.py::indicative_next_bar` verifies that the timestamp exists, but never checks that signal candle's `volume_lots > 0`. This is a reproducible fail-open hole in a synthetic test, not a verified market-data finding.
- The 09:35 bar-start candle is not fully observed until 09:36; 09:37 is the first permissible *indicative* candidate in the existing fixture. This is already covered by the tests; do not regress it.
- **Proposed minimal correction**: after finding the signal bar in the audit's `bars`, reject it with a `ValueError` containing `signal bar` and `volume` if its `volume_lots <= 0`. Do not select an alternative bar to manufacture a signal. The next candidate remains strictly later than observation time. Keep `strategy_gate=BLOCKED` even after all tests pass.
- Attempted a direct GitHub connector update of that exact file during this run; the write was **blocked by tool safety checks**. No code fix is claimed. Do not bypass those checks or represent CI as repaired.

## Important new source clarification: Shioaji market-data `ts` is Taiwan wall-clock encoded

Sinotrade's own Shioaji reference explicitly says Python `api.ticks().ts` and `api.kbars().ts` nanosecond timestamps are encoded so that `pd.to_datetime(ts)` gives Taiwan market **wall-clock time**, not a conventional UTC instant. It instructs **not** to parse them as UTC and then add/convert +8 hours. If timezone-aware representation is needed, **localize** the decoded wall-clock to `Asia/Taipei` without changing the hour.

Primary source: https://github.com/Sinotrade/Shioaji/blob/master/plugins/shioaji/skills/shioaji/references/MARKET_DATA.md (section “Market Data Time Handling”).

This clarifies the earlier observed eight-hour difference between numeric nanosecond `ts` interpreted as Unix UTC and the printed naive 09:00 local-time example. **It is a vendor documentation convention, not independent verification of actual authenticated ticks**. Require a source-specific timestamp adapter and raw-data tests before merging with timezone-aware Fugle candles or TWSE official daily anchors. Never use one generic UTC-normalizer across the two vendors.

The Fugle stock-minute API, in contrast, documents ISO-8601 timestamps with explicit `+08:00` and minute volumes in **lots** for board-lot equities, versus **shares** for daily bars. Source: https://developer.fugle.tw/docs/data/http-api/historical/candles/ . This source-specific units/clock distinction is mandatory in the data contract.

## Next data gates

1. Repair and rerun the zero-volume synthetic test; check the latest commit and actual CI run before claiming success.
2. Obtain authorized raw Fugle minute and Shioaji tick/Kbar records on **predeclared** TWSE and TPEx symbol/date pairs. Archive SHA256, retrieval time, raw response, timezone and units.
3. Reconcile 13:30 auction price against official close and check bar-start/end conventions against ticks; reconcile trade coverage and volume categories before any return calculation.
4. Build point-in-time stock universe and corporate-action history, then reserve a truly unseen later holdout. The previously inspected 2025-04–2026-04 interval is contaminated and must not be relabeled as fresh OOS.

**No new strategy validation, no user notification.**
