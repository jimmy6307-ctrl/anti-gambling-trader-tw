#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frozen Taiwan compression-breakout hypothesis.

One hypothesis only (no parameter search):
- decision/entry at 09:35
- prior close > MA20 > MA60
- 09:35 price breaks prior 20-day high, extension <= 2%
- 09:35 RVOL > 1.5
- sector is top-3 by 09:35 return and breadth >= 2
- prior 5-day median daily range% <= 75% of prior 20-day median range%
- fixed 5 trading-day hold
- round-trip cost 0.685%

Research protocol:
IS 2024-03-01..2025-03-31 must independently pass avg_net > 0 and PF > 1.2
with >= 30 trades before OOS is considered confirmatory.
OOS 2025-04-01..2026-04-01 must also pass, and remain positive/PF>1.2 after
removing the largest-contribution stock. This script intentionally does not tune thresholds.
"""
from __future__ import annotations

import math
from pathlib import Path
import pandas as pd

from tw_breakout_oos_research import (
    UNIVERSE, COST, IS_START, IS_END, OOS_START, OOS_END,
    download, features, fixed_return, metrics,
)

OUT = Path("research_output/tw_compression_breakout")


def daily_compression(bars: pd.DataFrame) -> pd.DataFrame:
    d = (bars.groupby("date", sort=True)
         .agg(high=("High", "max"), low=("Low", "min"), close=("Close", "last"))
         .reset_index())
    d["range_pct"] = (d["high"] - d["low"]) / d["close"].replace(0, pd.NA)
    d["range5_med"] = d["range_pct"].rolling(5, min_periods=5).median().shift(1)
    d["range20_med"] = d["range_pct"].rolling(20, min_periods=15).median().shift(1)
    d["compression_ratio"] = d["range5_med"] / d["range20_med"]
    return d[["date", "compression_ratio"]]


def pct(x: float) -> str:
    return "NA" if pd.isna(x) else f"{x*100:.2f}%"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    feat_parts, bars_map = [], {}
    for sid, ind in UNIVERSE:
        try:
            b = download(sid)
        except Exception as e:
            print(f"SKIP {sid}: {e}")
            continue
        f = features(b, ind)
        c = daily_compression(b)
        f = f.merge(c, on="date", how="left")
        feat_parts.append(f)
        bars_map[sid] = b

    allf = pd.concat(feat_parts, ignore_index=True)
    allf = allf.dropna(subset=["ret935", "rvol935", "ma20", "ma60", "high20", "compression_ratio"])

    sec = (allf.groupby(["date", "industry"])
           .agg(sector_ret=("ret935", "mean"), breadth=("ret935", lambda s: int((s > 0).sum())))
           .reset_index())
    sec["sector_rank"] = sec.groupby("date")["sector_ret"].rank(ascending=False, method="first")
    allf = allf.merge(sec, on=["date", "industry"], how="left")

    mask = (
        allf["trend"] & allf["break20"] & (allf["ext20"] <= 0.02) &
        (allf["rvol935"] > 1.5) & (allf["sector_rank"] <= 3) &
        (allf["breadth"] >= 2) & (allf["compression_ratio"] <= 0.75)
    )

    rows = []
    for _, r in allf[mask].iterrows():
        sid = str(r["stock_id"])
        gross = fixed_return(bars_map[sid], r["date"], float(r["p935"]), 5)
        if gross is None:
            continue
        if IS_START.normalize() <= r["date"] <= IS_END.normalize():
            period = "IS"
        elif OOS_START.normalize() <= r["date"] <= OOS_END.normalize():
            period = "OOS"
        else:
            continue
        rows.append({
            "period": period, "date": r["date"].date().isoformat(), "stock_id": sid,
            "industry": r["industry"], "entry": r["p935"], "rvol935": r["rvol935"],
            "sector_rank": r["sector_rank"], "breadth": r["breadth"],
            "compression_ratio": r["compression_ratio"], "gross": gross, "net": gross - COST,
        })

    t = pd.DataFrame(rows)
    t.to_csv(OUT / "trades.csv", index=False, encoding="utf-8-sig")
    if t.empty:
        (OUT / "report.md").write_text("# Compression breakout\n\nNo trades.\n", encoding="utf-8")
        print("No trades")
        return

    ism = metrics(t[t["period"] == "IS"])
    oos = t[t["period"] == "OOS"].copy()
    oosm = metrics(oos)
    contrib = oos.groupby("stock_id")["net"].sum().sort_values(ascending=False)
    top_sid = str(contrib.index[0]) if len(contrib) else ""
    drop = oos[oos["stock_id"] != top_sid] if top_sid else oos
    dropm = metrics(drop)

    is_pass = ism["trades"] >= 30 and ism["avg_net"] > 0 and ism["pf"] > 1.2
    oos_pass = oosm["trades"] >= 20 and oosm["avg_net"] > 0 and oosm["pf"] > 1.2
    robust_pass = dropm["trades"] >= 15 and dropm["avg_net"] > 0 and dropm["pf"] > 1.2
    confirmed = bool(is_pass and oos_pass and robust_pass)

    summary = pd.DataFrame([
        {"sample":"IS", **ism},
        {"sample":"OOS", **oosm},
        {"sample":f"OOS_DROP_TOP_{top_sid}", **dropm},
    ])
    summary.to_csv(OUT / "summary.csv", index=False, encoding="utf-8-sig")

    monthly = oos.assign(month=oos["date"].str[:7]).groupby("month")["net"].agg(["count","mean","sum"])
    monthly.to_csv(OUT / "oos_monthly.csv", encoding="utf-8-sig")
    positive_month_share = float((monthly["sum"] > 0).mean()) if len(monthly) else math.nan

    lines = [
        "# 整理壓縮後第一次突破：凍結假說驗證",
        "",
        "規則：09:35、20日新高、趨勢多頭、RVOL>1.5、產業前3且breadth>=2、突破延伸<=2%、前5日波動中位數 <= 前20日的75%、固定持有5日。",
        f"成本：{COST*100:.3f}% round-trip。",
        "",
        f"IS：{ism['trades']}筆，勝率 {pct(ism['win_rate'])}，平均 {pct(ism['avg_net'])}，中位數 {pct(ism['median_net'])}，PF {ism['pf']:.2f}，PASS={is_pass}",
        f"OOS：{oosm['trades']}筆，勝率 {pct(oosm['win_rate'])}，平均 {pct(oosm['avg_net'])}，中位數 {pct(oosm['median_net'])}，PF {oosm['pf']:.2f}，PASS={oos_pass}",
        f"OOS移除最大貢獻股票 {top_sid}：{dropm['trades']}筆，平均 {pct(dropm['avg_net'])}，PF {dropm['pf']:.2f}，PASS={robust_pass}",
        f"OOS正報酬月份占比：{pct(positive_month_share)}",
        "",
        f"CONFIRMED={confirmed}",
        "",
        "只有 IS、OOS、移除最大贏家三關全部通過，才算值得擴大全市場；否則淘汰。",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
