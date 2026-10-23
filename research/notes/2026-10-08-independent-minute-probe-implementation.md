# 2026-10-08 independent minute-data audit progress

New source-quality probe: research/tw_independent_minute_probe.py. It compares one day of official TWSE closing prices with independently obtained 1-minute bars from Fugle. Raw inputs, SHA256, capture time and selected intraday observations are saved. A matching 13:30 close only means ANCHOR_MATCH_ONLY, never a trading strategy pass. Added offline synthetic parser tests. No live vendor key is available, so no independent numeric check was completed. No trading strategy was rerun.

Additional independent candidate: Sinopac Shioaji historical 1-minute Kbars and ticks, which require authentication. Fubon Neo and Fugle may share upstream market data and should not be counted as two independent vendors. Continue with historical bar timestamp/closing auction checks, corporate actions, point-in-time universe, next-tradable-bar fills and fresh sealed holdout. Old OOS is contaminated. DATA GATE BLOCKED; NO CONFIRMED EDGE.
