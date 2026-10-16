#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""凍結的 B20 族群突破策略：延遲成交 + 同期基準比較（診斷，不是新策略）。
規則沿用既有 B20_SECTOR_LOWEXT；訊號 09:35、實際假設 09:45 開盤成交。
預先固定：每交易日最多一檔，選 RVOL 最大者；持有 5 交易日。
控制組：同一天 09:45 買進同一有限股票池（等權）與同產業其他股票。
檢驗是否只是 2025-26 多頭帶動，並排除同根K線成交的樂觀偏誤。
"""
from __future__ import annotations

from pathlib import Path
import math
import numpy as np
import pandas as pd
import tw_breakout_oos_research as base

OUT = Path("research_output/tw_breakout_alpha_diagnostic")
HOLD = 5
ENTRY_BAR = "09:45"
BOOT_SEED = 20261008
N_BOOT = 3000
BLOCK = 5

def metric(s):
    s = pd.Series(s).dropna().astype(float)
    if s.empty:
        return dict(n=0, mean=float("nan"), median=float("nan"), pf=float("nan"), win=float("nan"))
    gain = float(s[s > 0].sum())
    loss = float(-s[s < 0].sum())
    return dict(n=int(len(s)), mean=float(s.mean()), median=float(s.median()),
                pf=gain/loss if loss else float("inf"), win=float((s > 0).mean()))

def block_ci(x):
    """Conservative exploratory moving-block bootstrap over ordered signal dates."""
    x = np.asarray(pd.Series(x).dropna(), dtype=float)
    n = len(x)
    if n < 10:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(BOOT_SEED)
    width = min(BLOCK, n)
    means = []
    for _ in range(N_BOOT):
        idx = []
        while len(idx) < n:
            st = int(rng.integers(0, n - width + 1))
            idx.extend(range(st, st + width))
        means.append(float(x[np.asarray(idx[:n])].mean()))
    return tuple(np.quantile(means, [.025, .975]).tolist())

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fs, ds = [], []
    for sid, industry in base.UNIVERSE:
        try:
            bars = base.download(sid)
        except Exception as e:
            print(f"SKIP {sid}: {e}")
            continue
        fs.append(base.features(bars, industry))
        daily = []
        for d, g in bars.groupby("date", sort=True):
            entry = g.loc[g["time"] == ENTRY_BAR, "Open"]
            if entry.empty or not np.isfinite(entry.iloc[0]) or entry.iloc[0] <= 0:
                continue
            daily.append({"date": d, "stock_id": sid, "industry": industry,
                          "entry945": float(entry.iloc[0]), "close": float(g.iloc[-1]["Close"])})
        ddf = pd.DataFrame(daily).sort_values("date")
        if len(ddf) < HOLD + 1:
            continue
        ddf["exit_close"] = ddf["close"].shift(-HOLD)
        ddf["gross"] = ddf["exit_close"] / ddf["entry945"] - 1
        ds.append(ddf[["date", "stock_id", "industry", "entry945", "gross"]])
    if not fs or not ds:
        raise RuntimeError("沒有足夠的 5 分K資料，拒絕輸出績效")
    f = pd.concat(fs, ignore_index=True)
    d = pd.concat(ds, ignore_index=True)
    f = f.dropna(subset=["ret935", "rvol935", "ma20", "ma60", "high20", "ext20"])
    sec = (f.groupby(["date", "industry"])
           .agg(sector_ret=("ret935", "mean"),
                breadth=("ret935", lambda x: int((x > 0).sum())))
           .reset_index())
    sec["sector_rank"] = sec.groupby("date")["sector_ret"].rank(ascending=False, method="first")
    f = f.merge(sec, on=["date", "industry"], how="left")
    # Pre-registered rule; this is NOT necessarily a first breakout (may be consecutive highs).
    sig = f[f["trend"] & f["break20"] & (f["rvol935"] > 1.5) &
            (f["sector_rank"] <= 3) & (f["breadth"] >= 2) &
            (f["ext20"] <= .02)].copy()
    sig = sig.sort_values(["date", "rvol935", "stock_id"],
                          ascending=[True, False, True]).drop_duplicates("date")
    sig = sig.merge(d[["date", "stock_id", "gross", "entry945"]],
                    on=["date", "stock_id"], how="inner")
    sig = sig[np.isfinite(sig["gross"])].copy()
    # Same-day, same-horizon matched control: avoid attributing broad market gains to signal.
    mkt = d.groupby("date")["gross"].agg(mkt_mean="mean", mkt_n="count").reset_index()
    peers = d.groupby(["date", "industry"])["gross"].agg(
        peer_sum="sum", peer_n="count").reset_index()
    sig = sig.merge(mkt, on="date", how="left").merge(peers, on=["date", "industry"], how="left")
    sig["sector_peer_mean"] = (sig["peer_sum"] - sig["gross"]) / (sig["peer_n"] - 1)
    sig.loc[sig["peer_n"] < 2, "sector_peer_mean"] = np.nan
    sig["net"] = sig["gross"] - base.COST
    sig["mkt_net"] = sig["mkt_mean"] - base.COST
    sig["sector_net"] = sig["sector_peer_mean"] - base.COST
    sig["excess_mkt"] = sig["net"] - sig["mkt_net"]
    sig["excess_sector"] = sig["net"] - sig["sector_net"]
    sig["period"] = np.where(
        (sig["date"] >= base.IS_START.normalize()) & (sig["date"] <= base.IS_END.normalize()), "IS",
        np.where((sig["date"] >= base.OOS_START.normalize()) &
                 (sig["date"] <= base.OOS_END.normalize()), "OOS", "OTHER"))
    sig = sig[sig["period"].isin(["IS", "OOS"])].copy()
    sig["month"] = sig["date"].dt.strftime("%Y-%m")
    sig.to_csv(OUT / "signals_and_controls.csv", index=False, encoding="utf-8-sig")
    summaries = []
    report = [
        "# B20 族群突破：同期市場基準與延遲成交檢查", "",
        "規則固定：09:35 觀察 B20_SECTOR_LOWEXT；09:45 開盤價進場；持有 5 個交易日。",
        "每天最多一檔，事前固定挑 RVOL 最大者。買賣成本合計 0.685%。",
        "基準：同一天、同樣持有 5 日的代表股等權組合，以及同產業其他股票。",
        "注意：只有約 25 檔代表股；不同股票交易日可能有缺漏，並非正式指數或完整全市場。", ""
    ]
    eligible = {}
    for period in ["IS", "OOS"]:
        x = sig[sig["period"] == period].sort_values("date")
        a = metric(x["net"]); m = metric(x["mkt_net"])
        e = metric(x["excess_mkt"]); s = metric(x["excess_sector"])
        ci = block_ci(x["excess_mkt"])
        by_stock = x.groupby("stock_id")["net"].sum().sort_values(ascending=False)
        top = str(by_stock.index[0]) if len(by_stock) else "NA"
        drop = x[x["stock_id"] != top]
        drop_m = metric(drop["net"])
        months = x.groupby("month")["excess_mkt"].mean()
        pos_month = float((months > 0).mean()) if len(months) else float("nan")
        summaries.append({"period": period, "n": a["n"], "mean_net": a["mean"],
                          "pf_net": a["pf"], "market_net": m["mean"],
                          "mean_excess_mkt": e["mean"], "mean_excess_sector": s["mean"],
                          "excess_ci_low": ci[0], "excess_ci_high": ci[1],
                          "drop_top": top, "drop_top_n": drop_m["n"],
                          "drop_top_mean_net": drop_m["mean"], "positive_month_ratio": pos_month})
        eligible[period] = a["n"] >= 40 and a["mean"] > 0 and a["pf"] > 1.2 and e["mean"] > 0
        report.extend([
            f"## {period}", "",
            f"訊號 {a['n']} 筆；策略平均淨報酬 {a['mean']:.3%}，PF {a['pf']:.2f}；同期等權組合 {m['mean']:.3%}。",
            f"相對同期等權組合平均超額 {e['mean']:.3%}；相對同產業其他股票平均超額 {s['mean']:.3%}。",
            f"日期順序 moving-block bootstrap (block={BLOCK}) 超額 95% 區間 [{ci[0]:.3%}, {ci[1]:.3%}]。",
            f"移除最大淨貢獻股票 {top}：{drop_m['n']} 筆，平均淨報酬 {drop_m['mean']:.3%}。",
            f"超額報酬為正的月份比例 {pos_month:.1%}。", ""
        ])
    summary = pd.DataFrame(summaries)
    summary.to_csv(OUT / "summary.csv", index=False, encoding="utf-8-sig")
    oos = summary[summary["period"] == "OOS"].iloc[0]
    confirmed = (eligible.get("IS", False) and eligible.get("OOS", False) and
                 oos["excess_ci_low"] > 0 and oos["drop_top_mean_net"] > 0 and
                 oos["positive_month_ratio"] >= .5)
    report.extend([
        "## 研究裁決", "",
        f"CONFIRMED={bool(confirmed)}",
        "這是既有規則的基準比較，不能把 OOS 結果反過來調整條件後仍稱為乾淨樣本外。",
        "訊號仍可能連續多天發生，未嚴格驗證『第一次』；未模擬資金占用與重疊持倉。",
        "訊號來自非交易所官方的公開 5 分K，未處理除權息/歷史成分股存活偏差；",
        "統計區間是探索性估計，不是獲利保證。"
    ])
    txt = "\n".join(report)
    (OUT / "report.md").write_text(txt, encoding="utf-8")
    print(txt)

if __name__ == "__main__":
    main()
