#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Frozen 2026-10-07 opening gap-overreaction hypothesis.

Rules fixed before inspecting results; do not optimize against OOS.
IS: 2024-03-01..2025-03-31; OOS: 2025-04-01..2026-04-01.
Use 5-minute OHLCV from voidful/tw_stocker, ~26 selected stocks.
Cost: 0.685% round trip. Entry at close of bar labelled 09:20
(note vendor bar-label ambiguity; real orders may be later).
"""
from __future__ import annotations
import math
from pathlib import Path
import pandas as pd
from tw_breakout_oos_research import UNIVERSE, download, COST

OUT = Path("research_output/tw_gap_overreaction")
OUT.mkdir(parents=True, exist_ok=True)
IS_START, IS_END = "2024-03-01", "2025-03-31"
OOS_START, OOS_END = "2025-04-01", "2026-04-01"
HOLDS = (0, 1, 3)
MIN_IS_TRADES = 30  # reliability gate, not a parameter to tune

def pf(net):
    pos = net[net > 0].sum()
    neg = -net[net < 0].sum()
    return float(pos / neg) if neg > 0 else (float("inf") if pos > 0 else math.nan)

def metrics(df):
    if df.empty:
        return dict(n=0, avg=math.nan, median=math.nan, pf=math.nan, win=math.nan)
    s = df["net"]
    return dict(n=len(s), avg=float(s.mean()), median=float(s.median()),
                pf=pf(s), win=float((s > 0).mean()))

def main():
    features, days = [], {}
    coverage = []
    for sid, industry in UNIVERSE:
        try:
            bars = download(sid)
            if bars.empty:
                raise ValueError("empty data")
            rows = []
            for date, g in bars.groupby("date", sort=True):
                g = g.sort_values("Datetime")
                b920 = g[g["time"] == "09:20"]
                if b920.empty:
                    continue
                early = g[g["time"] <= "09:20"]
                rows.append(dict(date=date, sid=sid, industry=industry,
                                 open=float(g.iloc[0]["Open"]),
                                 p920=float(b920.iloc[-1]["Close"]),
                                 low_early=float(early["Low"].min()),
                                 close=float(g.iloc[-1]["Close"])))
            d = pd.DataFrame(rows).sort_values("date")
            if d.empty:
                continue
            d["prev_close"] = d["close"].shift(1)
            d["gap"] = d["open"] / d["prev_close"] - 1
            d["ret920"] = d["p920"] / d["prev_close"] - 1
            d["reclaim"] = d["p920"] / d["low_early"] - 1
            features.append(d)
            days[sid] = d.reset_index(drop=True)
            coverage.append((sid, len(d)))
            print(f"{sid}: {len(d)} sessions", flush=True)
        except Exception as e:
            coverage.append((sid, 0))
            print(f"{sid}: ERROR {e}", flush=True)
    if not features:
        raise RuntimeError("No usable data; fail closed")
    f = pd.concat(features, ignore_index=True)
    f = f.dropna(subset=["prev_close", "gap", "ret920", "reclaim"])
    sector = (f.groupby(["date", "industry"])["ret920"]
              .agg(sector_ret="mean", sector_n="size").reset_index())
    f = f.merge(sector, on=["date", "industry"], how="left")
    # Frozen threshold. Sector average includes candidate stock, as in
    # 2026-10-07 hypothesis; do not silently change the definition.
    sig = f[(f["gap"] <= -.02) &
            (f["ret920"] <= -.01) &
            (f["reclaim"] >= .01) &
            (f["sector_ret"] > -.01) &
            ((f["sector_ret"] - f["ret920"]) >= .015)].copy()
    sig = sig.sort_values(["date", "sid"])
    sig.to_csv(OUT / "signals.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(coverage, columns=["sid", "sessions"]).to_csv(
        OUT / "coverage.csv", index=False, encoding="utf-8-sig")
    all_trades = []
    for hold in HOLDS:
        for sid, sub in sig.groupby("sid"):
            d = days[sid]
            positions = {dt: i for i, dt in enumerate(d["date"])}
            last_exit = -1
            for _, r in sub.iterrows():
                idx = positions.get(r["date"])
                if idx is None or idx <= last_exit:
                    continue  # no overlapping positions in same stock
                exit_idx = idx + hold
                if exit_idx >= len(d):
                    continue
                exit_day = d.iloc[exit_idx]
                entry_date = str(r["date"].date())
                if IS_START <= entry_date <= IS_END:
                    period = "IS"
                elif OOS_START <= entry_date <= OOS_END:
                    period = "OOS"
                else:
                    continue
                net = float(exit_day["close"] / r["p920"] - 1 - COST)
                all_trades.append(dict(period=period, hold=hold, sid=sid,
                                       industry=r["industry"], entry_date=entry_date,
                                       exit_date=str(exit_day["date"].date()),
                                       gap=r["gap"], ret920=r["ret920"],
                                       sector_ret=r["sector_ret"], reclaim=r["reclaim"],
                                       net=net))
                last_exit = exit_idx
    t = pd.DataFrame(all_trades)
    if t.empty:
        (OUT / "report.md").write_text("# Gap overreaction\n\nNo signals with complete exits. Rejected.\n", encoding="utf-8")
        return
    t.to_csv(OUT / "trades.csv", index=False, encoding="utf-8-sig")
    summaries = []
    for (period, hold), g in t.groupby(["period", "hold"]):
        summaries.append(dict(period=period, hold=hold, **metrics(g)))
    s = pd.DataFrame(summaries)
    s.to_csv(OUT / "summary.csv", index=False, encoding="utf-8-sig")
    is_pass = s[(s.period == "IS") & (s.n >= MIN_IS_TRADES) &
                (s.avg > 0) & (s.pf > 1.2)].copy()
    lines = [
        "# 2026-10-07 frozen gap-overreaction hypothesis: execution",
        "",
        "26-stock representative universe, not all Taiwan equities.",
        f"IS {IS_START}~{IS_END}; OOS {OOS_START}~{OOS_END}; round-trip cost {COST:.3%}.",
        "Signal at 09:20; sector mean includes candidate; per-stock no overlapping positions.",
        "IS pass requires >=30 trades, mean >0 and PF>1.2. OOS cannot rescue IS failure.",
        "",
        "## All hold horizons (for diagnostics, not post-hoc OOS selection)",
        "",
        s.to_markdown(index=False),
        "",
    ]
    if is_pass.empty:
        lines += ["## Verdict", "", "**REJECTED: no IS horizon met predeclared gate.**",
                  "Do not select a better-looking OOS horizon after seeing these results."]
    else:
        # Frozen selection: highest IS PF, then avg, without OOS inspection.
        chosen = is_pass.sort_values(["pf", "avg"], ascending=False).iloc[0]
        hold = int(chosen.hold)
        oos = t[(t.period == "OOS") & (t.hold == hold)]
        m = metrics(oos)
        contributions = oos.groupby("sid")["net"].sum().sort_values(ascending=False)
        top = str(contributions.index[0]) if len(contributions) else ""
        drop = metrics(oos[oos.sid != top]) if top else metrics(oos)
        monthly = (oos.assign(month=oos.entry_date.str[:7])
                   .groupby("month")["net"].agg(["count", "sum", "mean"]))
        monthly.to_csv(OUT / "oos_monthly.csv", encoding="utf-8-sig")
        active_months = len(monthly)
        positive_months = int((monthly["sum"] > 0).sum())
        top2 = float(monthly["sum"].nlargest(2).sum())
        total = float(monthly["sum"].sum())
        top2_share = top2 / total if total > 0 else math.inf
        passed = (m["n"] >= 30 and m["avg"] > 0 and m["pf"] > 1.2
                  and drop["avg"] > 0 and drop["pf"] > 1.1
                  and active_months >= 6 and positive_months >= 3
                  and top2_share < .8)
        lines += [
            "## Frozen IS selection and OOS verdict", "",
            f"Chosen hold={hold} trading days; IS: {metrics(t[(t.period == 'IS') & (t.hold == hold)])}.",
            f"OOS: {m}.",
            f"Remove largest OOS contributing stock {top}: {drop}.",
            f"Months active={active_months}, positive={positive_months}, top-two contribution share={top2_share:.1%}.",
            f"**{'PRELIMINARY PASS (still needs broader universe and execution validation)' if passed else 'REJECTED / UNCONFIRMED'}**",
        ]
    lines += [
        "", "## Limitations",
        "- Nonrandom 26-stock universe; possible selection and survivorship bias.",
        "- Bar timestamps may be start- or end-labelled; entry at exact bar close may be optimistic.",
        "- No order-book depth, price-limit execution, or market impact simulation.",
        "- Correlated trades and cross-stock simultaneous exposure not portfolio-accounted.",
        "- IS/OOS years have already been used for earlier strategy research, so OOS is not pristine for the overall research program.",
    ]
    (OUT / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines), flush=True)

if __name__ == "__main__":
    main()
