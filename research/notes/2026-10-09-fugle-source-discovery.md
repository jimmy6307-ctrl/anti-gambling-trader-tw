# 2026-10-09 — Independent 5-minute source documentation

Fugle's official historical candle documentation confirms 5-minute data since 2023-05-23, with date ranges shorter than one year and examples that include a 13:30 +08:00 timestamp. Official source: https://developer.fugle.tw/docs/data/http-api/historical/candles/

Fugle's official September 2026 pricing page lists a free basic account with historical-data requests limited to 60/minute. Official source: https://developer.fugle.tw/docs/pricing/

Shioaji also documents historical tick and Kbar queries; Kbar request ranges cannot exceed 30 days. Official source: https://sinotrade.github.io/zh/tutor/market_data/historical/

This is a source-discovery result, not an authenticated retrieval or proof of 13:30 auction completeness. A strict TPEx historical daily parser and synthetic tests were added in research/tw_tpex_historical_daily_gate_v2.py and research/test_tw_tpex_historical_daily_gate_v2.py, but no live TPEx historical response has been validated. The existing workflow does not execute these new files; a separate workflow creation attempt was not accepted. An earlier superseded parser file remains, and only v2 should be considered for further testing.

Next data gate: compare independently sourced 1/5-minute bars and ticks against official daily close on fixed dates, verify timestamps and tradable next-bar fills, and audit historical universe/corporate actions. Do not rerun contaminated strategy windows. No verified edge, no user notification.
