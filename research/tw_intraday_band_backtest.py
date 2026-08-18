#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
台股「強勢產業 + RVOL + 09:30 漲幅區間」分 K 回測。

比較：
  A +0.5%~+3%
  B +1%~+4%
  C +2%~+7%

資料：voidful/tw_stocker 公開 5 分 K CSV。
期間預設：2025-04-01 ~ 2026-04-01。

訊號：
- 09:30 價格相對前一交易日收盤漲幅。
- 當日 09:30 產業平均漲幅排名前 3。
- 同產業至少 2 檔上漲。
- 前 30 分鐘 RVOL > 1.5，分母為過去 20 個交易日同時段平均量。
- 09:30 bar close 進場，另計 0.05%/邊滑價成本。

出場：
- fixed：持有 1/3/5 個交易日，於該日最後一根 5m bar 收盤出場。
- stop3_take6：-3% 停損 / +6% 停利，最長持有 1/3/5 個交易日；同根 K 同碰停損停利採保守假設停損先。

成本：
- 買手續費 0.1425%
- 賣手續費 0.1425%
- 證交稅 0.3%
- 買/賣滑價各 0.05%
合計 round-trip 0.685%。
"""
from __future__ import annotations

import argparse
import io
import math
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

RAW = "https://raw.githubusercontent.com/voidful/tw_stocker/main/data/{stock_id}.csv"

DEFAULT_UNIVERSE = [
    ("2330", "半導體業"), ("2408", "半導體業"), ("3034", "半導體業"), ("6488", "半導體業"),
    ("3231", "電腦及週邊設備業"), ("2357", "電腦及週邊設備業"),
    ("3017", "電腦及週邊設備業"), ("6669", "電腦及週邊設備業"),
    ("2317", "其他電子業"), ("3665", "其他電子業"),
    ("2881", "金融保險業"), ("2882", "金融保險業"), ("2883", "金融保險業"),
    ("2884", "金融保險業"), ("2891", "金融保險業"),
    ("2603", "航運業"), ("2615", "航運業"), ("2609", "航運業"), ("2618", "航運業"),
    ("2412", "通信網路業"), ("3045", "通信網路業"), ("4904", "通信網路業"),
    ("1513", "電機機械"), ("1519", "電機機械"), ("2049", "電機機械"), ("1504", "電機機械"),
]

BANDS = {
    "0.5-3%": (0.005, 0.03),
    "1-4%": (0.01, 0.04),
    "2-7%": (0.02, 0.07),
}


def download_one(stock_id: str, cache_dir: Path, timeout: int = 90) -> pd.DataFrame:
    cache_dir.mkdir(parents=True, exist_ok=True)
    fp = cache_dir / f"{stock_id}.csv"
    if fp.exists() and fp.stat().st_size > 100:
        raw = fp.read_bytes()
    else:
        url = RAW.format(stock_id=stock_id)
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "tw-band-backtest/2.0"})
        r.raise_for_status()
        raw = r.content
        fp.write_bytes(raw)
        time.sleep(0.08)

    df = pd.read_csv(io.BytesIO(raw))
    if "Datetime" not in df.columns:
        raise ValueError(f"{stock_id}: 找不到 Datetime 欄")

    # 原始 repo 不同歷史區段可能出現 +08:00 與 +00:00；先轉 UTC 再統一台北時間。
    dt = pd.to_datetime(df["Datetime"], errors="coerce", utc=True)
    df["Datetime"] = dt.dt.tz_convert("Asia/Taipei")
    df = df.dropna(subset=["Datetime"]).sort_values("Datetime")
    # repo 偶爾有重複時間戳；保留最後一筆，避免同一根 K 重複算量。
    df = df.drop_duplicates(subset=["Datetime"], keep="last")

    for c in ["Open", "High", "Low", "Close", "Volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["Open", "High", "Low", "Close"])
    df["Volume"] = df["Volume"].fillna(0.0)
    df["stock_id"] = stock_id
    return df


def prepare_sessions(df: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> tuple[pd.DataFrame, pd.DataFrame]:
    warmup_start = start - pd.Timedelta(days=50)
    extra_end = end + pd.Timedelta(days=12)
    df = df[(df["Datetime"] >= warmup_start) & (df["Datetime"] <= extra_end)].copy()
    if df.empty:
        return pd.DataFrame(), pd.DataFrame()

    df["date"] = df["Datetime"].dt.normalize()
    df["time"] = df["Datetime"].dt.strftime("%H:%M")

    sessions = []
    for d, g in df.groupby("date", sort=True):
        g = g.sort_values("Datetime")
        # 只把台股正常盤資料納入，避免來源若混入盤外異常時段。
        rg = g[(g["time"] >= "09:00") & (g["time"] <= "13:30")]
        if rg.empty:
            continue
        row930 = rg[rg["time"] == "09:30"]
        if row930.empty:
            continue
        pre = rg[(rg["time"] >= "09:00") & (rg["time"] <= "09:30")]
        last = rg.iloc[-1]
        sessions.append({
            "date": pd.Timestamp(d),
            "stock_id": g["stock_id"].iloc[0],
            "p930": float(row930.iloc[-1]["Close"]),
            "v930cum": float(pre["Volume"].sum()),
            "close": float(last["Close"]),
        })

    s = pd.DataFrame(sessions).sort_values("date")
    if s.empty:
        return s, df

    s["prev_close"] = s["close"].shift(1)
    s["ret930"] = s["p930"] / s["prev_close"] - 1.0
    s["avg20_v930"] = s["v930cum"].rolling(20, min_periods=15).mean().shift(1)
    s["rvol"] = s["v930cum"] / s["avg20_v930"]
    s = s[(s["date"] >= start.normalize()) & (s["date"] <= end.normalize())].copy()
    return s, df


def _trading_dates(stock_bars: pd.DataFrame, entry_date: pd.Timestamp) -> list[pd.Timestamp]:
    vals = pd.Series(stock_bars["date"].dropna().unique()).sort_values().tolist()
    dates = [pd.Timestamp(x) for x in vals]
    ed = entry_date.normalize()
    return [x for x in dates if x >= ed]


def fixed_exit_return(stock_bars: pd.DataFrame, entry_date: pd.Timestamp, entry: float, n: int) -> float | None:
    dates = _trading_dates(stock_bars, entry_date)
    if len(dates) <= n:
        return None
    exit_date = dates[n]
    g = stock_bars[stock_bars["date"] == exit_date].sort_values("Datetime")
    g = g[(g["time"] >= "09:00") & (g["time"] <= "13:30")]
    if g.empty:
        return None
    exit_px = float(g.iloc[-1]["Close"])
    return exit_px / entry - 1.0


def bracket_return(
    stock_bars: pd.DataFrame,
    entry_dt: pd.Timestamp,
    entry: float,
    n: int,
    stop: float = -0.03,
    take: float = 0.06,
) -> float | None:
    stop_px = entry * (1.0 + stop)
    take_px = entry * (1.0 + take)

    bars = stock_bars[stock_bars["Datetime"] > entry_dt].copy()
    bars = bars[(bars["time"] >= "09:00") & (bars["time"] <= "13:30")]
    if bars.empty:
        return None

    dates = _trading_dates(stock_bars, entry_dt.normalize())
    if len(dates) <= n:
        return None
    end_date = dates[n]
    bars = bars[bars["date"] <= end_date]

    for _, r in bars.sort_values("Datetime").iterrows():
        hit_stop = float(r["Low"]) <= stop_px
        hit_take = float(r["High"]) >= take_px
        # 同一根 K 同時碰兩邊無法知道先後，採保守假設停損先成交。
        if hit_stop:
            return stop
        if hit_take:
            return take

    last_day = bars[bars["date"] == end_date].sort_values("Datetime")
    if last_day.empty:
        return None
    exit_px = float(last_day.iloc[-1]["Close"])
    return exit_px / entry - 1.0


def profit_factor(rets: pd.Series) -> float:
    pos = float(rets[rets > 0].sum())
    neg = float(-rets[rets < 0].sum())
    if neg <= 0:
        return float("inf") if pos > 0 else float("nan")
    return pos / neg


def max_drawdown(rets: pd.Series) -> float:
    eq = (1.0 + rets.fillna(0.0)).cumprod()
    if eq.empty:
        return float("nan")
    peak = eq.cummax()
    return float((eq / peak - 1.0).min())


def summarize(trades: pd.DataFrame, cost: float) -> pd.DataFrame:
    rows = []
    for (band, mode, hold), g in trades.groupby(["band", "mode", "hold_days"], sort=False):
        net = g["gross_return"].dropna() - cost
        if net.empty:
            continue
        rows.append({
            "band": band,
            "mode": mode,
            "hold_days": int(hold),
            "trades": int(len(net)),
            "win_rate": float((net > 0).mean()),
            "avg_net": float(net.mean()),
            "median_net": float(net.median()),
            "profit_factor": float(profit_factor(net)),
            "max_drawdown": float(max_drawdown(net)),
            "p10": float(net.quantile(0.10)),
            "p90": float(net.quantile(0.90)),
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out = out.sort_values(["mode", "hold_days", "avg_net"], ascending=[True, True, False])
    return out


def write_report(summary: pd.DataFrame, coverage: pd.DataFrame, cost: float, out: Path) -> None:
    lines = [
        "# 台股 09:30 三區間回測結果",
        "",
        "期間：2025-04-01 ~ 2026-04-01（含 50 日暖身，只在正式期間產生訊號）",
        "",
        f"Round-trip 成本：{cost*100:.3f}%（手續費 + 證交稅 + 雙邊滑價）",
        "",
        "## 資料覆蓋",
        "",
    ]
    for _, r in coverage.iterrows():
        lines.append(f"- {r['stock_id']} {r['industry']}：{r['sessions']} 個可用交易日")

    lines += ["", "## 結果", ""]
    if summary.empty:
        lines.append("沒有符合條件的交易。")
    else:
        show = summary.copy()
        for c in ["win_rate", "avg_net", "median_net", "max_drawdown", "p10", "p90"]:
            show[c] = show[c].map(lambda x: f"{x*100:.2f}%")
        show["profit_factor"] = show["profit_factor"].map(lambda x: "∞" if math.isinf(x) else f"{x:.2f}")
        lines.append(show.to_markdown(index=False))
        best = summary.sort_values(["avg_net", "profit_factor"], ascending=False).iloc[0]
        lines += [
            "",
            "## 單看平均淨報酬最佳組合",
            "",
            f"**{best['band']} / {best['mode']} / {int(best['hold_days'])} 日**："
            f"交易 {int(best['trades'])} 筆、勝率 {best['win_rate']*100:.1f}%、"
            f"平均淨報酬 {best['avg_net']*100:.2f}%、PF {best['profit_factor']:.2f}。",
            "",
            "> 注意：這是有限 26 檔代表股、6 個產業的研究，不代表全市場；資料來源也不是交易所逐筆成交資料。",
        ]
    (out / "report.md").write_text("\n".join(lines), encoding="utf-8")


def make_plot(summary: pd.DataFrame, out: Path) -> None:
    if summary.empty:
        return
    import matplotlib.pyplot as plt

    # 最直觀：固定持有 3 日三區間比較。
    p = summary[(summary["mode"] == "fixed") & (summary["hold_days"] == 3)].copy()
    if p.empty:
        return
    order = ["0.5-3%", "1-4%", "2-7%"]
    p["band"] = pd.Categorical(p["band"], categories=order, ordered=True)
    p = p.sort_values("band")

    fig = plt.figure(figsize=(8, 5))
    plt.bar(p["band"].astype(str), p["avg_net"] * 100)
    plt.axhline(0, linewidth=1)
    plt.title("Fixed 3-day: Average Net Return by 09:30 Band")
    plt.xlabel("09:30 gain band")
    plt.ylabel("Average net return (%)")
    plt.tight_layout()
    fig.savefig(out / "comparison_fixed_3d.png", dpi=160)
    plt.close(fig)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2025-04-01")
    ap.add_argument("--end", default="2026-04-01")
    ap.add_argument("--cache-dir", default="data/intraday_5m_cache")
    ap.add_argument("--out-dir", default="research_output/tw_intraday_bands")
    ap.add_argument("--rvol", type=float, default=1.5)
    ap.add_argument("--top-sectors", type=int, default=3)
    ap.add_argument("--min-breadth", type=int, default=2)
    ap.add_argument("--fee", type=float, default=0.001425)
    ap.add_argument("--tax", type=float, default=0.003)
    ap.add_argument("--slippage-one-side", type=float, default=0.0005)
    args = ap.parse_args()

    start = pd.Timestamp(args.start, tz="Asia/Taipei")
    end = pd.Timestamp(args.end, tz="Asia/Taipei")
    cache = Path(args.cache_dir)
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    session_parts = []
    bars_by_stock: dict[str, pd.DataFrame] = {}
    coverage_rows = []

    print(f"讀取 {len(DEFAULT_UNIVERSE)} 檔 5 分 K，期間 {args.start} ~ {args.end}")
    for i, (sid, industry) in enumerate(DEFAULT_UNIVERSE, 1):
        print(f"[{i:02d}/{len(DEFAULT_UNIVERSE)}] {sid} {industry}")
        try:
            bars = download_one(sid, cache)
            s, clipped = prepare_sessions(bars, start, end)
        except Exception as e:
            print(f"  [SKIP] {sid}: {type(e).__name__}: {e}")
            coverage_rows.append({"stock_id": sid, "industry": industry, "sessions": 0, "status": f"skip: {e}"})
            continue
        if s.empty:
            print("  [SKIP] 正式期間無足夠資料")
            coverage_rows.append({"stock_id": sid, "industry": industry, "sessions": 0, "status": "empty"})
            continue
        s["industry"] = industry
        clipped["industry"] = industry
        session_parts.append(s)
        bars_by_stock[sid] = clipped
        coverage_rows.append({"stock_id": sid, "industry": industry, "sessions": len(s), "status": "ok"})
        print(f"  sessions={len(s)}")

    coverage = pd.DataFrame(coverage_rows)
    coverage.to_csv(out / "coverage.csv", index=False, encoding="utf-8-sig")

    if not session_parts:
        raise SystemExit("沒有任何可用股票資料")

    sess = pd.concat(session_parts, ignore_index=True)
    sess = sess.dropna(subset=["ret930", "rvol", "p930"]).copy()

    industry_day = (
        sess.groupby(["date", "industry"])
        .agg(
            sector_ret=("ret930", "mean"),
            breadth_pos=("ret930", lambda x: int((x > 0).sum())),
            n_names=("stock_id", "nunique"),
        )
        .reset_index()
    )
    industry_day["sector_rank"] = industry_day.groupby("date")["sector_ret"].rank(ascending=False, method="first")

    sig = sess.merge(
        industry_day[["date", "industry", "sector_ret", "breadth_pos", "n_names", "sector_rank"]],
        on=["date", "industry"],
        how="left",
    )
    sig = sig[
        (sig["sector_rank"] <= args.top_sectors)
        & (sig["breadth_pos"] >= args.min_breadth)
        & (sig["rvol"] > args.rvol)
    ].copy()

    base_signals = sig.copy()
    base_signals.to_csv(out / "eligible_signals_before_band.csv", index=False, encoding="utf-8-sig")

    trades = []
    for band, (lo, hi) in BANDS.items():
        candidates = sig[(sig["ret930"] >= lo) & (sig["ret930"] <= hi)].copy()
        print(f"band {band}: {len(candidates)} candidates")
        for _, r in candidates.iterrows():
            sid = str(r["stock_id"])
            bars = bars_by_stock.get(sid)
            if bars is None or bars.empty:
                continue
            entry_date = pd.Timestamp(r["date"])
            day = bars[bars["date"] == entry_date]
            row930 = day[day["time"] == "09:30"].sort_values("Datetime")
            if row930.empty:
                continue
            entry_dt = row930.iloc[-1]["Datetime"]
            entry = float(r["p930"])

            base = {
                "band": band,
                "date": entry_date.date().isoformat(),
                "stock_id": sid,
                "industry": r["industry"],
                "ret930": float(r["ret930"]),
                "rvol": float(r["rvol"]),
                "sector_ret": float(r["sector_ret"]),
                "breadth_pos": int(r["breadth_pos"]),
                "sector_rank": int(r["sector_rank"]),
                "entry": entry,
            }
            for hold in (1, 3, 5):
                fr = fixed_exit_return(bars, entry_date, entry, hold)
                if fr is not None:
                    trades.append({**base, "mode": "fixed", "hold_days": hold, "gross_return": fr})
                br = bracket_return(bars, entry_dt, entry, hold, stop=-0.03, take=0.06)
                if br is not None:
                    trades.append({**base, "mode": "stop3_take6", "hold_days": hold, "gross_return": br})

    trades = pd.DataFrame(trades)
    round_trip_cost = args.fee * 2 + args.tax + args.slippage_one_side * 2

    if trades.empty:
        pd.DataFrame().to_csv(out / "trades.csv", index=False)
        pd.DataFrame().to_csv(out / "summary.csv", index=False)
        write_report(pd.DataFrame(), coverage, round_trip_cost, out)
        print("沒有符合條件的交易。")
        return

    trades["net_return"] = trades["gross_return"] - round_trip_cost
    summary = summarize(trades, round_trip_cost)
    trades.to_csv(out / "trades.csv", index=False, encoding="utf-8-sig")
    summary.to_csv(out / "summary.csv", index=False, encoding="utf-8-sig")
    write_report(summary, coverage, round_trip_cost, out)
    make_plot(summary, out)

    show = summary.copy()
    for c in ["win_rate", "avg_net", "median_net", "max_drawdown", "p10", "p90"]:
        show[c] = (show[c] * 100).map(lambda x: f"{x:.2f}%")
    show["profit_factor"] = show["profit_factor"].map(lambda x: "∞" if math.isinf(x) else f"{x:.2f}")
    print("\n=== 回測摘要（已扣成本）===")
    print(show.to_string(index=False))
    print(f"\nRound-trip cost = {round_trip_cost*100:.3f}%")
    print(f"輸出目錄：{out}")


if __name__ == "__main__":
    main()
