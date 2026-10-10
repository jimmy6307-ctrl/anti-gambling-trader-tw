#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed TWSE official-close vs independent Fugle 1-minute data probe.

Data-source QA only, NOT a trading backtest or edge certification.
Live mode needs FUGLE_API_KEY in environment. No key is written to disk.
Offline mode takes already acquired TWSE/Fugle raw JSON files.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

TWSE_URL = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
FUGLE_URL = "https://api.fugle.tw/marketdata/v1.0/stock/historical/candles/{stock}"
TAIPEI = ZoneInfo("Asia/Taipei")


def number(value):
    x = float(str(value).replace(",", "").strip())
    if not math.isfinite(x):
        raise ValueError("nonfinite numeric field")
    return x


def official_close(payload, target):
    if payload.get("stat") != "OK" or not isinstance(payload.get("data"), list):
        raise ValueError("invalid official TWSE response")
    found = []
    for row in payload["data"]:
        y, m, d = map(int, row[0].split("/"))
        if f"{y+1911:04d}-{m:02d}-{d:02d}" == target:
            found.append(number(row[6]))
    if len(found) != 1 or found[0] <= 0:
        raise ValueError("official date absent or duplicated")
    return found[0]


def inspect_fugle(payload, stock, target):
    if payload.get("symbol") != stock or str(payload.get("timeframe")) != "1":
        raise ValueError("wrong vendor symbol/timeframe")
    if not isinstance(payload.get("data"), list) or not payload["data"]:
        raise ValueError("empty vendor data")
    bars = []
    for row in payload["data"]:
        dt = datetime.fromisoformat(row["date"].replace("Z", "+00:00"))
        if dt.tzinfo is None:
            raise ValueError("vendor timestamp lacks timezone")
        dt = dt.astimezone(TAIPEI)
        if dt.date().isoformat() != target:
            raise ValueError("vendor bar outside requested day")
        op, hi, lo, cl = [number(row[k]) for k in ("open", "high", "low", "close")]
        vol = number(row["volume"])
        if not (0 < lo <= min(op, cl) <= max(op, cl) <= hi and vol >= 0):
            raise ValueError("invalid vendor OHLCV")
        bars.append((dt, op, hi, lo, cl, vol))
    clocks = [b[0].strftime("%H:%M") for b in bars]
    if len(clocks) != len(set(clocks)):
        raise ValueError("duplicate minute timestamps")
    bars.sort(key=lambda b: b[0])
    by_clock = {b[0].strftime("%H:%M"): b for b in bars}
    closing = by_clock.get("13:30")
    return {
        "bar_count": len(bars),
        "first_clock": bars[0][0].strftime("%H:%M"),
        "last_clock": bars[-1][0].strftime("%H:%M"),
        "last_close": bars[-1][4],
        "close_at_1330": closing[4] if closing else None,
        "bar_0900_volume_lots": by_clock["09:00"][5] if "09:00" in by_clock else None,
        "volume_sum_lots": sum(b[5] for b in bars),
        "sample_clocks": {
            k: {"close": by_clock[k][4], "volume_lots": by_clock[k][5]}
            for k in ("09:00", "09:05", "09:30", "13:20", "13:25", "13:30")
            if k in by_clock
        },
        "bar_label_semantics": "UNVERIFIED_NEEDS_INDEPENDENT_TICKS",
    }


def get_bytes(url, params, headers):
    import requests
    response = requests.get(url, params=params, headers=headers, timeout=35)
    response.raise_for_status()
    return response.content


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--stock", default="2330")
    ap.add_argument("--date", default="2026-03-31")
    ap.add_argument("--twse-json", type=Path)
    ap.add_argument("--fugle-json", type=Path)
    ap.add_argument("--out", type=Path,
                    default=Path("research_output/tw_independent_minute_probe"))
    args = ap.parse_args(argv)
    target_day = date.fromisoformat(args.date)
    args.out.mkdir(parents=True, exist_ok=True)
    result = {
        "stock": args.stock, "date": args.date,
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "BLOCKED", "strategy_gate": "BLOCKED",
        "independent_source": "Fugle", "official_source": "TWSE STOCK_DAY",
        "errors": [],
    }
    try:
        official_raw = args.twse_json.read_bytes() if args.twse_json else get_bytes(
            TWSE_URL,
            {"date": target_day.strftime("%Y%m01"),
             "stockNo": args.stock, "response": "json"},
            {"User-Agent": "Taiwan-data-audit/1.0"},
        )
        result["twse_sha256"] = hashlib.sha256(official_raw).hexdigest()
        result["official_close"] = official_close(json.loads(official_raw), args.date)
        (args.out / "twse_raw.json").write_bytes(official_raw)
    except Exception as exc:
        result["errors"].append("TWSE " + type(exc).__name__ + ": " + str(exc)[:180])
    try:
        if args.fugle_json:
            vendor_raw = args.fugle_json.read_bytes()
        else:
            key = os.environ.get("FUGLE_API_KEY", "")
            if not key:
                raise ValueError("FUGLE_API_KEY absent; no independent minute data")
            vendor_raw = get_bytes(
                FUGLE_URL.format(stock=args.stock),
                {"from": args.date, "to": args.date, "timeframe": "1",
                 "fields": "open,high,low,close,volume", "sort": "asc"},
                {"X-API-KEY": key, "User-Agent": "Taiwan-data-audit/1.0"},
            )
        result["fugle_sha256"] = hashlib.sha256(vendor_raw).hexdigest()
        result["vendor"] = inspect_fugle(json.loads(vendor_raw), args.stock, args.date)
        (args.out / "fugle_raw.json").write_bytes(vendor_raw)
    except Exception as exc:
        # Never log headers or API keys.
        result["errors"].append("Fugle " + type(exc).__name__ + ": "
                                + str(exc).split("FUGLE_API_KEY=")[0][:180])
    if "official_close" in result and "vendor" in result:
        vendor_close = result["vendor"]["close_at_1330"]
        if vendor_close is None:
            result["status"] = "BLOCKED_NO_1330_VENDOR_BAR"
        else:
            delta = round(vendor_close - result["official_close"], 6)
            result["vendor_1330_minus_official"] = delta
            result["status"] = ("ANCHOR_MATCH_ONLY" if abs(delta) < 1e-6
                                else "FAIL_VENDOR_OFFICIAL_CLOSE")
    # Even a perfect match does not establish bar timestamps, fillability,
    # point-in-time universe, adjustments, or sealed OOS.
    (args.out / "gate.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    (args.out / "report.md").write_text(
        "# Independent minute source quality probe\n\n"
        + f"- Stock/date: {args.stock} / {args.date}\n"
        + f"- Data status: **{result['status']}**\n"
        + "- Strategy gate: **BLOCKED** (no confirmed trading edge)\n"
        + f"- TWSE official close: {result.get('official_close', 'N/A')}\n"
        + f"- Fugle 13:30 bar close: {result.get('vendor', {}).get('close_at_1330', 'N/A')}\n"
        + "- A matching close does not prove timestamp semantics, auction coverage, or executable fills.\n"
        + "".join(f"- Error: {e}\n" for e in result["errors"]),
        encoding="utf-8",
    )
    print(json.dumps({k: v for k, v in result.items() if k != "vendor"},
                     ensure_ascii=False, indent=2))
    return 0 if result["status"] == "ANCHOR_MATCH_ONLY" else 2


if __name__ == "__main__":
    raise SystemExit(main())
