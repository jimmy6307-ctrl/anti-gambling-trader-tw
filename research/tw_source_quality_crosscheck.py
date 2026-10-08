#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Cross-check the archived 5-minute OHLCV with official TWSE daily data.

This is a DATA QUALITY audit, not a strategy search or new backtest.
- Keep the existing IS/OOS dates unchanged.
- Compare a small predeclared sample of listed stocks across three periods.
- Flag duplicate bar timestamps, zero-volume 09:00 bars, first nonzero bar time,
  and discrepancies versus TWSE official daily OHLCV.
- Never infer intraday bar timestamp semantics from daily OHLCV alone.
- Never promote any strategy to 'confirmed' based on this audit.
"""
from __future__ import annotations

import io
import math
import time
from pathlib import Path

import pandas as pd
import requests

OUT = Path("research_output/tw_source_quality")
CACHE = Path("research_output/cache_5m")
STOCKS = ("2330", "2317", "2881", "2603", "1519")
MONTHS = ("20240801", "20251001", "20260301")
TWSE = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
ARCHIVE = "https://raw.githubusercontent.com/voidful/tw_stocker/main/data/{sid}.csv"


def official_month(session: requests.Session, sid: str, month: str) -> pd.DataFrame:
    r = session.get(TWSE, params={"date": month, "stockNo": sid, "response": "json"},
                    timeout=30, headers={"User-Agent": "Mozilla/5.0 data-quality-research"})
    r.raise_for_status()
    obj = r.json()
    if obj.get("stat") != "OK" or not obj.get("data"):
        raise ValueError(f"TWSE returned stat={obj.get('stat')} for {sid} {month}")
    out = []
    for row in obj["data"]:
        try:
            yy, mm, dd = [int(v.strip()) for v in row[0].split("/")]
            dt = pd.Timestamp(year=yy + 1911, month=mm, day=dd)
            num = lambda v: float(str(v).replace(",", "").strip())
            out.append(dict(date=dt, twse_volume=num(row[1]), twse_open=num(row[3]),
                            twse_high=num(row[4]), twse_low=num(row[5]), twse_close=num(row[6])))
        except (ValueError, IndexError, TypeError):
            continue
    return pd.DataFrame(out)


def archive_bars(session: requests.Session, sid: str) -> tuple[pd.DataFrame, dict]:
    fp = CACHE / f"{sid}.csv"
    if fp.exists() and fp.stat().st_size > 100:
        raw = fp.read_bytes()
    else:
        r = session.get(ARCHIVE.format(sid=sid), timeout=60)
        r.raise_for_status()
        raw = r.content
        CACHE.mkdir(parents=True, exist_ok=True)
        fp.write_bytes(raw)
    x = pd.read_csv(io.BytesIO(raw))
    x["Datetime"] = pd.to_datetime(x["Datetime"], errors="coerce", utc=True).dt.tz_convert("Asia/Taipei")
    x = x.dropna(subset=["Datetime"]).copy()
    for c in ("Open", "High", "Low", "Close", "Volume"):
        x[c] = pd.to_numeric(x[c], errors="coerce")
    x = x.dropna(subset=["Open", "High", "Low", "Close"])
    total = len(x)
    duplicate = int(x["Datetime"].duplicated(keep=False).sum())
    conflicting_volume = int(
        (x.groupby("Datetime")["Volume"].nunique(dropna=False) > 1).sum()
    )
    # Follow existing research convention, but flag its ambiguity.
    x = x.sort_values("Datetime").drop_duplicates("Datetime", keep="last")
    x["date"] = x["Datetime"].dt.tz_localize(None).dt.normalize()
    x["time"] = x["Datetime"].dt.strftime("%H:%M")
    x = x[(x["time"] >= "09:00") & (x["time"] <= "13:30")].copy()
    stats = dict(stock_id=sid, raw_rows=total, duplicate_rows_involved=duplicate,
                 conflicting_volume_timestamp_groups=conflicting_volume,
                 deduped_regular_bars=len(x))
    return x, stats


def summarize_days(x: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    daily = []
    firsts = []
    opens = []
    for date, g in x.groupby("date", sort=True):
        g = g.sort_values("Datetime")
        at9 = g[g["time"] == "09:00"]
        if not at9.empty:
            opens.append(float(at9.iloc[0]["Volume"]) == 0)
        nz = g[g["Volume"] > 0]
        if not nz.empty:
            firsts.append(nz.iloc[0]["time"])
        daily.append(dict(date=date, archive_open=float(g.iloc[0]["Open"]),
                          archive_high=float(g["High"].max()),
                          archive_low=float(g["Low"].min()),
                          archive_close=float(g.iloc[-1]["Close"]),
                          archive_volume=float(g["Volume"].sum()),
                          n_bars=len(g)))
    mode = pd.Series(firsts).value_counts()
    stats = dict(days_with_0900=len(opens), zero_0900_count=sum(opens),
                 zero_0900_fraction=sum(opens)/len(opens) if opens else math.nan,
                 first_nonzero_bar_mode=str(mode.index[0]) if len(mode) else "NA")
    return pd.DataFrame(daily), stats


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    comparisons, diagnostics, errors = [], [], []
    for sid in STOCKS:
        try:
            bars, raw_stats = archive_bars(session, sid)
            daily, bar_stats = summarize_days(bars)
            diagnostics.append({**raw_stats, **bar_stats})
            for month in MONTHS:
                try:
                    off = official_month(session, sid, month)
                    if off.empty:
                        raise ValueError("No parsable TWSE records")
                    # Fixed first four common trading days of each month.
                    m = daily.merge(off, on="date", how="inner").sort_values("date").head(4)
                    for _, row in m.iterrows():
                        v = float(row["twse_volume"])
                        close = float(row["twse_close"])
                        comparisons.append(dict(
                            stock_id=sid, date=str(row["date"].date()),
                            n_bars=int(row["n_bars"]),
                            archive_volume=float(row["archive_volume"]), twse_volume=v,
                            volume_relative_error=(float(row["archive_volume"])/v-1) if v else math.nan,
                            archive_close=float(row["archive_close"]), twse_close=close,
                            close_relative_error=(float(row["archive_close"])/close-1) if close else math.nan,
                            archive_open=float(row["archive_open"]), twse_open=float(row["twse_open"]),
                        ))
                    if m.empty:
                        errors.append(f"{sid} {month}: no overlapping dates")
                except Exception as e:
                    errors.append(f"{sid} {month}: {type(e).__name__}: {e}")
                time.sleep(0.4)
        except Exception as e:
            errors.append(f"{sid}: {type(e).__name__}: {e}")
    comp = pd.DataFrame(comparisons)
    diag = pd.DataFrame(diagnostics)
    comp.to_csv(OUT / "daily_compare.csv", index=False, encoding="utf-8-sig")
    diag.to_csv(OUT / "bar_diagnostics.csv", index=False, encoding="utf-8-sig")
    lines = [
        "# 5-minute source vs official TWSE daily OHLCV audit", "",
        f"Fixed sample: stocks {', '.join(STOCKS)}; months {', '.join(MONTHS)}.",
        "Archived bars: voidful/tw_stocker. Daily comparator: TWSE rwd/zh/afterTrading/STOCK_DAY.",
        "Official daily volume can include trades not represented in regular-session 5-minute bars;",
        "differences are diagnostic, not necessarily data corruption.", "",
        "## Archive structural diagnostics", "",
        diag.to_markdown(index=False) if not diag.empty else "NO DATA", "",
        "## TWSE daily comparison", "",
    ]
    if comp.empty:
        lines.append("BLOCKED: no official daily observations could be matched.")
    else:
        vol = comp["volume_relative_error"].abs().dropna()
        cls = comp["close_relative_error"].abs().dropna()
        lines += [
            f"Matched stock-days: {len(comp)}.",
            f"Median absolute daily volume relative error: {vol.median():.2%}.",
            f"95th percentile absolute daily close relative error: {cls.quantile(.95):.2%}.",
            f"Stock-days with >10% volume discrepancy: {int((vol > .10).sum())}/{len(vol)}.",
            "", comp.to_markdown(index=False), "",
        ]
    lines += [
        "## Research readiness gate", "",
        "**NOT VERIFIED for intraday execution.** Official daily OHLCV comparison cannot",
        "resolve whether 09:35 bar timestamps mark bar OPEN or bar CLOSE, nor whether",
        "same-bar close could be executed after observing the signal.",
        "Require independently sourced minute/trade data, next-bar fill tests,",
        "corporate-action treatment, a point-in-time universe, and fresh holdout data.",
        "Do not notify the user of a profitable strategy from this audit.", "",
        "## Source/API errors", "",
        *(f"- {e}" for e in errors),
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:24]), flush=True)


if __name__ == "__main__":
    main()
    # Data-only follow-on: capture previously unavailable 2026 official daily
    # anchors in the existing quality-audit artifact. Never calculate P&L here.
    from tw_official_daily_quarantine import main as collect_official_daily
    raise SystemExit(collect_official_daily())
