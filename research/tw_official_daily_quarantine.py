#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Collect a provenance-stamped, OFFICIAL DAILY anchor for later data validation.

No strategy, signals, P&L, or OOS performance is calculated here.
Data collected after 2026-04-01 are quarantined: do not tune on them.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
STOCKS = ("2330", "2317", "2881", "2603", "1519")
MONTHS = tuple(f"2026{m:02d}01" for m in range(4, 10))
FIELDS = ("stock_id", "date", "volume_shares", "turnover_twd",
          "open", "high", "low", "close", "trades", "source", "retrieved_at_utc")


def number(value: object) -> float:
    x = str(value).replace(",", "").strip()
    if x in ("", "--", "---", "-"):
        raise ValueError("non-trading or missing numeric value")
    y = float(x)
    if not math.isfinite(y):
        raise ValueError("nonfinite value")
    return y


def parse_month(payload: dict, sid: str, month: str, at: str) -> list[dict]:
    if payload.get("stat") != "OK" or not isinstance(payload.get("data"), list):
        raise ValueError(f"{sid}/{month}: bad status or missing data: {payload.get('stat')}")
    if len(payload["data"]) < 10:
        raise ValueError(f"{sid}/{month}: suspiciously short month")
    rows = []
    for raw in payload["data"]:
        if not isinstance(raw, list) or len(raw) < 9:
            raise ValueError(f"{sid}/{month}: malformed row")
        try:
            roc_y, mm, dd = map(int, str(raw[0]).split("/"))
            date = f"{roc_y + 1911:04d}-{mm:02d}-{dd:02d}"
            if date[:7] != f"{month[:4]}-{month[4:6]}":
                raise ValueError("date outside requested month")
            datetime.fromisoformat(date)
            volume = number(raw[1])
            turnover = number(raw[2])
            op, hi, lo, cl = (number(raw[i]) for i in (3, 4, 5, 6))
            trades = number(raw[8])
        except ValueError as exc:
            # A suspended/no-trade day is not a valid OHLC observation.
            if any(str(raw[i]).strip() in ("--", "---", "-", "") for i in (3, 4, 5, 6)):
                continue
            raise ValueError(f"{sid}/{month}: invalid row {raw!r}: {exc}") from exc
        if not (0 < lo <= min(op, cl) <= max(op, cl) <= hi):
            raise ValueError(f"{sid}/{date}: impossible OHLC")
        if volume < 0 or turnover < 0 or trades < 0:
            raise ValueError(f"{sid}/{date}: negative activity")
        rows.append(dict(stock_id=sid, date=date, volume_shares=volume,
                         turnover_twd=turnover, open=op, high=hi, low=lo,
                         close=cl, trades=trades, source=URL,
                         retrieved_at_utc=at))
    if not rows:
        raise ValueError(f"{sid}/{month}: no tradable daily rows")
    dates = [r["date"] for r in rows]
    if len(dates) != len(set(dates)):
        raise ValueError(f"{sid}/{month}: duplicate official date")
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="research_output/tw_source_quality/official_daily_2026")
    args = ap.parse_args()
    out = Path(args.out)
    raw_dir = out / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    sess = requests.Session()
    retry = Retry(total=3, backoff_factor=1.5, status_forcelist=[429, 500, 502, 503, 504])
    sess.mount("https://", HTTPAdapter(max_retries=retry))
    observations, manifest, failures = [], [], []
    for sid in STOCKS:
        for month in MONTHS:
            at = datetime.now(timezone.utc).isoformat()
            try:
                response = sess.get(URL, params={"date": month, "stockNo": sid,
                                                 "response": "json"},
                                    timeout=35, headers={"User-Agent": "Taiwan-data-quality-research/1.0"})
                response.raise_for_status()
                payload = response.json()
                rows = parse_month(payload, sid, month, at)
                raw_bytes = response.content
                (raw_dir / f"{sid}_{month}.json").write_bytes(raw_bytes)
                observations.extend(rows)
                manifest.append(dict(stock_id=sid, month=month, rows=len(rows),
                                     sha256=hashlib.sha256(raw_bytes).hexdigest(),
                                     retrieved_at_utc=at, http_status=response.status_code))
            except Exception as exc:
                failures.append(f"{sid}/{month}: {type(exc).__name__}: {exc}")
            time.sleep(0.25)
    observations.sort(key=lambda r: (r["stock_id"], r["date"]))
    with (out / "official_daily.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(observations)
    (out / "manifest.json").write_text(
        json.dumps(dict(source=URL, stocks=STOCKS, months=MONTHS,
                        files=manifest, errors=failures), ensure_ascii=False, indent=2),
        encoding="utf-8")
    count = len(manifest)
    status = "PASS_OFFICIAL_DAILY_ONLY" if count == len(STOCKS) * len(MONTHS) and not failures else "BLOCKED"
    report = [
        "# 2026-04 through 2026-09 official TWSE daily anchor",
        "",
        f"Status: **{status}**; official stock-months: {count}/{len(STOCKS)*len(MONTHS)}; stock-days: {len(observations)}.",
        "Predeclared symbols: " + ", ".join(STOCKS) + ".",
        "Original response bytes and SHA256 are retained in the workflow artifact.",
        "This is NOT independent intraday validation, NOT a tradable backtest, and NOT a confirmed edge.",
        "All dates after 2026-04-01 are QUARANTINED from strategy selection and parameter tuning.",
        "Must obtain independent minute/tick bars, corporate actions, point-in-time universe,",
        "next-tradable-bar execution, realistic capital occupancy and genuinely sealed OOS.",
        "",
        "## Fetch / validation errors",
        *(f"- {e}" for e in failures),
    ]
    (out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report), flush=True)
    return 0 if status.startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
