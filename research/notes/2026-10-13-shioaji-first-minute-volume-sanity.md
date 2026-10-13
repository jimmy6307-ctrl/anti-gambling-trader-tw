# 2026-10-13 — Shioaji opening-minute volume-unit sanity check (documentation only)

**Status: DATA GATE BLOCKED / STRATEGY GATE BLOCKED. No trading results, no authenticated raw feed.**

## First verify the current branch and CI

At branch head `d3a18d808fbc784cc52d74d96ff65255a05622d0`, Actions run `38340989761` quality_audit **success**; raw job `115111684352` confirms auction tests **21/21**, independent-minute synthetic tests **10/10**, and Shioaji timestamp ambiguity tests **6/6**. `legacy_exploration` skipped. The old 5-minute archive still disagrees with official closes on **241/320** stock-days and with official volume by >10% on **315/320**. Official TWSE daily checks (30/30 stock-months; 620 stock-days) and TWSE marketwide four-date checks (4,221 rows) remain **daily-only**. No independent minute/tick data, fill evidence or untouched OOS was acquired.

## New cross-field sanity calculation from official Shioaji documentation

Shioaji's published **2026-05-18** 2330 first Kbar example has time **09:01:00**, Open 2225, High 2235, Low 2225, Close 2230, `Volume=2565`, and `Amount=5,708,965,000`. If Volume is interpreted as **board lots of 1,000 shares**, implied VWAP is `5,708,965,000/(2565*1000)=2225.72`, inside the documented bar's [2225,2235] range. If Volume were **shares**, implied VWAP would be `2,225,717.35`, impossible relative to OHLC. This is **strong documentation-level evidence for lots**, not a live API contract guarantee. Verify per exchange/security type using actual authorized records; never hard-code 1,000 for odd-lot/other securities.

The same official example lists a tick at **09:00:08.306075** with `volume=2166` and price 2225. If that tick belongs to the first 09:01 Kbar, it represents **84.44%** of the Kbar's 2565 lots. This strongly motivates **isolating the opening auction** from the first Kbar's volume when computing continuous-session RVOL. The documentation alone cannot prove exact inclusion, auction semantics, tick clock conversion, or vendor bar label alignment; these must be checked from complete authenticated ticks against Kbars and TWSE anchors. Shioaji's 13:30 close and 14:30 after-hours ticks must also remain separate.

**Do not infer** from the 09:01 label that all vendor Kbars are bar-end-labelled, or from the arithmetic that all timestamps are correct. The published nanosecond epoch vs displayed local time has an eight-hour discrepancy; `tw_shioaji_timestamp_gate.py` correctly leaves every case BLOCKED. For Fugle, independently verify 09:35 bar label meaning and observation time; 09:37 remains an indicative candidate, never a proven fill.

Sources: https://sinotrade.github.io/zh/tutor/market_data/historical/ and https://developer.fugle.tw/docs/data/http-api/historical/candles/ .

## Next gate (no strategy tuning)

Acquire a **legally authorized, predeclared** same-stock/same-day Shioaji full tick + Kbar sample and independent Fugle 1m bars, with raw bytes, SHA256, retrieval UTC, account/license provenance, exchange, stock type, and volume units. Reconcile tick-to-Kbar OHLC, Amount/Volume implied VWAP, 09:00 auction, 13:24 last continuous print, 13:30 close, 14:30 after-hours, and bar timestamp conventions before any strategy return calculations. Without credentials, do not fetch or invent vendor responses. No notification.
