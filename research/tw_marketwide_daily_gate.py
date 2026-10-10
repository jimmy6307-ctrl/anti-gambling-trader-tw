#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Official TWSE historical marketwide DAILY QA only; never certify strategy edge.
Collect selected past market dates from MI_INDEX, compare 2330 against STOCK_DAY.
No intraday data, no survivorship-free universe, no strategy signals or P&L.
"""
import argparse
import csv
import hashlib
import html
import json
import math
import re
import time
from datetime import date, datetime, timezone
from pathlib import Path
import requests

MI = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
DAY = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
DATES = ("2024-08-05", "2025-10-01", "2026-03-31", "2026-10-07")
FIELDS = ("date", "stock_id", "name", "volume_shares", "turnover_twd", "trades", "open", "high", "low", "close", "source")
HEADERS = {"User-Agent": "TWSE-data-quality-research/1.0", "Accept": "application/json"}


def clean(x):
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]*>", "", str(x))))


def number(x):
    s = clean(x).replace(",", "")
    if s in ("", "-", "--", "---", "—", "N/A"):
        raise ValueError("missing number")
    v = float(s)
    if not math.isfinite(v):
        raise ValueError("nonfinite number")
    return v


def parse_mi(payload, expected):
    if payload.get("stat") != "OK" or not isinstance(payload.get("tables"), list):
        raise ValueError("MI_INDEX invalid status or missing tables")
    matches = [t for t in payload["tables"] if "每日收盤行情" in clean(t.get("title", ""))]
    if len(matches) != 1:
        raise ValueError("MI_INDEX daily close table missing/ambiguous")
    table = matches[0]
    title = clean(table.get("title", ""))
    match = re.search(r"(\d{2,4})年(\d{1,2})月(\d{1,2})日", title)
    if not match:
        raise ValueError("MI_INDEX title has no trade date")
    yy, mm, dd = map(int, match.groups())
    if yy < 1911:
        yy += 1911
    if date(yy, mm, dd).isoformat() != expected:
        raise ValueError("MI_INDEX returned a different trade date")
    fields, data = table.get("fields"), table.get("data")
    if not isinstance(fields, list) or not isinstance(data, list) or not data:
        raise ValueError("MI_INDEX missing fields/data")
    ix = {clean(x): i for i, x in enumerate(fields)}
    needed = ("證券代號", "證券名稱", "成交股數", "成交筆數", "成交金額", "開盤價", "最高價", "最低價", "收盤價")
    if any(k not in ix for k in needed):
        raise ValueError("MI_INDEX field schema drift: " + str([k for k in needed if k not in ix]))
    result, seen = [], set()
    skips = {"non_equity_code_shape": 0, "no_trade": 0}
    for row in data:
        if not isinstance(row, list) or len(row) < len(fields):
            raise ValueError("MI_INDEX malformed row")
        sid = clean(row[ix["證券代號"]])
        # Exclude 0050-like ETFs; NOT a complete historical common-stock classifier.
        if not re.fullmatch(r"[1-9]\d{3}", sid):
            skips["non_equity_code_shape"] += 1
            continue
        if sid in seen:
            raise ValueError("duplicate stock id: " + sid)
        seen.add(sid)
        try:
            op, hi, lo, cl = (number(row[ix[k]]) for k in ("開盤價", "最高價", "最低價", "收盤價"))
            vol, turn, trades = (number(row[ix[k]]) for k in ("成交股數", "成交金額", "成交筆數"))
        except ValueError:
            skips["no_trade"] += 1
            continue
        if not (0 < lo <= min(op, cl) <= max(op, cl) <= hi and min(vol, turn, trades) >= 0):
            raise ValueError("impossible OHLCV: " + sid)
        result.append(dict(date=expected, stock_id=sid, name=clean(row[ix["證券名稱"]]),
                           volume_shares=int(vol), turnover_twd=int(turn), trades=int(trades),
                           open=op, high=hi, low=lo, close=cl, source=MI))
    if not result:
        raise ValueError("no stock rows")
    return sorted(result, key=lambda r: r["stock_id"]), skips


def parse_stock_day(payload, expected):
    if payload.get("stat") != "OK" or not isinstance(payload.get("data"), list):
        raise ValueError("STOCK_DAY bad response")
    rows = []
    for row in payload["data"]:
        yy, mm, dd = map(int, str(row[0]).split("/"))
        if date(yy + 1911, mm, dd).isoformat() == expected:
            rows.append({k: number(row[i]) for k, i in (("open", 3), ("high", 4), ("low", 5), ("close", 6))})
    if len(rows) != 1:
        raise ValueError("STOCK_DAY anchor missing or duplicate")
    return rows[0]


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dates", nargs="+", default=list(DATES))
    ap.add_argument("--out", type=Path, default=Path("research_output/tw_marketwide_daily_gate"))
    ap.add_argument("--min-stocks", type=int, default=900)
    args = ap.parse_args(argv)
    rawdir = args.out / "raw"
    rawdir.mkdir(parents=True, exist_ok=True)
    manifest = dict(sources=[MI, DAY], requested=args.dates, data_gate="BLOCKED",
                    strategy_gate="BLOCKED", holdout_quarantined=True, dates=[], errors=[])
    all_rows = []
    session = requests.Session()
    for target in args.dates:
        try:
            date.fromisoformat(target)
            stamp = target.replace("-", "")
            at = datetime.now(timezone.utc).isoformat()
            r = session.get(MI, params={"date": stamp, "type": "ALLBUT0999", "response": "json"},
                            headers=HEADERS, timeout=45)
            r.raise_for_status()
            rows, skipped = parse_mi(r.json(), target)
            if len(rows) < args.min_stocks:
                raise ValueError(f"marketwide rows {len(rows)} < {args.min_stocks}")
            anchor = next((x for x in rows if x["stock_id"] == "2330"), None)
            if anchor is None:
                raise ValueError("2330 missing from marketwide data")
            r2 = session.get(DAY, params={"date": stamp[:6] + "01", "stockNo": "2330", "response": "json"},
                             headers=HEADERS, timeout=45)
            r2.raise_for_status()
            official = parse_stock_day(r2.json(), target)
            diff = {k: round(anchor[k] - official[k], 6) for k in ("open", "high", "low", "close")}
            if any(abs(v) > 1e-6 for v in diff.values()):
                raise ValueError("two TWSE endpoints disagree: " + str(diff))
            (rawdir / f"mi_{stamp}.json").write_bytes(r.content)
            (rawdir / f"stockday_2330_{stamp}.json").write_bytes(r2.content)
            all_rows.extend(rows)
            manifest["dates"].append(dict(date=target, retrieved_at_utc=at, rows=len(rows),
                skipped=skipped, mi_sha256=hashlib.sha256(r.content).hexdigest(),
                stockday_sha256=hashlib.sha256(r2.content).hexdigest(),
                anchor_2330_diff=diff, status="PASS_OFFICIAL_DAILY_ONLY"))
            print(f"PASS {target}: {len(rows)} rows; 2330 OHLC matches", flush=True)
        except Exception as exc:
            manifest["errors"].append(f"{target}: {type(exc).__name__}: {str(exc)[:240]}")
            print("BLOCKED " + manifest["errors"][-1], flush=True)
        time.sleep(0.5)
    with (args.out / "daily_snapshot.csv").open("w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(all_rows)
    if len(manifest["dates"]) == len(args.dates) and not manifest["errors"]:
        manifest["data_gate"] = "PASS_MARKETWIDE_DAILY_ONLY"
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    report = ["# TWSE historical marketwide official daily QA", "",
        f"Data gate: **{manifest['data_gate']}**; sessions {len(manifest['dates'])}/{len(args.dates)}; rows {len(all_rows)}.",
        "MI_INDEX full listed-market daily snapshots are checked against STOCK_DAY 2330 for each date.",
        "Raw JSON, SHA256, retrieval time and normalized CSV saved in workflow artifact.",
        "Four-digit traded securities only: NOT complete historical stock universe (OTC, suspensions, delistings, corporate actions).",
        "**No independent minute/tick data; no next-bar fills; no untouched OOS; no strategy pass.**",
        "New dates quarantined from strategy tuning.", "", "## Errors",
        *(f"- {x}" for x in manifest["errors"])]
    (args.out / "report.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report[:8]), flush=True)
    return 0 if manifest["data_gate"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
