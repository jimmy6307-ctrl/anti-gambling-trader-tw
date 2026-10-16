# 2026-10-10 — Closing-auction and next-bar execution contract (data gate only)

## Prior state preserved

No legacy strategy was rerun, no 2025-04–2026-04 period was re-labelled as untouched OOS, and no performance result was generated. The existing 25-stock Yahoo-derived minute CSV cannot establish the official 13:30 closing price. Earlier official TWSE/TPEx four-date daily gates remain **daily-only**, not intraday validation. The old TPEx per-stock `st43_result.php` route returned TPEx-branded HTML 404 for all five predeclared stock probes (2026-10-10 prior note); it is quarantined.

## Evidence checked in this run

- Fugle's current official historical stock candle documentation (updated 2026-08-20) explicitly shows a 2330 **13:30** minute auction point on **2026-04-23** with OHLC 2080 and volume **5,330 lots**, while the preceding documented continuous-session minute is **13:24** with volume **104 lots**. The example demonstrates why a 13:20/13:24 print is not a reliable official close. **This is a documentation example, NOT independently downloaded live history and NOT a confirmed exchange reconciliation.**
- The same documentation specifies minute bars for board-lot stocks in **lots** and daily bars in **shares**, `adjusted=true` only for daily/weekly/monthly, and required `exchange` metadata. Documentation does not by itself prove stock-minute bar-start/bar-end semantics against actual ticks.
- TPEx currently advertises an official historical **individual stock daily pricing UI** at `https://www.tpex.org.tw/zh-tw/mainboard/trading/info/stock-pricing.html?code=6996`, with monthly search and records dating back to ROC year 83. The visible UI is **not** proof that its undocumented back-end API can be called. Local direct TPEx access remains DNS-blocked. Do not retry the retired `st43_result.php` endpoint as though it worked.
- Sources: https://developer.fugle.tw/docs/data/http-api/historical/candles/ ; https://www.tpex.org.tw/zh-tw/mainboard/trading/info/stock-pricing.html?code=6996

## New reproducible fail-closed code

- Added `research/tw_auction_execution_gate.py` and `research/test_tw_auction_execution_gate.py`.
- **17 synthetic offline unit tests passed locally**: official close mismatch, missing/zero-volume auction, non-point auction, wrong exchange/security type, duplicate or timezone-naive timestamps, impossible OHLC, unexpected bars in 13:25–13:29, lack of proven timestamp semantics, insufficient cash, full portfolio, limit-up, missing exchange upper price limit, and next-bar indicative-only status.
- Minute/auction validation requires the explicit 13:30 positive-volume single-price point matching the official close. It reports `ANCHOR_MATCH_ONLY` and **always** `strategy_gate=BLOCKED`. A one-minute candle example is insufficient to infer a fill.
- Indicative next-bar evaluation requires independent confirmation of bar-start semantics. For a **09:35 bar labelled by start**, the signal is not fully observable until **09:36**; the first later positive-volume continuous-session bar is a *candidate print*, not a guaranteed fill. It reserves board-lot cash including estimated buy costs, respects a maximum number of positions, blocks upper-limit buys and missing daily price limits. Ex-post next-bar volume participation is only a diagnostic, not a fill guarantee.
- Synthetic test prices/volumes are illustrative, not observed returns or execution evidence. Exact execution requires order-book/tick and broker fill records. The validator is intentionally strict and can produce false negatives when source conventions are not proven.
- Attempted to add these tests to the existing GitHub Actions quality job; connector safety checks **blocked the workflow edit**. Tests are committed but **not CI-wired**; local `python -m unittest -v test_tw_auction_execution_gate.py` succeeded (17/17).

## Next mandatory data gate

Obtain an authorized Fugle or other independent minute/tick history feed (no credentials available in this run); archive original bytes and SHA256; compare predeclared TWSE 2330 and TPEx 6488 dates with exchange daily closes and 13:30 auction; verify stock bar label conventions against ticks. Then build a point-in-time stock universe, as-of corporate actions and fresh sealed holdout before any new hypothesis P&L study. **No verified edge, no user notification.**
