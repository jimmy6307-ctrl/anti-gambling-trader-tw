"""風險情境模擬的實作。"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from ..survivorship import prob_streak_in_trials


def gambler_ruin_probability(
    start: int, target: int, p_win: float
) -> float:
    """賭徒破產問題的**解析解**(用來驗證我們的模擬是否正確)。

    每一步 ±1,贏的機率 p,起始資本 a,在碰到 target 之前碰到 0 就破產。

        p ≠ 0.5:  r = q/p
                  P(破產) = (r^a − r^N) / (1 − r^N)
        p = 0.5:  P(破產) = 1 − a/N

    這是教科書結果(Feller)。我們用它當作模擬的正確性基準。
    """
    a, N = int(start), int(target)
    if a <= 0:
        return 1.0
    if a >= N:
        return 0.0
    if not (0.0 < p_win < 1.0):
        return 1.0 if p_win == 0.0 else 0.0
    if abs(p_win - 0.5) < 1e-12:
        return 1.0 - a / N
    r = (1.0 - p_win) / p_win
    return (r ** a - r ** N) / (1.0 - r ** N)


def losing_streak_probability(
    n_future_trades: int, streak: int, win_rate: float
) -> float:
    """以你的勝率,未來 N 筆交易裡出現「連續虧損 streak 次」的機率。

    用與倖存者偏差同一套精確 DP(把「贏」換成「輸」)。
    這是心理面最實用的數字:很多人不是被數學打敗,是被連虧打崩紀律。
    """
    loss_rate = 1.0 - win_rate
    return prob_streak_in_trials(n_future_trades, streak, loss_rate)


@dataclass
class RuinScenario:
    """未來情境的模擬結果。

    刻意命名為「情境」而非「預測」—— 這些數字回答的是
    「如果未來長得像過去,會怎樣」,而不是「未來會怎樣」。
    """

    n_future_trades: int
    n_paths: int
    start_equity: float
    ruin_threshold: float          # 權益跌破此值視為「爆掉」

    ruin_fraction: float           # 有多少比例的模擬路徑爆掉
    median_final_equity: float
    p05_final_equity: float
    p95_final_equity: float
    median_max_drawdown: float
    p95_max_drawdown: float
    median_trade_at_ruin: int | None   # 爆掉的路徑,中位數在第幾筆爆

    losing_streak_10_prob: float   # 未來出現連虧 10 次的機率

    warnings: list[str] = field(default_factory=list)
    # 起始權益是否為工具粗估(而非使用者提供)。爆倉比例對這個假設極度敏感:
    # 本金假設砍半,爆倉比例可能從 5% 跳到 90%。推估時必須醒目揭露。
    start_equity_inferred: bool = False

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        return d


def simulate_ruin_scenario(
    pnls: list[float],
    *,
    start_equity: float | None = None,
    ruin_drawdown: float = 0.5,
    n_future_trades: int = 200,
    n_paths: int = 5000,
    seed: int = 20260710,
) -> RuinScenario | None:
    """用你實際的損益分布,bootstrap 模擬未來 N 筆交易的情境。

    做法:從你的 pnls 有放回地重抽,一筆一筆累積權益,
    看有多少比例的路徑會跌破「起始權益 × (1 − ruin_drawdown)」。

    Args:
        start_equity:  起始權益。未給時用「單筆最大虧損 × 20」的粗估。
        ruin_drawdown: 跌破起始權益的多少比例算「爆掉」(預設 50%)。
        n_paths:       模擬幾條路徑。

    Returns:
        RuinScenario;樣本 < 10 筆時回傳 None(誠實地不編數字)。
    """
    # 參數驗證:越界的參數會產生無意義的模擬,直接拒絕並講清楚,
    # 而不是默默算出垃圾數字。
    if n_paths < 1 or n_future_trades < 1:
        raise ValueError("n_paths 與 n_future_trades 必須 >= 1")
    if not (0.0 <= ruin_drawdown <= 1.0):
        raise ValueError(f"ruin_drawdown 必須在 [0, 1],收到 {ruin_drawdown}")
    if start_equity is not None and start_equity <= 0:
        raise ValueError(f"start_equity 必須 > 0,收到 {start_equity}")

    n = len(pnls)
    if n < 10:
        return None

    equity_inferred = start_equity is None
    if start_equity is None:
        worst = abs(min(pnls)) if min(pnls) < 0 else abs(max(pnls))
        start_equity = max(worst * 20.0, 1.0)
    ruin_level = start_equity * (1.0 - ruin_drawdown)

    rng = random.Random(seed)
    ruined = 0
    finals: list[float] = []
    max_dds: list[float] = []
    ruin_steps: list[int] = []

    for _ in range(n_paths):
        equity = start_equity
        peak = equity
        max_dd = 0.0
        blew_up_at: int | None = None
        for step in range(1, n_future_trades + 1):
            equity += pnls[rng.randrange(n)]
            peak = max(peak, equity)
            dd = (peak - equity) / peak if peak > 0 else 1.0
            max_dd = min(1.0, max(max_dd, dd))   # 回撤不可能超過 100%
            if equity <= ruin_level:
                # 爆倉是**吸收狀態**:現實中你被強制平倉、資金耗盡,遊戲結束。
                # 若讓路徑繼續交易,權益會變成負數,算出「回撤 181%」這種荒謬數字。
                blew_up_at = step
                break
        if blew_up_at is not None:
            ruined += 1
            ruin_steps.append(blew_up_at)
        finals.append(equity)
        max_dds.append(max_dd)

    finals.sort()
    max_dds.sort()
    ruin_steps.sort()

    def q(sorted_vals: list[float], pct: float) -> float:
        if not sorted_vals:
            return 0.0
        idx = min(len(sorted_vals) - 1, max(0, int(pct * len(sorted_vals))))
        return sorted_vals[idx]

    # 連虧機率要用「真實的虧損率」:打平交易(pnl == 0)既不是贏也不是虧,
    # 用 1 − win_rate 會把打平算成虧損,高估連虧機率。
    losses = sum(1 for p in pnls if p < 0)
    streak10 = losing_streak_probability(n_future_trades, 10, 1.0 - losses / n)

    warnings = []
    if equity_inferred:
        # 放最前面:爆倉比例對本金假設極度敏感,推估的本金必須第一眼看到。
        warnings.append(
            f"⚠️ 起始權益 {start_equity:,.0f} 是工具用『單筆最大虧損 × 20』**粗估的假設本金**,"
            "不是你的真實帳戶。爆倉比例對這個假設極度敏感 —— 請用 --equity 提供"
            "真實權益重跑,結果可能天差地遠。"
        )
    warnings += [
        "這**不是預測**。它假設「未來每一筆交易的損益,都從你過去的損益裡隨機抽出」——"
        "而未來必然不會如此。市場會變。",
        f"⚠️ 尾端低估:重抽只能抽到你樣本裡**出現過**的損益。你只有 {n} 筆樣本,"
        "如果那段期間剛好沒發生過大虧(例如選擇權賣方沒遇到暴跌),"
        "模擬就永遠抽不到它 —— 真實的爆倉機率會遠比這裡高。",
        "各筆交易被假設為獨立同分布。真實交易有序列相關(連續加碼、情緒化報復性交易),"
        "會讓實際的連虧與回撤比模擬更嚴重。",
        f"這些數字只有 {n} 筆樣本支撐。樣本一變,結果可能天差地遠 —— "
        "請把它當作「量級的感覺」,不要當作精確的機率。",
    ]

    return RuinScenario(
        n_future_trades=n_future_trades,
        n_paths=n_paths,
        start_equity=start_equity,
        ruin_threshold=ruin_level,
        ruin_fraction=ruined / n_paths,
        median_final_equity=q(finals, 0.5),
        p05_final_equity=q(finals, 0.05),
        p95_final_equity=q(finals, 0.95),
        median_max_drawdown=q(max_dds, 0.5),
        p95_max_drawdown=q(max_dds, 0.95),
        median_trade_at_ruin=(ruin_steps[len(ruin_steps) // 2] if ruin_steps else None),
        losing_streak_10_prob=streak10,
        warnings=warnings,
        start_equity_inferred=equity_inferred,
    )


def render_scenario(s: RuinScenario) -> str:
    """輸出可讀報告。刻意用「情境」而非「預測」的措辭。"""
    L = ["=" * 66, "        風險情境模擬 — 如果未來長得像過去,會怎樣?", "=" * 66, ""]
    L.append(f"【設定】模擬未來 {s.n_future_trades} 筆交易,跑 {s.n_paths:,} 條路徑")
    inferred_tag = "(⚠️ 工具粗估,非真實帳戶)" if s.start_equity_inferred else ""
    L.append(f"       起始權益 {s.start_equity:,.0f}{inferred_tag},"
             f"跌破 {s.ruin_threshold:,.0f} 視為爆掉")
    L.append("")
    L.append("【情境結果】")

    # 爆倉比例:用「多少條路徑」而非「機率」措辭,並分級。
    # 格式化紀律:0.998 不可印成「100%」(讀起來像確定性,是說假話)。
    frac = s.ruin_fraction
    pct = f"{frac:.0%}" if 0.005 <= frac <= 0.995 else f"{frac:.1%}"
    if frac == 0:
        desc = "在這些情境裡,沒有一條路徑爆掉"
    elif frac < 0.01:
        desc = f"約每 100 條路徑不到 1 條爆掉({pct})"
    elif frac < 0.1:
        desc = f"約 {pct} 的路徑爆掉 —— 十次裡有一次以內"
    elif frac < 0.5:
        desc = f"⚠️ 約 {pct} 的路徑爆掉 —— 這是很高的比例"
    elif frac >= 1.0:
        desc = "🔴 全部的路徑都爆掉 —— 這套玩法在這些情境裡沒有活路"
    else:
        desc = f"🔴 超過一半({pct})的路徑爆掉 —— 這套玩法極可能毀掉你"
    L.append(f"  爆倉情境    : {desc}")
    if s.median_trade_at_ruin:
        L.append(f"  爆掉的路徑中,中位數在第 {s.median_trade_at_ruin} 筆交易時爆")

    L.append(f"  最終權益    : 中位數 {s.median_final_equity:,.0f}"
             f"(5%~95% 區間 {s.p05_final_equity:,.0f} ~ {s.p95_final_equity:,.0f})")
    L.append("            (爆掉的路徑在爆倉當下就停止 —— 現實中你會被強制平倉,")
    L.append("             不會用負的資金繼續交易)")
    L.append(f"  最大回撤    : 中位數 {s.median_max_drawdown:.0%},"
             f"最壞 5% 的情境達 {s.p95_max_drawdown:.0%}")
    L.append(f"  連虧 10 次  : 在未來 {s.n_future_trades} 筆裡出現的機率 "
             f"{s.losing_streak_10_prob:.1%}")
    L.append("            (以你目前的勝率計算。連虧不是「會不會」,是「什麼時候」——")
    L.append("             問題是那時候你還守得住紀律嗎?)")
    L.append("")
    L.append("【你必須知道的限制】")
    for w in s.warnings:
        L.append(f"  ⚠ {w}")
    L.append("")
    L.append("─" * 66)
    L.append("這是「情境」不是「預測」。我們不提供 Kelly 部位建議,也不給 VaR 數字 ——")
    L.append("在幾十筆樣本下,那些量抖動劇烈,給出來就是假精準。")
    return "\n".join(L)
