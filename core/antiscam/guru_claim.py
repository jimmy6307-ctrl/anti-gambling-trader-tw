"""假老師績效驗證器 — 把「老師的宣稱」丟進數學裡檢驗。

使用者常拿到這種宣稱:
    「我勝率 90%」「我連續 12 個月獲利」「月報酬 20%」

本模組回答:
    1. 在「老師毫無能力」的前提下,這種績效有多容易靠運氣出現?
    2. 要多少樣本,才能證明這不是運氣?
    3. 如果市面上有 N 個自稱老師的人,期望會有幾個人達成這種績效?
    4. 宣稱本身在數學上自相矛盾嗎?(如月報酬 20% 複利的歸謬)

⚠️ 誠實性紀律:
   - 所有機率都以「虛無假設」為前提,必須明講那個假設是什麼。
   - 虛無假設的勝率 p0 預設 0.5(純猜),但**大盤有正漂移**,
     單月上漲的基準機率其實約 0.55~0.62。p0 必須可調,並在輸出中揭露。
   - 我們不宣稱「他一定是騙子」,只說「這種績效在無能力假設下有多容易發生」。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from ..survivorship import (
    expected_number_with_streak,
    prob_perfect_run,
    prob_streak_in_trials,
)
from ..verdict.statistics import _reg_incomplete_beta, required_sample_size

#: 全球一年的 GDP 概略值(台幣),用於複利歸謬法的參考錨點
WORLD_GDP_TWD = 3.5e15


def binomial_tail_ge(n: int, k: int, p: float) -> float:
    """二項分布上尾機率 P(X >= k),X ~ Binomial(n, p)。純標準庫。

    用於檢驗「宣稱的勝率」:在毫無能力(每次贏的機率 = p)的前提下,
    n 次交易裡贏 k 次以上的機率有多大。

    實作用恆等式 P(X >= k) = I_p(k, n − k + 1)(正則化不完全 beta),
    複用 verdict/statistics 已驗證的 _reg_incomplete_beta。
    舊版逐項累加 math.comb(n, i) 在 n = 10000 時會 OverflowError
    (巨大整數無法轉 float)—— 老師宣稱「一萬筆交易勝率 90%」會讓工具直接崩潰。
    """
    if k <= 0:
        return 1.0
    if k > n:
        return 0.0
    if p <= 0.0:
        return 0.0
    if p >= 1.0:
        return 1.0
    total = _reg_incomplete_beta(p, float(k), float(n - k + 1))
    return min(1.0, max(0.0, total))


def years_to_own_the_world(
    monthly_return: float, start_capital: float = 100_000.0
) -> float | None:
    """複利歸謬法:照這個月報酬複利下去,幾年後會擁有全世界的錢?

        capital * (1 + r)^(12Y) >= WORLD_GDP
        → Y = log(WORLD_GDP / capital) / (12 * log(1 + r))

    回傳 None 表示月報酬 <= 0(不會發散)。
    這不是嘲諷,是嚴謹的歸謬:若一個宣稱在數學上導致荒謬結論,該宣稱為假。
    """
    if monthly_return <= 0 or start_capital <= 0:
        return None
    if start_capital >= WORLD_GDP_TWD:
        return 0.0
    return math.log(WORLD_GDP_TWD / start_capital) / (12 * math.log(1 + monthly_return))


@dataclass(frozen=True)
class GuruClaimAnalysis:
    """對「老師宣稱」的檢驗結果。"""

    # 使用者輸入的宣稱
    claimed_win_rate: float | None = None
    claimed_trades: int | None = None
    claimed_winning_months: int | None = None
    total_months: int | None = None
    claimed_monthly_return: float | None = None
    payoff_ratio: float | None = None
    n_gurus_in_market: int = 1000

    # 虛無假設
    null_win_prob: float = 0.5

    # 計算結果(None 表示資訊不足,無法計算 —— 誠實地不編數字)
    luck_prob_win_rate: float | None = None
    luck_prob_streak: float | None = None
    expected_gurus_achieving: float | None = None
    required_trades: int | None = None
    years_to_own_world: float | None = None
    internal_contradiction: str | None = None

    verdict: str = "資訊不足"
    findings: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        return d


def analyze_guru_claim(
    *,
    claimed_win_rate: float | None = None,
    claimed_trades: int | None = None,
    claimed_winning_months: int | None = None,
    total_months: int | None = None,
    claimed_monthly_return: float | None = None,
    payoff_ratio: float | None = None,
    n_gurus_in_market: int = 1000,
    null_win_prob: float = 0.5,
) -> GuruClaimAnalysis:
    """檢驗老師的績效宣稱。所有欄位都可選 —— 給多少算多少,不編造。

    Args:
        claimed_win_rate:      宣稱的勝率(0~1)
        claimed_trades:        宣稱基於幾筆交易(**沒有這個就無法檢驗勝率**)
        claimed_winning_months: 宣稱連續獲利幾個月
        total_months:          整段紀錄總共幾個月(用於修正「挑區間」的偏差)
        claimed_monthly_return: 宣稱的月報酬(0.2 = 20%)
        payoff_ratio:          宣稱的盈虧比(用於一致性檢查)
        n_gurus_in_market:     市面上有多少人在自稱老師(倖存者偏差的分母)
        null_win_prob:         虛無假設下的單次勝率。預設 0.5。
    """
    findings: list[str] = []
    caveats: list[str] = []

    luck_wr: float | None = None
    luck_streak: float | None = None
    expected_gurus: float | None = None
    req_trades: int | None = None
    years: float | None = None
    contradiction: str | None = None

    # ── 1. 宣稱的勝率:純運氣達成的機率(二項上尾)──
    if claimed_win_rate is not None:
        if claimed_trades is None or claimed_trades < 1:
            findings.append(
                "⚠️ 他只說勝率,沒說『基於幾筆交易』—— 這種宣稱無法檢驗。"
                "10 筆裡贏 9 筆(90%)跟 1000 筆裡贏 900 筆(90%),可信度天差地遠。"
                "先問他:這個勝率是幾筆交易算出來的?"
            )
        else:
            wins = int(round(claimed_win_rate * claimed_trades))
            luck_wr = binomial_tail_ge(claimed_trades, wins, null_win_prob)
            findings.append(
                f"他宣稱 {claimed_trades} 筆裡贏 {wins} 筆(勝率 {claimed_win_rate:.0%})。"
                f"假設他毫無能力(每筆贏的機率 {null_win_prob:.0%}),"
                f"純靠運氣達到這個成績的機率是 {luck_wr:.4%}。"
            )
            if luck_wr > 0.05:
                findings.append(
                    "→ 這個機率不算低。單看這份成績,無法排除他只是運氣好。"
                )
            else:
                findings.append(
                    "→ 這個機率很低。但**低機率不等於有能力**:"
                    f"若市面上有 {n_gurus_in_market} 個人都在猜,"
                    f"期望會有 {n_gurus_in_market * luck_wr:.1f} 個人達成 —— "
                    "而你只會看到達成的那幾個(倖存者偏差)。"
                )
                expected_gurus = n_gurus_in_market * luck_wr

    # ── 2. 連續獲利月數:純運氣的機率 ──
    if claimed_winning_months is not None and claimed_winning_months > 0:
        if total_months and total_months >= claimed_winning_months:
            # 有完整紀錄長度 → 用 run-in-T(正確處理「從長紀錄挑一段」的偏差)
            luck_streak = prob_streak_in_trials(
                total_months, claimed_winning_months, null_win_prob
            )
            findings.append(
                f"他宣稱在 {total_months} 個月的紀錄裡,有連續 {claimed_winning_months} "
                f"個月獲利。純靠運氣出現這種連勝的機率是 {luck_streak:.2%}。"
            )
        else:
            # 只知道連勝長度 → N-for-N
            luck_streak = prob_perfect_run(claimed_winning_months, null_win_prob)
            findings.append(
                f"他宣稱連續 {claimed_winning_months} 個月獲利。"
                f"假設每個月獲利的機率是 {null_win_prob:.0%},"
                f"純靠運氣連續達成的機率是 {luck_streak:.2%}。"
            )
            caveats.append(
                "他沒說『總共交易了幾個月』。如果他做了 5 年(60 個月),"
                "從裡面挑出一段連續 12 個月獲利,比「一開始就連贏 12 個月」"
                "容易得多 —— 這叫挑選偏差,要問他完整紀錄有多長。"
            )
        exp_n = expected_number_with_streak(
            n_gurus_in_market,
            total_months or claimed_winning_months,
            claimed_winning_months,
            null_win_prob,
        )
        findings.append(
            f"若市面上有 {n_gurus_in_market} 個自稱老師的人全都在瞎猜,"
            f"期望會有 {exp_n:.1f} 個人達成這種連勝 —— 而他們會被推出來當名師。"
        )
        if expected_gurus is None:
            expected_gurus = exp_n

    # ── 3. 需要多少樣本才能證明不是運氣 ──
    if claimed_win_rate is not None and payoff_ratio is not None and payoff_ratio > 0:
        req_trades = required_sample_size(claimed_win_rate, payoff_ratio)
        if claimed_trades and req_trades > claimed_trades:
            findings.append(
                f"以他宣稱的勝率與盈虧比,要在統計上證明「這不是運氣」,"
                f"至少需要約 {req_trades} 筆交易 —— 而他只給了你 {claimed_trades} 筆。"
            )

    # ── 4. 內部一致性:宣稱穩賺,但期望值卻是負的?──
    if claimed_win_rate is not None and payoff_ratio is not None:
        expectancy_r = claimed_win_rate * payoff_ratio - (1 - claimed_win_rate)
        if expectancy_r <= 0:
            contradiction = (
                f"他宣稱勝率 {claimed_win_rate:.0%}、盈虧比 {payoff_ratio:.2f},"
                f"但這組數字算出來的每筆期望值是 {expectancy_r:+.3f} R(負的)——"
                "照他自己給的數字,長期下去是**賠錢**的。宣稱本身自相矛盾。"
            )
            findings.append(f"🔴 {contradiction}")

    # ── 5. 複利歸謬:月報酬 20% 意味著什麼 ──
    if claimed_monthly_return is not None and claimed_monthly_return > 0:
        years = years_to_own_the_world(claimed_monthly_return)
        if years is not None:
            annual = (1 + claimed_monthly_return) ** 12 - 1
            findings.append(
                f"他宣稱月報酬 {claimed_monthly_return:.0%},等於年化 {annual:.0%}。"
                f"若真能持續,從 10 萬台幣開始,只要 **{years:.1f} 年** 就能賺到"
                "超過全世界一年的 GDP。"
            )
            findings.append(
                "→ 這在數學上是荒謬的。所以這個宣稱要嘛是短期運氣、"
                "要嘛是假的、要嘛無法持續。真能穩定做到的人,不會需要你的錢。"
            )

    # ── 裁決(序數,不給假百分比)──
    # 「有沒有算出任何機率」才是能不能下結論的關鍵,不是「有沒有話可說」。
    computed_anything = any(
        x is not None for x in (luck_wr, luck_streak, years, contradiction)
    )
    if not computed_anything:
        verdict = "資訊不足,無法檢驗"
        if not findings:
            findings.append(
                "你提供的資訊不足以檢驗。至少要知道:勝率是基於幾筆交易、"
                "或完整紀錄有多長。**問不出這些,本身就是最大的警訊。**"
            )
    elif contradiction:
        verdict = "宣稱自相矛盾"
    elif luck_wr is not None and luck_wr > 0.05:
        verdict = "與純運氣無法區分"
    elif years is not None and years < 30:
        verdict = "宣稱在數學上不可能持續"
    elif expected_gurus is not None and expected_gurus >= 1.0:
        verdict = "可由倖存者偏差解釋"
    else:
        verdict = "需要完整紀錄才能判斷"

    caveats.append(
        f"以上機率都建立在「虛無假設:他毫無能力,單次勝率 = {null_win_prob:.0%}」之上。"
        "若他交易的是長期上漲的大盤,單月上漲的基準機率其實約 55~62%,"
        "此時應把 null_win_prob 調高,否則會高估他的『神奇程度』。"
    )
    caveats.append(
        "低機率**不等於**有能力。要證明有能力,唯一的方法是看他"
        "完整、連續、夠長的交易紀錄(含所有失敗),丟進統計檢定與樣本外驗證。"
    )

    return GuruClaimAnalysis(
        claimed_win_rate=claimed_win_rate,
        claimed_trades=claimed_trades,
        claimed_winning_months=claimed_winning_months,
        total_months=total_months,
        claimed_monthly_return=claimed_monthly_return,
        payoff_ratio=payoff_ratio,
        n_gurus_in_market=n_gurus_in_market,
        null_win_prob=null_win_prob,
        luck_prob_win_rate=luck_wr,
        luck_prob_streak=luck_streak,
        expected_gurus_achieving=expected_gurus,
        required_trades=req_trades,
        years_to_own_world=years,
        internal_contradiction=contradiction,
        verdict=verdict,
        findings=findings,
        caveats=caveats,
    )


def render_guru_claim(a: GuruClaimAnalysis) -> str:
    """輸出可讀的文字報告。"""
    L = ["=" * 60, "        假老師績效驗證器 — 把宣稱丟進數學裡檢驗", "=" * 60, ""]
    L.append(f"【裁決】{a.verdict}")
    L.append("")
    L.append("【檢驗結果】")
    for f in a.findings:
        L.append(f"  • {f}")
    L.append("")
    L.append("【必須知道的前提】")
    for c in a.caveats:
        L.append(f"  ⚠ {c}")
    L.append("")
    L.append("─" * 60)
    L.append("本工具不指控任何人是騙子。它只回答一個問題:")
    L.append("『在他毫無能力的假設下,這種績效有多容易靠運氣發生?』")
    return "\n".join(L)
