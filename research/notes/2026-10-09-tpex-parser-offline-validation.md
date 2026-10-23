# 2026-10-09 — TPEx historical daily parser offline check (data-only)

Existing work already discovered the official TPEx historical daily quotation endpoint and TWSE MI_INDEX source. This run did not re-run any legacy strategy or treat 2025-04 to 2026-04 as clean OOS.

A local, standalone Python prototype for the TPEx official historical daily HTML/CSV parser was implemented and passed **9 offline synthetic tests** (HTML table, CSV, wrong date, missing date, schema drift, duplicate security, impossible OHLC, no-trade row, ROC year conversion). It extracts date, security code, OHLC, volume shares, turnover, trades, checks duplicate IDs and OHLC invariants, and preserves source provenance. **These are synthetic parser tests, not a live-data pass.**

Official TPEx historical report evidence: https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php?d=103%2F03%2F12&l=zh-tw&o=htm&s=0&se=EW . Historical report headings include 代號、名稱、收盤、開盤、最高、最低、成交股數、成交金額(元)、成交筆數. The report is labeled 不含定價. Four-digit security-code filtering alone is **not** a point-in-time common-stock universe.

Local files created in the research runtime: tw_tpex_historical_daily_gate.py and test_tw_tpex_historical_daily_gate.py. These were not committed to GitHub: code-file and workflow changes were blocked by the connector's safety checks. The existing workflow therefore still does not execute TWSE MI_INDEX or TPEx historical full-market gates. This is a workflow/data-access limitation, **not evidence of any trading edge**.

Live TWSE/TPEx fetches from the local runtime failed DNS. The 2026-10-07 TPEx live response was not retrieved. No new independent 5-minute/tick data, corporate actions, or clean holdout were acquired.

Next: run the official TWSE MI_INDEX and TPEx historical parser on an approved networked runner, archive raw bytes, UTC retrieval times and SHA256, verify actual schema and dated rows; cross-check at least five TPEx daily close anchors; then seek licensed independent intraday/tick source. Do not certify P&L before next-tradable-bar fills, costs, overlap and point-in-time universe.

**DATA GATE BLOCKED; NO CONFIRMED EDGE; no user notification.**
