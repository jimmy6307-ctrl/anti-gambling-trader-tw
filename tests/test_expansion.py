"""新模組測試:市場擴充、倖存者偏差、假老師驗證、話術偵測、鑑識、風險模擬、HTML。

每個數學主張都對照解析解或已知值,防止未來改壞。
執行: python tests/test_expansion.py
"""

from __future__ import annotations

import math
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.analyzer import analyze_log  # noqa: E402
from core.antiscam.guru_claim import (  # noqa: E402
    analyze_guru_claim,
    binomial_tail_ge,
    years_to_own_the_world,
)
from core.antiscam.text_scanner import scan_text  # noqa: E402
from core.forensics import analyze_returns  # noqa: E402
from core.forensics.stat_tests import chi2_sf, runs_test, sharpe_with_ci  # noqa: E402
from core.ingest.costs import estimate_round_trip_cost  # noqa: E402
from core.markets import contract_multiplier, infer_market  # noqa: E402
from core.models import Market, Side, Trade, TradeLog  # noqa: E402
from core.montecarlo import (  # noqa: E402
    gambler_ruin_probability,
    losing_streak_probability,
    simulate_ruin_scenario,
)
from core.report_html import render_html_report, render_share_card  # noqa: E402
from core.survivorship import (  # noqa: E402
    guru_illusion,
    prob_perfect_run,
    prob_streak_in_trials,
)


def _t(pnl, i, tag=None):
    d = datetime(2024, 1, 1) + timedelta(days=i)
    return Trade("X", Market.US_STOCK, Side.LONG, d, d + timedelta(days=1),
                 100, 100, 10, fees=0, pnl=pnl, tag=tag)


# ══════ S4: 市場與契約乘數 ══════
def test_forex_not_misclassified_as_crypto():
    """回歸測試:舊版因『以 USD 結尾』把外匯誤判為加密貨幣。"""
    assert infer_market("EURUSD") == Market.FOREX
    assert infer_market("GBPUSD") == Market.FOREX
    assert infer_market("AUDUSD") == Market.FOREX
    assert infer_market("BTCUSDT") == Market.CRYPTO


def test_market_classification():
    assert infer_market("2330") == Market.TW_STOCK
    assert infer_market("0050") == Market.TW_ETF
    assert infer_market("TXF") == Market.TW_FUTURES
    assert infer_market("TXO") == Market.TW_OPTIONS
    assert infer_market("AAPL") == Market.US_STOCK
    assert infer_market("ZZZZZZ") == Market.UNKNOWN   # 模稜兩可 → 不猜


def test_contract_multiplier_whitelist():
    assert contract_multiplier("TXF202607") == (200.0, True)
    assert contract_multiplier("MXF") == (50.0, True)
    # 查不到就是查不到,不猜
    assert contract_multiplier("2330") == (1.0, False)


def test_futures_pnl_uses_multiplier():
    """台指期漲 100 點 × 1 口 = 20,000 元(不是 100 元)。"""
    d = datetime(2025, 1, 2)
    t = Trade("TXF", Market.TW_FUTURES, Side.LONG, d, d, 23000, 23100, 1,
              fees=0, contract_multiplier=200.0)
    assert t.pnl == 20000


def test_stock_backward_compatible():
    """乘數預設 1.0,股票結果與舊版逐位相同。"""
    d = datetime(2025, 1, 2)
    t = Trade("2330", Market.TW_STOCK, Side.LONG, d, d, 1000, 1080, 1000, fees=100)
    assert t.pnl == 79900
    assert t.contract_multiplier == 1.0


def test_futures_cost_both_sides_tax():
    """期交稅買賣雙邊都收,且課契約價值。"""
    c = estimate_round_trip_cost(Market.TW_FUTURES, Side.LONG, 23000, 23100, 1,
                                 contract_multiplier=200.0)
    # 手續費 20×2 + 稅 0.00002×契約價值×2 + 滑價
    assert 500 < c < 900   # 實務上台指期一口來回約 500~800 元


# ══════ A2: 倖存者偏差(解析解)══════
def test_streak_dp_matches_closed_form():
    """T = N 時,連勝機率精確等於 p^N。"""
    for n in (3, 5, 10):
        assert abs(prob_streak_in_trials(n, n, 0.5) - 0.5 ** n) < 1e-12


def test_streak_dp_matches_monte_carlo():
    def mc(T, N, p, trials=40000, seed=1):
        rng = random.Random(seed)
        hit = 0
        for _ in range(trials):
            run = 0
            for _ in range(T):
                if rng.random() < p:
                    run += 1
                    if run >= N:
                        hit += 1
                        break
                else:
                    run = 0
        return hit / trials

    for T, N, p in [(20, 5, 0.5), (30, 4, 0.6)]:
        assert abs(prob_streak_in_trials(T, N, p) - mc(T, N, p)) < 0.01


def test_guru_illusion_is_probabilistic_not_certain():
    """絕不能用『必然存在』的語氣 —— 實際機率不是 1。"""
    g = guru_illusion(n_traders=1000, n_trials=10, streak=10)
    assert 0.6 < g.prob_at_least_one < 0.65     # 約 0.6236
    assert g.prob_at_least_one < 1.0
    assert "一定" not in g.headline and "必然" not in g.headline


def test_perfect_run_probability():
    assert abs(prob_perfect_run(10, 0.5) - 1 / 1024) < 1e-12


# ══════ A4: 假老師驗證器 ══════
def test_binomial_tail_matches_hand_calc():
    exact = (math.comb(10, 8) + math.comb(10, 9) + math.comb(10, 10)) / 1024
    assert abs(binomial_tail_ge(10, 8, 0.5) - exact) < 1e-12
    assert binomial_tail_ge(10, 0, 0.5) == 1.0
    assert binomial_tail_ge(10, 11, 0.5) == 0.0


def test_compounding_reductio():
    y = years_to_own_the_world(0.20)
    assert y is not None and 10 < y < 13
    assert years_to_own_the_world(-0.05) is None    # 負報酬不發散


def test_guru_claim_detects_contradiction():
    """宣稱勝率 60% + 盈虧比 0.5 → 期望值為負,自相矛盾。"""
    a = analyze_guru_claim(claimed_win_rate=0.6, payoff_ratio=0.5)
    assert a.verdict == "宣稱自相矛盾"


def test_guru_claim_refuses_without_sample_size():
    """只說勝率不說筆數 → 誠實說「無法檢驗」,不編數字。"""
    a = analyze_guru_claim(claimed_win_rate=0.9)
    assert a.verdict == "資訊不足,無法檢驗"
    assert a.luck_prob_win_rate is None


# ══════ A3: 話術偵測(誤報率是關鍵)══════
def test_scanner_catches_scams():
    scams = [
        "老師帶單超準!加入VIP群保證獲利,名額有限,私訊我加客服",
        "你的獲利要出金需先繳稅,請先匯款到平台帳戶刷流水解凍",
    ]
    for s in scams:
        assert scan_text(s).risk_level in ("高", "極高")


def test_scanner_no_false_positive_on_normal_discussion():
    normals = [
        "我覺得台積電基本面不錯,但現在本益比偏高,想等回檔再進場",
        "定期定額買 0050 是不錯的長期策略,不用擇時",
        "最近大盤震盪,我把部位降到五成,設好停損",
    ]
    for s in normals:
        assert scan_text(s).risk_level not in ("高", "極高"), s


def test_scanner_does_not_flag_anti_scam_education():
    """反詐教育文含關鍵字但在否定語境,不可誤判(雙向否定視窗)。"""
    edus = [
        "任何說保證獲利的都是騙人的,千萬不要相信",
        "老師帶單、升級VIP,這些都是詐騙的典型手法,請小心",
        "提醒大家:出金要繳稅的說法 100% 是詐騙,請撥 165",
    ]
    for s in edus:
        assert scan_text(s).risk_level not in ("高", "極高"), s


def test_scanner_resists_self_denial_evasion():
    """詐騙犯自稱『我們不是詐騙』不該讓風險降級,反而是警訊。"""
    r = scan_text("我們絕不是詐騙!保證獲利穩賺不賠,快加客服升級VIP")
    assert r.risk_level in ("高", "極高")
    assert any(h.category == "self_denial" for h in r.hits)


# ══════ A1: 鑑識 ══════
def test_chi2_sf_matches_table():
    for x, df, exp in [(3.841, 1, 0.05), (16.919, 9, 0.05), (21.666, 9, 0.01)]:
        assert abs(chi2_sf(x, df) - exp) < 0.001


def test_runs_test_type_i_error_calibrated():
    hits = 0
    N = 800
    for s in range(N):
        rng = random.Random(s)
        r = runs_test([rng.gauss(0, 1) for _ in range(40)])
        if r and r.p_two_sided < 0.05:
            hits += 1
    assert 0.02 < hits / N < 0.08


def test_sharpe_lo_standard_error():
    rng = random.Random(3)
    rets = [rng.gauss(0.02, 0.03) for _ in range(36)]
    s = sharpe_with_ci(rets, periods_per_year=12)
    m = sum(rets) / 36
    var = sum((x - m) ** 2 for x in rets) / 35
    sr = m / math.sqrt(var)
    se = math.sqrt((1 + 0.5 * sr * sr) / 36) * math.sqrt(12)
    assert abs(s.std_error - se) < 1e-9


def test_forensics_catches_madoff_like_returns():
    rng = random.Random(7)
    smooth = [abs(rng.gauss(0.0095, 0.002)) for _ in range(60)]
    f = analyze_returns(smooth)
    assert f.suspicion_level in ("高度可疑", "可疑")
    assert any(x.code == "almost_never_loses" for x in f.findings)


def test_forensics_does_not_flag_legit_strategy():
    rng = random.Random(11)
    legit = [rng.gauss(0.008, 0.04) for _ in range(48)]
    f = analyze_returns(legit)
    assert f.suspicion_level in ("未發現明顯疑點", "略有疑點")


def test_forensics_never_convicts():
    """每個 finding 都必須說明「這不代表什麼」—— 絕不自動定罪造假。"""
    rng = random.Random(7)
    f = analyze_returns([abs(rng.gauss(0.0095, 0.002)) for _ in range(60)])
    for x in f.findings:
        assert x.does_not_mean, f"{x.code} 缺少『不代表什麼』的誠實揭露"
        assert "造假" not in x.what   # what 只描述觀察,不定罪


# ══════ S1: 風險模擬 ══════
def test_gambler_ruin_closed_form():
    assert abs(gambler_ruin_probability(5, 10, 0.5) - 0.5) < 1e-12
    assert abs(gambler_ruin_probability(3, 10, 0.5) - 0.7) < 1e-12
    # p != 0.5 對照解析式
    r = (1 - 0.45) / 0.45
    exp = (r ** 5 - r ** 10) / (1 - r ** 10)
    assert abs(gambler_ruin_probability(5, 10, 0.45) - exp) < 1e-12


def test_gambler_ruin_matches_simulation():
    def mc(a, N, p, paths=20000, seed=1):
        rng = random.Random(seed)
        ruin = 0
        for _ in range(paths):
            x = a
            while 0 < x < N:
                x += 1 if rng.random() < p else -1
            if x <= 0:
                ruin += 1
        return ruin / paths
    assert abs(gambler_ruin_probability(5, 10, 0.45) - mc(5, 10, 0.45)) < 0.02


def test_drawdown_never_exceeds_100pct():
    """爆倉是吸收狀態 —— 不可能出現 181% 的回撤(回歸測試)。"""
    rng = random.Random(2)
    s = simulate_ruin_scenario([rng.gauss(-20, 100) for _ in range(40)],
                               start_equity=10000, n_paths=800)
    assert s is not None
    assert s.p95_max_drawdown <= 1.0
    assert s.median_max_drawdown <= 1.0


def test_ruin_sim_discriminates():
    rng = random.Random(2)
    bad = simulate_ruin_scenario([rng.gauss(-20, 100) for _ in range(40)],
                                 start_equity=10000, n_paths=800)
    good = simulate_ruin_scenario([rng.gauss(30, 80) for _ in range(40)],
                                  start_equity=10000, n_paths=800)
    assert bad.ruin_fraction > good.ruin_fraction


def test_ruin_sim_warns_about_tail_underestimation():
    rng = random.Random(2)
    s = simulate_ruin_scenario([rng.gauss(10, 50) for _ in range(30)], n_paths=400)
    assert any("尾端低估" in w for w in s.warnings)


def test_ruin_sim_refuses_small_sample():
    assert simulate_ruin_scenario([1.0] * 5) is None


def test_losing_streak_probability():
    # 勝率越低,連虧越容易
    assert (losing_streak_probability(200, 10, 0.4)
            > losing_streak_probability(200, 10, 0.7))


# ══════ S2: HTML 報告 ══════
def _sample_result():
    trades = [_t(-50, i, "壞招") for i in range(20)]
    trades += [_t(30, i + 30, "好招") for i in range(20)]
    return analyze_log(TradeLog(trades), n_bootstrap=300)


def test_html_report_escapes_xss():
    trades = [_t(-50, i, '</script><img src=x onerror=alert(1)>') for i in range(20)]
    trades += [_t(30, i + 30, "正常") for i in range(20)]
    html = render_html_report(analyze_log(TradeLog(trades), n_bootstrap=300))
    assert "<img src=x onerror=alert(1)>" not in html
    assert "&lt;img" in html


def test_html_report_no_future_projection():
    html = render_html_report(_sample_result())
    for banned in ("你將會有", "預期未來", "預測未來報酬"):
        assert banned not in html


def test_share_card_renders():
    card = render_share_card(_sample_result())
    assert "不構成投資建議" in card
    assert len(card) > 500


if __name__ == "__main__":
    import traceback

    _this = sys.modules[__name__]
    fns = [
        v for k, v in sorted(globals().items())
        if k.startswith("test_") and callable(v)
        and getattr(v, "__module__", None) == _this.__name__
    ]
    passed = failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  PASS  {fn.__name__}")
            passed += 1
        except Exception:  # noqa: BLE001
            print(f"  FAIL  {fn.__name__}")
            traceback.print_exc()
            failed += 1
    print(f"\n{passed} passed, {failed} failed")
    sys.exit(1 if failed else 0)
