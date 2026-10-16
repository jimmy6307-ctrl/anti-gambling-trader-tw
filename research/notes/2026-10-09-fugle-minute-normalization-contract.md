# Independent minute-data normalization contract (2026-10-09)

This is a **data-only research note**, not a strategy result. No historical holdout is opened or backtested.

Official Fugle historical candles documentation (https://developer.fugle.tw/docs/data/http-api/historical/candles/) specifies:

- Historical 1/3/5/10/15/30/60-minute bars are available since **2023-05-23**, with timestamp ISO 8601 including **+08:00**. Their 1-minute example has a **13:30** closing-auction bar after 13:24, so gaps in minute indices are not automatically data corruption; do not fabricate zero-volume bars.
- Minute-bar `volume` for board-lot stocks is in **lots (1,000 shares)**, while daily-bar `volume` is in **shares**. Compare `sum(minute_volume)*1000` with daily shares only after identifying all auction and other trading-session components and excluding incompatible transaction categories.
- `adjusted=true` is only supported for **daily/weekly/monthly** candles. Do not silently merge adjusted daily moving averages with unadjusted minute prices. Maintain a corporate-action event ledger and a consistent as-of adjustment policy.
- `data.average` on minute bars is **cumulative average from the open**, not that bar's VWAP; never use it as a minute execution price.
- A query range must be **less than one year**; 404 can mean no observations for that interval. Never interpret a 404 as a zero-price or zero-volume trading day.
- Source is authenticated (`X-API-KEY`); no independent historical minute data has been fetched/validated in this run. Do not invent API credentials or publish them in artifacts.

Required independent-source gate before any performance study: fetch predeclared 2330/6488 samples and dates; archive raw responses and SHA256 with UTC retrieval time; check timestamp timezone, no duplicate timestamps, auction closing print against official TWSE/TPEx close, minute-volume units, adjusted/unadjusted alignment, and next-available tradable bar execution. Use a **separate truly unseen later period** for OOS, never 2025-04~2026-04. Mark strategy validation BLOCKED until all conditions pass.

**NO CONFIRMED EDGE.**