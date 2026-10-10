#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""台股「第一次突破」探索 + 一年樣本外驗證。

目的：不要再把『熱門 + 爆量』直接當買點，而是測試：
- 09:35 才判斷，降低開盤雜訊
- 價格突破前 20/60 交易日高點
- 前一日趨勢結構：prev_close > MA20 > MA60
- 09:35 RVOL > 1.5
- 可選：產業前 3 強 + 同產業至少 2 檔上漲

研究設計：
- IS（開發）：2024-03-01 ~ 2025-03-31
- OOS（凍結驗證）：2025-04-01 ~ 2026-04-01
- 只用 IS 排名候選規則；OOS 僅驗證，不拿來挑參數。
- 成本 0.685% round-trip（手續費、證交稅、雙邊滑價）。
- 固定持有 3/5/10 個交易日。
- 額外做 OOS『移除最大貢獻股票』穩健性檢查。

資料：voidful/tw_stocker 公開 5 分 K CSV。
這仍是有限代表股探索，不是全市場最終結論。
"""
from __future__ import annotations

import io
import math
import time
from pathlib import Path

import pandas as pd
import requests

RAW = "https://raw.githubusercontent.com/voidful/tw_stocker/main/data/{stock_id}.csv"
UNIVERSE = [
    ("2330", "半導體業"), ("2408", "半導體業"), ("3034", "半導體業"), ("6488", "半導體業"),
    ("3231", "電腦及週邊設備業"), ("2357", "電腦及週邊設備業"), ("3017", "電腦及週邊設備業"), ("6669", "電腦及週邊設備業"),
    ("2317", "其他電子業"), ("3665", "其他電子業"),
    ("2881", "金融保險業"), ("2882", "金融保險業"), ("2883", "金融保險業"), ("2884", "金融保險業"), ("2891", "金融保險業"),
    ("2603", "航運業"), ("2615", "航運業"), ("2609", "航運業"), ("2618", "航運業"),
    ("2412", "通信網路業"), ("3045", "通信網路業"), ("4904", "通信網路業"),
    ("1513", "電機機械"), ("1519", "電機機械"), ("2049", "電機機械"), ("1504", "電機機械"),
]
COST = 0.00685
IS_START = pd.Timestamp("2024-03-01", tz="Asia/Taipei")
IS_END = pd.Timestamp("2025-03-31", tz="Asia/Taipei")
OOS_START = pd.Timestamp("2025-04-01", tz="Asia/Taipei")
OOS_END = pd.Timestamp("2026-04-01", tz="Asia/Taipei")
OUT = Path("research_output/tw_breakout_oos")
CACHE = Path("research_output/cache_5m")


def download(stock_id: str) -> pd.DataFrame:
    CACHE.mkdir(parents=True, exist_ok=True)
    fp = CACHE / f"{stock_id}.csv"
    if fp.exists() and fp.stat().st_size > 100:
        raw = fp.read_bytes()
    else:
        r = requests.get(RAW.format(stock_id=stock_id), timeout=90,
                         headers={"User-Agent": "tw-breakout-oos/1.0"})
        r.raise_for_status()
        raw = r.content
        fp.write_bytes(raw)
        time.sleep(0.08)
    df = pd.read_csv(io.BytesIO(raw))
    dt = pd.to_datetime(df["Datetime"], errors="coerce", utc=True)
    df["Datetime"] = dt.dt.tz_convert("Asia/Taipei")
    df = df.dropna(subset=["Datetime"]).sort_values("Datetime")
    df = df.drop_duplicates("Datetime", keep="last")
    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Volume"] = df["Volume"].fillna(0.0)
    df["stock_id"] = stock_id
    df["date"] = df["Datetime"].dt.normalize()
    df["time"] = df["Datetime"].dt.strftime("%H:%M")
    return df[(df["time"] >= "09:00") & (df["time"] <= "13:30")].copy()


def features(bars: pd.DataFrame, industry: str) -> pd.DataFrame:
    rows = []
    for d, g in bars.groupby("date", sort=True):
        g = g.sort_values("Datetime")
        r935 = g[g["time"] == "09:35"]
        if r935.empty:
            continue
        pre = g[g["time"] <= "09:35"]
        rows.append({
            "date": d,
            "stock_id": g["stock_id"].iloc[0],
            "industry": industry,
            "p935": float(r935.iloc[-1]["Close"]),
            "v935": float(pre["Volume"].sum()),
            "open": float(g.iloc[0]["Open"]),
            "high": float(g["High"].max()),
            "low": float(g["Low"].min()),
            "close": float(g.iloc[-1]["Close"]),
        })
    x = pd.DataFrame(rows).sort_values("date")
    if x.empty:
        return x
    x["prev_close"] = x["close"].shift(1)
    x["ret935"] = x["p935"] / x["prev_close"] - 1
    x["ma20"] = x["close"].rolling(20).mean().shift(1)
    x["ma60"] = x["close"].rolling(60).mean().shift(1)
    x["high20"] = x["high"].rolling(20).max().shift(1)
    x["high60"] = x["high"].rolling(60).max().shift(1)
    x["avg_v93520"] = x["v935"].rolling(20, min_periods=15).mean().shift(1)
    x["rvol935"] = x["v935"] / x["avg_v93520"]
    x["trend"] = (x["prev_close"] > x["ma20"]) & (x["ma20"] > x["ma60"])
    x["break20"] = x["p935"] > x["high20"]
    x["break60"] = x["p935"] > x["high60"]
    x["ext20"] = x["p935"] / x["high20"] - 1
    return x


def fixed_return(bars: pd.DataFrame, entry_date: pd.Timestamp, entry: float, hold: int) -> float | None:
    dates = sorted(bars["date"].drop_duplicates().tolist())
    dates = [d for d in dates if d >= entry_date]
    if len(dates) <= hold:
        return None
    exd = dates[hold]
    g = bars[bars["date"] == exd].sort_values("Datetime")
    if g.empty:
        return None
    return float(g.iloc[-1]["Close"]) / entry - 1


def pf(s: pd.Series) -> float:
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    return pos / neg if neg > 0 else float("inf")


def metrics(df: pd.DataFrame) -> dict:
    s = df["net"].dropna()
    return {
        "trades": len(s),
        "win_rate": float((s > 0).mean()) if len(s) else math.nan,
        "avg_net": float(s.mean()) if len(s) else math.nan,
        "median_net": float(s.median()) if len(s) else math.nan,
        "pf": pf(s) if len(s) else math.nan,
        "p10": float(s.quantile(.1)) if len(s) else math.nan,
        "p90": float(s.quantile(.9)) if len(s) else math.nan,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    feat_parts, bars_map = [], {}
    coverage = []
    print("讀取代表股 5 分 K...")
    for i, (sid, ind) in enumerate(UNIVERSE, 1):
        try:
            b = download(sid)
        except Exception as e:
            print(f"[{i:02d}] {sid} SKIP {e}")
            coverage.append((sid, ind, 0))
            continue
        f = features(b, ind)
        feat_parts.append(f)
        bars_map[sid] = b
        coverage.append((sid, ind, len(f)))
        print(f"[{i:02d}] {sid} {ind}: {len(f)} sessions")

    allf = pd.concat(feat_parts, ignore_index=True)
    allf = allf.dropna(subset=["ret935", "rvol935", "ma20", "ma60", "high20", "high60"])

    # 當日產業強度：09:35 同產業平均漲幅；breadth = 上漲檔數。
    sec = (allf.groupby(["date", "industry"])
           .agg(sector_ret=("ret935", "mean"),
                breadth=("ret935", lambda s: int((s > 0).sum())))
           .reset_index())
    sec["sector_rank"] = sec.groupby("date")["sector_ret"].rank(ascending=False, method="first")
    allf = allf.merge(sec, on=["date", "industry"], how="left")

    # 預先宣告少量候選，不看 OOS 才新增。
    base = allf["trend"] & (allf["rvol935"] > 1.5)
    masks = {
        "B20": base & allf["break20"],
        "B20_SECTOR": base & allf["break20"] & (allf["sector_rank"] <= 3) & (allf["breadth"] >= 2),
        "B60": base & allf["break60"],
        "B60_SECTOR": base & allf["break60"] & (allf["sector_rank"] <= 3) & (allf["breadth"] >= 2),
        # 限制突破後 09:35 不超過舊 20 日高點 2%，避免已經垂直噴太遠。
        "B20_SECTOR_LOWEXT": base & allf["break20"] & (allf["sector_rank"] <= 3) & (allf["breadth"] >= 2) & (allf["ext20"] <= .02),
    }

    trades = []
    for rule, mask in masks.items():
        cand = allf[mask].copy()
        for _, r in cand.iterrows():
            sid = str(r["stock_id"])
            for hold in (3, 5, 10):
                gross = fixed_return(bars_map[sid], r["date"], float(r["p935"]), hold)
                if gross is None:
                    continue
                period = "IS" if IS_START.normalize() <= r["date"] <= IS_END.normalize() else (
                    "OOS" if OOS_START.normalize() <= r["date"] <= OOS_END.normalize() else None)
                if period is None:
                    continue
                trades.append({
                    "period": period, "rule": rule, "hold": hold,
                    "date": r["date"].date().isoformat(), "stock_id": sid,
                    "industry": r["industry"], "entry": r["p935"],
                    "ret935": r["ret935"], "rvol935": r["rvol935"],
                    "sector_rank": r["sector_rank"], "breadth": r["breadth"],
                    "gross": gross, "net": gross - COST,
                })

    t = pd.DataFrame(trades)
    t.to_csv(OUT / "trades.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(coverage, columns=["stock_id", "industry", "sessions"]).to_csv(
        OUT / "coverage.csv", index=False, encoding="utf-8-sig")

    rows = []
    for (period, rule, hold), g in t.groupby(["period", "rule", "hold"]):
        rows.append({"period": period, "rule": rule, "hold": hold, **metrics(g)})
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / "summary.csv", index=False, encoding="utf-8-sig")

    # 只用 IS 選：先要求 >= 40 筆，再按 avg_net，其次 PF 排名。
    isx = summary[(summary["period"] == "IS") & (summary["trades"] >= 40)].copy()
    if isx.empty:
        chosen = summary[summary["period"] == "IS"].sort_values(["avg_net", "pf"], ascending=False).iloc[0]
    else:
        chosen = isx.sort_values(["avg_net", "pf"], ascending=False).iloc[0]
    rule, hold = chosen["rule"], int(chosen["hold"])
    oos = t[(t["period"] == "OOS") & (t["rule"] == rule) & (t["hold"] == hold)].copy()
    oos_m = metrics(oos)

    contrib = oos.groupby("stock_id")["net"].sum().sort_values(ascending=False)
    top_sid = str(contrib.index[0]) if len(contrib) else ""
    oos_drop = oos[oos["stock_id"] != top_sid] if top_sid else oos
    drop_m = metrics(oos_drop)

    robust = pd.DataFrame([
        {"sample": "OOS_ALL", "rule": rule, "hold": hold, **oos_m},
        {"sample": f"OOS_DROP_TOP_{top_sid}", "rule": rule, "hold": hold, **drop_m},
    ])
    robust.to_csv(OUT / "chosen_rule_robustness.csv", index=False, encoding="utf-8-sig")

    # 人類可讀報告。
    def pct(x): return "NA" if pd.isna(x) else f"{x*100:.2f}%"
    lines = [
        "# 台股第一次突破：樣本外研究",
        "",
        f"IS：{IS_START.date()} ~ {IS_END.date()}；OOS：{OOS_START.date()} ~ {OOS_END.date()}",
        f"成本：{COST*100:.3f}% round-trip；進場：09:35。",
        "",
        "## 凍結規則",
        "",
        "B20 = 20 日新高 + prev_close > MA20 > MA60 + RVOL>1.5",
        "B20_SECTOR = B20 + 產業前3強 + 同產業至少2檔上漲",
        "B60 = 60 日新高 + 趨勢 + RVOL",
        "B60_SECTOR = B60 + 產業條件",
        "B20_SECTOR_LOWEXT = B20_SECTOR + 突破幅度 <=2%",
        "",
        "## IS 選出的唯一規則",
        "",
        f"**{rule} / 持有 {hold} 日**：IS {int(chosen['trades'])} 筆，勝率 {pct(chosen['win_rate'])}，平均 {pct(chosen['avg_net'])}，中位數 {pct(chosen['median_net'])}，PF {chosen['pf']:.2f}。",
        "",
        "## 真正要看的 OOS 一年",
        "",
        f"全部：{oos_m['trades']} 筆，勝率 {pct(oos_m['win_rate'])}，平均 {pct(oos_m['avg_net'])}，中位數 {pct(oos_m['median_net'])}，PF {oos_m['pf']:.2f}。",
        f"移除最大貢獻股票 {top_sid} 後：{drop_m['trades']} 筆，勝率 {pct(drop_m['win_rate'])}，平均 {pct(drop_m['avg_net'])}，中位數 {pct(drop_m['median_net'])}，PF {drop_m['pf']:.2f}。",
        "",
        "## 判讀",
        "",
        "只有 OOS 平均為正、PF > 1.2，而且移除最大貢獻股票後仍為正，才值得擴大全市場測試。否則淘汰。",
        "",
        "> 限制：目前仍只有約 25 檔代表股；這一步只負責淘汰爛假說，不負責宣稱可直接下單。",
    ]
    (OUT / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("\n=== ALL SUMMARY ===")
    print(summary.sort_values(["period", "avg_net"], ascending=[True, False]).to_string(index=False))


if __name__ == "__main__":
    main()
