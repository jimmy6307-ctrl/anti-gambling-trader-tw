"""S3 trend 模組測試:分期彙總、權益曲線、滾動期望值、衰退偵測、誠實性保護。

執行: python tests/test_trend.py
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.models import Market, Side, Trade, TradeLog  # noqa: E402
from core.trend.timeline import (  # noqa: E402
    LOW_SAMPLE_TRADES,
    MIN_PER_HALF,
    TOO_FEW_TRADES,
    analyze_trend,
    bucket_by_period,
    detect_decay,
    equity_curve,
    render_trend_text,
    rolling_expectancy,
)
from core.verdict.statistics import welch_mean_test  # noqa: E402


def _t(pnl, year=2026, month=1, day=1, price=100.0, qty=1000.0):
    d = datetime(year, month, day)
    return Trade("2330", Market.TW_STOCK, Side.LONG, d, d, price,
                 price + pnl / qty, qty, pnl=pnl)


# ── 分期彙總 ────────────────────────────────────────────────
def test_bucket_groups_by_month():
    trades = [_t(10, month=1, day=i + 1) for i in range(3)]
    trades += [_t(20, month=2, day=i + 1) for i in range(4)]
    buckets = bucket_by_period(TradeLog(trades), granularity="month")
    assert [b.period_key for b in buckets] == ["2026-01", "2026-02"]
    assert buckets[0].n_trades == 3 and buckets[1].n_trades == 4
    # 依時間排序
    assert buckets[0].period_key < buckets[1].period_key


def test_bucket_quarter():
    trades = [_t(5, month=2), _t(5, month=5), _t(5, month=8)]
    buckets = bucket_by_period(TradeLog(trades), granularity="quarter")
    assert {b.period_key for b in buckets} == {"2026-Q1", "2026-Q2", "2026-Q3"}


def test_small_month_flagged_too_few():
    # 3 筆的月份 → too_few,不判讀
    buckets = bucket_by_period(TradeLog([_t(10, day=i + 1) for i in range(3)]))
    b = buckets[0]
    assert b.reliability == "too_few"
    assert b.too_few and b.low_sample
    assert "不對此期下任何結論" in b.note


def test_low_sample_flag_boundary():
    n = LOW_SAMPLE_TRADES - 1  # 29 筆 → low
    buckets = bucket_by_period(TradeLog([_t(10, day=(i % 27) + 1) for i in range(n)]))
    assert buckets[0].reliability == "low"
    n2 = LOW_SAMPLE_TRADES      # 30 筆 → ok
    buckets2 = bucket_by_period(TradeLog([_t(10, day=(i % 27) + 1) for i in range(n2)]))
    assert buckets2[0].reliability == "ok"


def test_too_few_hidden_in_text():
    # too_few 的期間文字報告不得印出勝率/期望值(只印 —)
    txt = render_trend_text(analyze_trend(TradeLog([_t(10, day=i + 1) for i in range(3)])))
    assert "資料不足,不判讀" in txt


# ── 權益曲線 ────────────────────────────────────────────────
def test_equity_curve_cumulative_and_drawdown():
    trades = [_t(10), _t(-5), _t(10)]
    eq = equity_curve(TradeLog(trades))
    assert [round(p.cum_pnl, 2) for p in eq] == [10.0, 5.0, 15.0]
    # 回撤:第二筆從高點 10 掉到 5 → dd=5;其餘為 0
    assert [round(p.drawdown, 2) for p in eq] == [0.0, 5.0, 0.0]


def test_equity_time_ordered():
    # 亂序輸入也要依 exit_time 排序累積
    trades = [_t(10, month=3), _t(20, month=1), _t(-5, month=2)]
    eq = equity_curve(TradeLog(trades))
    assert [round(p.cum_pnl, 2) for p in eq] == [20.0, 15.0, 25.0]


# ── 滾動期望值 ──────────────────────────────────────────────
def test_rolling_window():
    trades = [_t(v, day=(i % 27) + 1) for i, v in enumerate([10, 20, 30, 40])]
    pts = rolling_expectancy(TradeLog(trades), window=2)
    # 視窗 2:平均為 (10,20)->15, (20,30)->25, (30,40)->35
    assert [round(p.rolling_expectancy, 2) for p in pts] == [15.0, 25.0, 35.0]
    assert all(p.window == 2 for p in pts)


def test_rolling_insufficient_returns_empty():
    # 不足一個完整視窗 → 空,不硬湊殘缺視窗
    assert rolling_expectancy(TradeLog([_t(10), _t(20)]), window=5) == []


# ── 衰退偵測:誠實性核心 ────────────────────────────────────
def test_decay_insufficient_says_unknown():
    n = 2 * MIN_PER_HALF - 1
    d = detect_decay(TradeLog([_t(10, day=(i % 27) + 1) for i in range(n)]))
    assert not d.enough_data
    assert d.direction == "unknown"
    assert d.p_value is None
    assert "無法判斷" in d.headline


def test_decay_stable_edge_not_flagged():
    # 早晚期望值相同 → 不該報衰退
    trades = [_t(10 + (i % 3), day=(i % 27) + 1, month=(i // 27) + 1) for i in range(60)]
    d = detect_decay(TradeLog(trades))
    assert d.enough_data
    assert d.direction == "flat"
    assert not d.is_significant_change


def test_decay_uses_return_pct_not_pnl():
    # 關鍵誠實測試:期望值(報酬率)不變,但後期部位放大 10 倍。
    # 若用金額 pnl 會誤報「進步」;用 return_pct 應判 flat。
    early = [_t(10 + (i % 5 - 2), price=100, qty=1000,
               day=(i % 27) + 1, month=1) for i in range(20)]
    # 後期:同樣的報酬率結構,但部位×10(pnl 也×10)
    recent = [_t(100 + (i % 5 - 2) * 10, price=100, qty=10000,
                day=(i % 27) + 1, month=6) for i in range(20)]
    d = detect_decay(TradeLog(early + recent))
    # 金額期望值明顯不同(被部位放大),但報酬率相近
    assert d.recent_expectancy > d.early_expectancy * 5  # 金額被放大
    assert abs(d.recent_return_pct - d.early_return_pct) < 0.001  # 報酬率相近
    assert d.direction == "flat"  # 用報酬率檢定 → 不誤報進步


def test_decay_detects_real_decline():
    # 早期穩定賺、後期穩定賠 → 應顯著且方向 declining
    early = [_t(50 + (i % 3), day=(i % 27) + 1, month=1) for i in range(20)]
    recent = [_t(-50 + (i % 3), day=(i % 27) + 1, month=6) for i in range(20)]
    d = detect_decay(TradeLog(early + recent))
    assert d.enough_data and d.is_significant_change
    assert d.direction == "declining"


# ── Welch 兩樣本檢定 ────────────────────────────────────────
def test_welch_identical_not_significant():
    r = welch_mean_test([1, 2, 3, 4, 5], [1, 2, 3, 4, 5])
    assert r is not None and not r.is_significant
    assert abs(r.diff) < 1e-9


def test_welch_clear_difference():
    r = welch_mean_test([10, 11, 9, 10, 12, 8], [1, 2, 0, 1, 3, -1])
    assert r is not None and r.is_significant and r.diff > 0


def test_welch_too_small_returns_none():
    assert welch_mean_test([1], [1, 2, 3]) is None


# ── 端到端 as_dict / JSON 安全 ─────────────────────────────
def test_analyze_trend_as_dict_json_safe():
    import json
    trades = [_t(10 + (i % 7 - 3), day=(i % 27) + 1, month=(i // 27) + 1)
              for i in range(50)]
    rep = analyze_trend(TradeLog(trades))
    d = rep.as_dict()
    json.dumps(d, ensure_ascii=False)  # 不得拋例外
    assert "decay" in d and "buckets" in d and "equity" in d
    # 內部哨兵 / 物件不得外洩
    assert isinstance(d["decay"]["p_value"], (float, type(None)))


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    passed = 0
    for fn in fns:
        fn()
        passed += 1
        print(f"  ok  {fn.__name__}")
    print(f"\n{passed}/{len(fns)} 測試通過")


if __name__ == "__main__":
    _run_all()
