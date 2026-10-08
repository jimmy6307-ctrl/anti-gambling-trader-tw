# 2026-10-09 — Historical official daily source gate, not a strategy result

## Status and evidence
- TWSE marketwide historical MI_INDEX parser and 5 offline tests exist in `research/tw_marketwide_daily_gate.py` / `research/test_tw_marketwide_daily_gate.py`; no verified live MI_INDEX artifact yet. The currently configured workflow runs other official source-quality checks, not this new marketwide gate.
- Official TPEx historical daily source: `https://www.tpex.org.tw/web/stock/aftertrading/otc_quotes_no1430/stk_wn1430_result.php` with a ROC date parameter `d`, `se=EW`, `o=csv`. Unlike TPEx OpenAPI latest-day snapshots, this older report is intended for dated history. Reference: TPEx official stock-pricing page `https://www.tpex.org.tw/zh-tw/mainboard/trading/info/stock-pricing.html`; historical parser examples are available in `yukishirotsubasa/tw-stock-data-release`.
- Prototyped a strict TPEx CSV/HTML parser locally with eight passing synthetic tests (date mismatch, missing date, duplicate security, invalid OHLC, schema drift, CSV and HTML, ROC date conversion). This is **parser logic only**, not proof the live TPEx endpoint currently returns that schema.
- Live TWSE/TPEx access from the local runtime fails DNS; attempts to add a separate GitHub workflow or new remote probe file were not accepted by the connector. The local test prototype is not yet committed to the research branch. No new live data, independent 5-minute bars, or actual fills were acquired.

## Next data-only run (no repeated strategy tuning)
1. Execute the already-written TWSE marketwide parser against four predeclared historical dates on an approved networked runner, archiving raw JSON, UTC fetch times, SHA256, per-date row counts, and 2330 comparison against STOCK_DAY.
2. Independently query TPEx historical daily reports for the same four dates, confirm date-in-response, schema, historical code appearance, and at least five OTC stock close anchors. Do not treat the 4-digit-code filter as a point-in-time common-stock classifier.
3. Keep new daily data quarantined. Obtain licensed independent minute/tick data and verify 13:30 auction, timestamp conventions, next-tradable-bar fills, split/dividend events, liquidity, portfolio overlap and costs.
4. 2025-04–2026-04 remains a repeatedly inspected period, not an untouched OOS. No strategy performance claims until the entire data gate passes.

**DATA GATE BLOCKED; NO CONFIRMED EDGE; no user notification.**
