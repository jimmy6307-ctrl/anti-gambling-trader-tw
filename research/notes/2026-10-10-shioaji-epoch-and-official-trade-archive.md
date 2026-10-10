# 2026-10-10 — Timestamp-source QA (no trading results)

No strategy rerun or new holdout claim. Existing data gate remains BLOCKED.

## New finding: Shioaji example clocks

The Shioaji historical-market-data documentation prints a 2026-05-18 stock tick with nanosecond value 1779094808306075000 alongside a timezone-naive 09:00:08.306075 clock. Standard Unix UTC conversion of the integer produces 17:00:08.306075 in Taiwan, an eight-hour discrepancy. The documented first Kbar similarly shows a 09:01 label versus a 09:00:08 tick, consistent with (but not proof of) an end-labelled minute bar. These are **documentation ambiguities**, not confirmed defects in actual authenticated API records.

Source: https://sinotrade.github.io/zh/tutor/market_data/historical/

Added a fail-closed comparison helper and six local tests; 6/6 passed. The helper always blocks strategy certification. No authenticated tick feed was acquired; no CI wiring claimed.

## Newly discovered official historical files

TWSE E-Shop lists historical trade files at NT$10,000/month, excluding the most recent year, and historical quote/disclosure files at NT$5,000/month, available only through the end of two months before purchase. Both require custom preparation (at least seven working days), with internal-use restrictions. Trade and quote files have distinct schema-version boundaries in 2025 and 2026; quote data alone do not establish trade fills.

Sources:
- https://eshop.twse.com.tw/zh/product/detail/0000000063ce6ab00163d860b694000a
- https://eshop.twse.com.tw/zh/product/detail/0000000063afcda50163b1a5bc180006

Next: obtain an authorized narrow sample of independent Shioaji ticks/Kbars and Fugle 1-minute bars, archive raw bytes and SHA256, reconcile timestamps and 13:30 official close before any new backtest. Keep 2025-04~2026-04 contaminated and reserve a truly unseen later holdout.

**DATA GATE BLOCKED; NO CONFIRMED EDGE; no user notification.**
