"""統計檢定工具 — 不依賴 scipy,純標準函式庫實作。

我們要回答的核心問題是:
「這個策略的『平均每筆賺錢』,有沒有可能其實只是運氣?」

用兩種互補的方法:
1. t 檢定:在常態近似下,平均報酬顯著大於 0 的機率
2. Bootstrap 重抽樣:不假設分布,直接從資料重抽,看「平均值 ≤ 0」的頻率
   (這對交易資料特別重要,因為損益分布通常嚴重偏態、厚尾)
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

# 單尾 α=0.05 的常態分位數,與 80% 檢定力的分位數。
# 樣本量估計需同時涵蓋「型 I 錯誤」與「型 II 錯誤(檢定力)」——
# 只用 z_alpha(或原本寫死的常數 2)等於只有約 50% 檢定力,會低估所需樣本。
Z_ALPHA_ONE_SIDED = 1.6449
Z_POWER_80 = 0.8416

# 負期望時「所需樣本量」沒有意義的哨兵值(對外一律轉成 None,不顯示給使用者)
NEGATIVE_EDGE_SENTINEL = 9999

# bootstrap 總抽樣次數上限(n × n_bootstrap)。純 Python 抽樣約 300 萬次/秒,
# 10,000 筆 × 5,000 次 = 5,000 萬次 ≈ 17 秒 —— 整個 analyze 管線會跑到 ~24 秒。
# 超過上限時自動調降重抽次數(但不低於 1,000 次,分位數索引仍有 25 的精度)。
# 誠實揭露:大樣本下 t 檢定本就極可靠,bootstrap 是第二道保險,降次數不損結論。
MAX_BOOTSTRAP_DRAWS = 20_000_000


@dataclass
class SignificanceResult:
    """期望值顯著性檢定的結果。"""

    n: int                       # 樣本數
    mean: float                  # 樣本平均
    std: float                   # 樣本標準差
    t_stat: float                # t 統計量
    p_value_t: float             # t 檢定的單尾 p 值(H0: mean <= 0)
    p_value_bootstrap: float     # bootstrap 下平均值 <= 0 的比例
    ci_low: float                # 平均值的 95% 信賴區間下界(bootstrap)
    ci_high: float               # 上界
    is_significant: bool         # 在 α=0.05 下是否顯著為正


def _normal_cdf(x: float) -> float:
    """標準常態累積分布函數(用 erf)。"""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def _betacf(a: float, b: float, x: float, *, max_iter: int = 200,
            eps: float = 1e-12) -> float:
    """不完全 beta 函數的連分數展開(Lentz 演算法)。"""
    tiny = 1e-30
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < tiny:
        d = tiny
    d = 1.0 / d
    h = d
    for m in range(1, max_iter + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < tiny:
            d = tiny
        c = 1.0 + aa / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < eps:
            break
    return h


def _reg_incomplete_beta(x: float, a: float, b: float) -> float:
    """正則化不完全 beta 函數 I_x(a, b),純標準庫實作。"""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    ln_beta = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
    front = math.exp(ln_beta + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return front * _betacf(a, b, x) / a
    return 1.0 - front * _betacf(b, a, 1.0 - x) / b


def _student_t_sf(t: float, df: int) -> float:
    """Student-t 分布的單尾存活函數 P(T > t),用真正的 t 分布 CDF。

    透過正則化不完全 beta 函數計算(不依賴 scipy)。這取代了先前自創的
    收縮近似 —— 對小樣本(df 5~15)的尾端機率才會正確,而非拍腦袋的常數。
    """
    if df <= 0:
        return 1.0
    if t == 0:
        return 0.5
    x = df / (df + t * t)
    # I_x(df/2, 1/2) 給的是雙尾機率;單尾依 t 的正負對半分配
    ib = _reg_incomplete_beta(x, df / 2.0, 0.5)
    if t > 0:
        return 0.5 * ib
    return 1.0 - 0.5 * ib


def test_expectancy_positive(
    pnls: list[float],
    *,
    n_bootstrap: int = 5000,
    alpha: float = 0.05,
    seed: int = 1234,
) -> SignificanceResult:
    """檢定「每筆交易的平均損益是否顯著大於 0」。

    這是分辨「真優勢」與「賭博」最關鍵的一步:
    一個賭徒即使長期期望值為負,短期也可能因運氣而帳面為正。
    我們要問的是 — 在統計上,我們有多大把握說這個正期望值不是運氣?

    Args:
        pnls:         每筆交易的損益(已扣成本)
        n_bootstrap:  bootstrap 重抽次數
        alpha:        顯著水準(預設 0.05)
        seed:         亂數種子,確保結果可重現

    Returns:
        SignificanceResult
    """
    # n_bootstrap < 1 會導致除以零(p_boot)或空 list 索引(CI 分位數),
    # 且 CLI 的 --bootstrap 直通這裡 —— 必須在入口擋下,給清楚的錯誤訊息。
    if n_bootstrap < 1:
        raise ValueError(f"n_bootstrap 必須 >= 1,收到 {n_bootstrap}")

    n = len(pnls)
    if n == 0:
        return SignificanceResult(0, 0, 0, 0, 1.0, 1.0, 0, 0, False)

    mean = sum(pnls) / n
    if n < 2:
        # 單筆樣本無法做任何統計推論 — 一律視為不顯著
        return SignificanceResult(n, mean, 0.0, 0.0, 1.0, 1.0, mean, mean, False)

    # 大樣本自動調降重抽次數(見 MAX_BOOTSTRAP_DRAWS 的說明)
    if n * n_bootstrap > MAX_BOOTSTRAP_DRAWS:
        n_bootstrap = max(1000, MAX_BOOTSTRAP_DRAWS // n)

    var = sum((p - mean) ** 2 for p in pnls) / (n - 1)
    std = math.sqrt(var)

    # ── t 檢定 ──
    se = std / math.sqrt(n) if std > 0 else 0.0
    if se > 0:
        t_stat = mean / se
        p_t = _student_t_sf(t_stat, n - 1)
    else:
        # 標準差為 0:所有交易損益相同。全正則確定獲利,全負則確定虧損
        t_stat = math.inf if mean > 0 else (-math.inf if mean < 0 else 0.0)
        p_t = 0.0 if mean > 0 else 1.0

    # ── Bootstrap ──
    # 用 random.choices 一次抽整批(CPython C 實作):實測比逐一 randrange
    # 快約 4.6 倍。分布完全相同(均勻、有放回),同 seed 仍可重現;
    # 僅抽樣序列與舊版不同,統計上等價。
    rng = random.Random(seed)
    boot_means: list[float] = []
    for _ in range(n_bootstrap):
        boot_means.append(sum(rng.choices(pnls, k=n)) / n)
    boot_means.sort()

    # 平均值 <= 0 的比例 ≈ 「期望其實不為正」的經驗機率
    n_le_zero = sum(1 for bm in boot_means if bm <= 0)
    p_boot = n_le_zero / n_bootstrap

    lo_idx = int((alpha / 2) * n_bootstrap)
    hi_idx = min(int((1 - alpha / 2) * n_bootstrap), n_bootstrap - 1)
    ci_low = boot_means[lo_idx]
    ci_high = boot_means[hi_idx]

    # 同時要求兩種檢定都過關,才算顯著(雙重保險,偏保守)
    is_sig = (p_t < alpha) and (p_boot < alpha) and (mean > 0)

    return SignificanceResult(
        n=n,
        mean=mean,
        std=std,
        t_stat=t_stat,
        p_value_t=p_t,
        p_value_bootstrap=p_boot,
        ci_low=ci_low,
        ci_high=ci_high,
        is_significant=is_sig,
    )


def required_sample_size(win_rate: float, payoff_ratio: float) -> int:
    """粗估「要多少筆交易,才足以驗證這個策略不是運氣」。

    直覺:勝率越接近 50%、盈虧比越接近 1,訊號越微弱,
    需要越多樣本才能從雜訊中分辨出真實優勢。

    這是一個經驗性的指引值,不是嚴格的統計檢定力分析,
    目的是讓使用者對「我交易的次數夠不夠」有量化的概念。
    """
    # 無虧損樣本的 payoff_ratio 是 inf(不適用):二項模型算不了
    # (inf-inf=NaN),回預設門檻,由呼叫端的樣本量判斷去把關
    if win_rate <= 0 or win_rate >= 1 or payoff_ratio <= 0 or math.isinf(payoff_ratio):
        return 100

    # 每筆的期望(R 為單位)與其變異,用來估所需樣本
    edge = win_rate * payoff_ratio - (1 - win_rate)
    if edge <= 0:
        return NEGATIVE_EDGE_SENTINEL  # 負期望:再多樣本也驗證不出「優勢」

    # 報酬的近似變異(白努利 × 報酬幅度)
    var = (
        win_rate * (payoff_ratio - edge) ** 2
        + (1 - win_rate) * (-1 - edge) ** 2
    )
    sd = math.sqrt(var)
    # n ≈ ((z_alpha + z_power) * sd / edge)^2
    # 原本用常數 2,約等於只有 50% 檢定力(等於擲硬幣決定能不能驗出優勢),
    # 系統性低估所需樣本、給使用者「我交易夠多了」的錯誤安心。
    n = ((Z_ALPHA_ONE_SIDED + Z_POWER_80) * sd / edge) ** 2
    return max(30, int(math.ceil(n)))


def required_sample_size_from_pnls(
    pnls: list[float], *, alpha: float = 0.05, power: float = 0.8
) -> int | None:
    """用『真實的損益樣本變異』估算所需樣本量(比二項模型貼近現實)。

    n ≈ ((z_alpha + z_power) * std / mean)^2

    二項模型假設「贏必得 payoff 個 R、輸必失 1 個 R」(組內零變異),
    但真實交易的贏家之間、輸家之間離散度很大,因此二項模型只是
    **最樂觀的下限**。有實際 pnl 時應優先用這個函式。

    Returns:
        所需樣本數;若平均損益 <= 0(負期望)則回傳 None(再多樣本也沒用)。
    """
    n = len(pnls)
    if n < 2:
        return None
    mean = sum(pnls) / n
    if mean <= 0:
        return None
    var = sum((p - mean) ** 2 for p in pnls) / (n - 1)
    std = math.sqrt(var)
    if std == 0:
        return 30
    z = Z_ALPHA_ONE_SIDED + Z_POWER_80
    if abs(power - 0.8) > 1e-9:
        z = Z_ALPHA_ONE_SIDED + _z_from_power(power)
    need = (z * std / mean) ** 2
    return max(30, int(math.ceil(need)))


def _z_from_power(power: float) -> float:
    """由檢定力反推 z(標準常態分位數),用二分法,純標準庫。"""
    lo, hi = -6.0, 6.0
    for _ in range(80):
        mid = (lo + hi) / 2
        if _normal_cdf(mid) < power:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


@dataclass
class TwoSampleResult:
    """兩獨立樣本『平均值是否不同』的 Welch 檢定結果(雙尾)。

    專用於「早期 vs 近期」這種**單一、事先指定**的比較。
    刻意不提供「掃描多個切點找最像衰退的那個」的介面 —— 那是資料探勘,
    會把雜訊當成訊號(見 trend 模組與 strategy/per_tag 的多重比較說明)。
    """

    n1: int
    n2: int
    mean1: float
    mean2: float
    diff: float                  # mean1 - mean2
    t_stat: float
    df: float                    # Welch–Satterthwaite 自由度
    p_value: float               # 雙尾 p 值(H0: 兩者平均相等)
    is_significant: bool         # 在給定 alpha 下是否顯著不同


def welch_mean_test(
    a: list[float], b: list[float], *, alpha: float = 0.05
) -> TwoSampleResult | None:
    """Welch 兩樣本 t 檢定(不假設等變異),雙尾檢定兩組平均是否不同。

    回傳 None 表示無法檢定(任一組樣本 < 2,或兩組變異都為 0)。

    設計為**雙尾**而非單尾:因為使用者的問題是「我在進步還是退步?」——
    方向未知,不該預設只找「退步」。方向由呼叫端依 diff 的正負描述,
    但顯著與否只做一次對稱的檢定,避免『兩個方向各測一次』變相 p-hacking。
    """
    n1, n2 = len(a), len(b)
    if n1 < 2 or n2 < 2:
        return None
    m1 = sum(a) / n1
    m2 = sum(b) / n2
    v1 = sum((x - m1) ** 2 for x in a) / (n1 - 1)
    v2 = sum((x - m2) ** 2 for x in b) / (n2 - 1)
    se2 = v1 / n1 + v2 / n2
    if se2 <= 0:
        # 兩組內部都零變異:平均相同→不顯著;不同→視為確定不同
        diff = m1 - m2
        return TwoSampleResult(
            n1, n2, m1, m2, diff,
            t_stat=0.0 if diff == 0 else math.copysign(math.inf, diff),
            df=float(n1 + n2 - 2),
            p_value=1.0 if diff == 0 else 0.0,
            is_significant=diff != 0,
        )
    se = math.sqrt(se2)
    t = (m1 - m2) / se
    # Welch–Satterthwaite 自由度
    df = se2 ** 2 / (
        (v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1)
    )
    # 雙尾 p:單尾存活函數對稱處理
    p = 2.0 * _student_t_sf(abs(t), df)
    p = min(1.0, max(0.0, p))
    return TwoSampleResult(
        n1=n1, n2=n2, mean1=m1, mean2=m2, diff=m1 - m2,
        t_stat=t, df=df, p_value=p, is_significant=p < alpha,
    )
