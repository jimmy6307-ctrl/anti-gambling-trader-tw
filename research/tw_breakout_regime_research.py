#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""第二階段：檢驗突破策略是否其實只在廣泛多頭市場有效。

規則在看本次結果前固定：
- 沿用 B20_SECTOR_LOWEXT：20日新高 + prev_close>MA20>MA60 + RVOL>1.5 + 產業前3 + breadth>=2 + 突破<=2%
- 市場環境只用代表股自身的前一日結構，不偷看當日未來：
  MKT60: 當日可用代表股中，至少 60% 的前收盤 > MA20
  MKT70: 至少 70% 的前收盤 > MA20
- IS 2024-03-01~2025-03-31 只能用來選；OOS 2025-04-01~2026-04-01 僅驗證。
- 成本與原研究相同 0.685%，持有 3/5/10 日。
- 只有 IS 平均>0、PF>1.2、交易>=30 才有資格進 OOS 驗證。
"""
from __future__ import annotations

import math
from pathlib import Path
import pandas as pd

import tw_breakout_oos_research as base

OUT = Path("research_output/tw_breakout_regime")


def pf(s: pd.Series) -> float:
    pos = float(s[s > 0].sum())
    neg = float(-s[s < 0].sum())
    return pos / neg if neg > 0 else (float("inf") if pos > 0 else math.nan)


def metrics(df: pd.DataFrame) -> dict:
    s = df["net"].dropna()
    return {
        "trades": int(len(s)),
        "win_rate": float((s > 0).mean()) if len(s) else math.nan,
        "avg_net": float(s.mean()) if len(s) else math.nan,
        "median_net": float(s.median()) if len(s) else math.nan,
        "pf": pf(s) if len(s) else math.nan,
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    parts, bars_map = [], {}
    for sid, ind in base.UNIVERSE:
        try:
            b = base.download(sid)
        except Exception as e:
            print(f"SKIP {sid}: {e}")
            continue
        bars_map[sid] = b
        parts.append(base.features(b, ind))

    f = pd.concat(parts, ignore_index=True)
    f = f.dropna(subset=["ret935", "rvol935", "ma20", "ma60", "high20"])

    sec = (f.groupby(["date", "industry"])
           .agg(sector_ret=("ret935", "mean"), breadth=("ret935", lambda s: int((s > 0).sum())))
           .reset_index())
    sec["sector_rank"] = sec.groupby("date")["sector_ret"].rank(ascending=False, method="first")
    f = f.merge(sec, on=["date", "industry"], how="left")

    # 市場廣度只用前一日收盤與前一日已知 MA20。
    f["above20"] = f["prev_close"] > f["ma20"]
    mkt = (f.groupby("date")
           .agg(mkt_breadth20=("above20", "mean"), n_market=("above20", "size"))
           .reset_index())
    f = f.merge(mkt, on="date", how="left")

    core = (
        f["trend"] & (f["rvol935"] > 1.5) & f["break20"] &
        (f["sector_rank"] <= 3) & (f["breadth"] >= 2) & (f["ext20"] <= .02)
    )
    masks = {
        "B20_SECTOR_LOWEXT_MKT60": core & (f["mkt_breadth20"] >= .60),
        "B20_SECTOR_LOWEXT_MKT70": core & (f["mkt_breadth20"] >= .70),
    }

    rows = []
    trades = []
    for rule, mask in masks.items():
        for _, r in f[mask].iterrows():
            sid = str(r["stock_id"])
            period = "IS" if base.IS_START.normalize() <= r["date"] <= base.IS_END.normalize() else (
                "OOS" if base.OOS_START.normalize() <= r["date"] <= base.OOS_END.normalize() else None)
            if period is None:
                continue
            for hold in (3, 5, 10):
                gross = base.fixed_return(bars_map[sid], r["date"], float(r["p935"]), hold)
                if gross is None:
                    continue
                trades.append({
                    "period": period, "rule": rule, "hold": hold,
                    "date": r["date"].date().isoformat(), "stock_id": sid,
                    "industry": r["industry"], "mkt_breadth20": r["mkt_breadth20"],
                    "gross": gross, "net": gross - base.COST,
                })

    t = pd.DataFrame(trades)
    t.to_csv(OUT / "trades.csv", index=False, encoding="utf-8-sig")
    for (period, rule, hold), g in t.groupby(["period", "rule", "hold"]):
        rows.append({"period": period, "rule": rule, "hold": hold, **metrics(g)})
    s = pd.DataFrame(rows)
    s.to_csv(OUT / "summary.csv", index=False, encoding="utf-8-sig")

    eligible = s[(s["period"] == "IS") & (s["trades"] >= 30) & (s["avg_net"] > 0) & (s["pf"] > 1.2)].copy()
    lines = ["# 突破策略 × 市場環境驗證", "", "先看 IS，只有正期望且 PF>1.2 才准看 OOS 作正式驗證。", ""]
    if eligible.empty:
        lines.append("**結果：沒有任何市場環境版本通過 IS 門檻，因此本輪直接淘汰，不用拿 OOS 的漂亮數字自我安慰。**")
    else:
        chosen = eligible.sort_values(["avg_net", "pf"], ascending=False).iloc[0]
        rule, hold = chosen["rule"], int(chosen["hold"])
        o = t[(t["period"] == "OOS") & (t["rule"] == rule) & (t["hold"] == hold)]
        om = metrics(o)
        contrib = o.groupby("stock_id")["net"].sum().sort_values(ascending=False)
        top = str(contrib.index[0]) if len(contrib) else ""
        dm = metrics(o[o["stock_id"] != top]) if top else om
        lines += [
            f"IS 選中：{rule} / {hold} 日；{int(chosen['trades'])} 筆，平均 {chosen['avg_net']*100:.2f}%，PF {chosen['pf']:.2f}。",
            f"OOS：{om['trades']} 筆，勝率 {om['win_rate']*100:.1f}%，平均 {om['avg_net']*100:.2f}%，中位數 {om['median_net']*100:.2f}%，PF {om['pf']:.2f}。",
            f"移除最大貢獻股票 {top}：{dm['trades']} 筆，平均 {dm['avg_net']*100:.2f}%，PF {dm['pf']:.2f}。",
        ]

    lines += ["", "## 全部摘要", "", s.to_markdown(index=False)]
    report = "\n".join(lines)
    (OUT / "report.md").write_text(report, encoding="utf-8")
    print(report)


if __name__ == "__main__":
    main()
