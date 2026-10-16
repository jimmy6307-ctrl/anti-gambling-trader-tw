#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fail-closed audit of 2330 2026-03-31 TWSE close vs archived minute bars.

Data validation only; does not certify minute bars or a trading strategy.
Preserves official raw JSON, archive SHA256, machine-readable gate and report.
"""
from __future__ import annotations
import hashlib
import io
import json
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
import pandas as pd
import requests

OUT = Path("research_output/tw_2330_anchor")
TWSE = "https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY"
ARCHIVE = "https://raw.githubusercontent.com/voidful/tw_stocker/main/data/2330.csv"
TARGET = "2026-03-31"

def run():
    OUT.mkdir(parents=True, exist_ok=True)
    report = {"time_taipei": datetime.now(ZoneInfo("Asia/Taipei")).isoformat(),
              "target": TARGET, "official_url": TWSE, "archive_url": ARCHIVE,
              "daily_close_gate": "FAIL", "minute_gate": "NOT_TESTED",
              "strategy_gate": "BLOCKED", "errors": []}
    session = requests.Session()
    session.headers["User-Agent"] = "Mozilla/5.0 Taiwan-data-quality-research"
    try:
        r = session.get(TWSE, params={"date": "20260301", "stockNo": "2330",
                                      "response": "json"}, timeout=40)
        r.raise_for_status()
        (OUT / "twse_2330_202603_raw.json").write_bytes(r.content)
        payload = r.json()
        if payload.get("stat") != "OK":
            raise ValueError("TWSE status " + str(payload.get("stat")))
        official = {}
        for row in payload.get("data", []):
            y, m, d = [int(v) for v in row[0].split("/")]
            official[f"{y+1911:04d}-{m:02d}-{d:02d}"] = float(row[6].replace(",", ""))
        if TARGET not in official:
            raise ValueError("official date missing")
        report["official_close"] = official[TARGET]
    except Exception as exc:
        report["errors"].append("official: " + type(exc).__name__ + ": " + str(exc))
    try:
        r = session.get(ARCHIVE, timeout=120)
        r.raise_for_status()
        report["archive_sha256"] = hashlib.sha256(r.content).hexdigest()
        df = pd.read_csv(io.BytesIO(r.content))
        df["Datetime"] = pd.to_datetime(df["Datetime"], errors="coerce", utc=True).dt.tz_convert("Asia/Taipei")
        df = df.dropna(subset=["Datetime"]).sort_values("Datetime", kind="stable")
        report["duplicate_rows"] = int(df.duplicated("Datetime", keep=False).sum())
        df = df.drop_duplicates("Datetime", keep="last")
        df["date"] = df["Datetime"].dt.strftime("%Y-%m-%d")
        df["clock"] = df["Datetime"].dt.strftime("%H:%M")
        report["archive_last_date"] = df["date"].max()
        target = df[(df["date"] == TARGET) & (df["clock"].between("09:00", "13:30"))]
        if target.empty:
            raise ValueError("archive target date missing")
        target = target.sort_values("Datetime")
        last = target.iloc[-1]
        report["archive_last_clock"] = last["clock"]
        report["archive_last_close"] = float(last["Close"])
        at9 = target[target["clock"] == "09:00"]
        report["zero_0900_volume"] = bool(len(at9) and float(at9.iloc[-1]["Volume"]) == 0)
    except Exception as exc:
        report["errors"].append("archive: " + type(exc).__name__ + ": " + str(exc))
    if "official_close" in report and "archive_last_close" in report:
        report["close_difference"] = report["archive_last_close"] - report["official_close"]
        report["daily_close_gate"] = ("PASS" if abs(report["close_difference"]) < 1e-9 else "FAIL")
    report["strategy_gate"] = "BLOCKED"  # Even a matching close cannot validate fills.
    (OUT / "gate.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT / "report.md").write_text(
        "# TWSE 2330 official-close anchor\n\n"
        + "Data-quality audit only; no new trading strategy or validated edge.\n\n"
        + "\n".join(f"- {k}: {v}" for k, v in report.items()) + "\n",
        encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
if __name__ == "__main__":
    run()
