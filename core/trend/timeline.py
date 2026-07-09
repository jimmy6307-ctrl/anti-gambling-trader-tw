"""S3 — 時間趨勢分析:「我是在進步還是退步?優勢是不是正在消失?」

這個模組回答的是「時間」的問題:把交易依出場時間排開,看損益/勝率/期望值
隨時間怎麼變、權益曲線長什麼樣、以及優勢有沒有在衰退。

⚠️ 本模組的最大風險是「假精準」與「p-hacking」。時間序列最容易被誤讀:
   人腦看到一條上下起伏的曲線就會腦補出「趨勢」。因此本模組的設計原則是:

   1. 分月/分季彙總、權益曲線、滾動期望值 —— 一律當作**描述統計**,
      不附任何顯著性判定、不對個別月份下結論。
   2. 小樣本月份(如只有 2~3 筆)明確標記「資料不足,不判讀」,
      只列數字、不給勝率/期望值的解讀。
   3. 「優勢衰退偵測」只做**一次、事先指定**的比較(早期一半 vs 近期一半),
      而且用「報酬率(return_pct)」而非「金額(pnl)」,以免部位變大被誤讀成優勢。
      絕不掃描多個切點/多個 K 值去找「最像衰退」的那一個 —— 那是資料探勘。
   4. 樣本不足以判斷時,誠實說「無法判斷」,不編造樂觀或悲觀的結論。

與既有模組的關係:
   - 逐段的顯著性、樣本內/外優勢是否延續,由 backtest.holdout_validate 負責;
     本模組的 detect_decay 是「早期 vs 近期」的互補視角,兩者都是單一切點、不重覆檢定。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..metrics.performance import compute_metrics
from ..models import TradeLog
from ..verdict.statistics import TwoSampleResult, welch_mean_test

# ── 樣本量門檻(與全專案慣例對齊)────────────────────────────
# < TOO_FEW:只列數字,一律不判讀(2~3 筆的月份就是這種)。
# < LOW_SAMPLE:數字可看,但標記「樣本少,僅供參考」。
# 30 這個界線沿用 verdict/judge 的 min_trades 與 per_tag 的 low_sample 慣例。
TOO_FEW_TRADES = 5
LOW_SAMPLE_TRADES = 30

# 衰退偵測:早/近兩段各至少這麼多筆才做檢定(總數約需 >= 2×)。
# 沿用 30 的「可判定」門檻:每段 15,總數 30。低於此一律回報「無法判斷」。
MIN_PER_HALF = 15

# 滾動期望值的預設視窗。太小 → 全是雜訊;太大 → 看不出變化。
DEFAULT_ROLLING_WINDOW = 20


# ══════════════════════════════════════════════════════════════
# 1) 分期彙總(描述統計)
# ══════════════════════════════════════════════════════════════
@dataclass
class PeriodBucket:
    """單一時間桶(月或季)的描述統計。

    reliability 三態,決定「這桶的數字能不能拿來下結論」:
      "too_few" : 筆數 < TOO_FEW,只列數字,任何勝率/期望值都不判讀。
      "low"     : TOO_FEW <= 筆數 < LOW_SAMPLE,可參考但不可當定論。
      "ok"      : 筆數 >= LOW_SAMPLE,較可靠(仍只是描述,非顯著性認證)。
    """

    period_key: str          # 機器可讀鍵,如 "2026-01" 或 "2026-Q1"
    period_label: str        # 顯示用,如 "2026 年 1 月"
    n_trades: int
    wins: int
    losses: int
    win_rate: float
    expectancy: float        # 每筆期望損益(金額)
    total_pnl: float
    avg_return_pct: float     # 每筆平均報酬率(scale-invariant,較能跨期比較)
    reliability: str         # "ok" | "low" | "too_few"

    @property
    def too_few(self) -> bool:
        return self.reliability == "too_few"

    @property
    def low_sample(self) -> bool:
        return self.reliability in ("too_few", "low")

    @property
    def note(self) -> str:
        if self.reliability == "too_few":
            return f"僅 {self.n_trades} 筆,資料不足,不對此期下任何結論(只列數字)。"
        if self.reliability == "low":
            return f"僅 {self.n_trades} 筆,樣本偏少,數字僅供參考,勿當定論。"
        return ""

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["too_few"] = self.too_few
        d["low_sample"] = self.low_sample
        d["note"] = self.note
        return d


_MONTH_CN = "1 2 3 4 5 6 7 8 9 10 11 12".split()


def _period_key(dt, granularity: str) -> tuple[str, str]:
    """回傳 (機器鍵, 顯示標籤)。"""
    if granularity == "quarter":
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{q}", f"{dt.year} 年 Q{q}"
    # 預設月
    return f"{dt.year}-{dt.month:02d}", f"{dt.year} 年 {_MONTH_CN[dt.month - 1]} 月"


def _reliability(n: int) -> str:
    if n < TOO_FEW_TRADES:
        return "too_few"
    if n < LOW_SAMPLE_TRADES:
        return "low"
    return "ok"


def bucket_by_period(
    log: TradeLog, *, granularity: str = "month"
) -> list[PeriodBucket]:
    """依 exit_time 把交易分月(或分季)彙總,回傳按時間排序的桶。

    granularity: "month" | "quarter"。

    這是純描述統計:每桶各自呼叫 compute_metrics,不做顯著性、不做跨桶檢定。
    小樣本桶會被標記 reliability,呈現時務必尊重(見 render_trend_text)。
    """
    if granularity not in ("month", "quarter"):
        raise ValueError("granularity 必須是 'month' 或 'quarter'")

    ordered = list(log.sorted_by_time())
    groups: dict[str, list] = {}
    labels: dict[str, str] = {}
    for t in ordered:
        key, label = _period_key(t.exit_time, granularity)
        groups.setdefault(key, []).append(t)
        labels[key] = label

    buckets: list[PeriodBucket] = []
    for key in sorted(groups):
        sub = TradeLog(groups[key], log.source, f"{log.account_label}::{key}")
        m = compute_metrics(sub)
        rets = [t.return_pct for t in groups[key]]
        avg_ret = sum(rets) / len(rets) if rets else 0.0
        buckets.append(PeriodBucket(
            period_key=key,
            period_label=labels[key],
            n_trades=m.total_trades,
            wins=m.wins,
            losses=m.losses,
            win_rate=m.win_rate,
            expectancy=m.expectancy,
            total_pnl=m.total_pnl,
            avg_return_pct=avg_ret,
            reliability=_reliability(m.total_trades),
        ))
    return buckets


# ══════════════════════════════════════════════════════════════
# 2) 權益曲線(累積 pnl)
# ══════════════════════════════════════════════════════════════
@dataclass
class EquityPoint:
    """權益曲線上的一點(依出場時間累積已實現損益)。"""

    index: int               # 第幾筆(1-based)
    exit_time: str           # ISO 時間字串(方便丟給前端畫圖)
    pnl: float               # 這一筆的損益
    cum_pnl: float           # 累積損益
    drawdown: float          # 距歷史高點的回撤(>=0)

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def equity_curve(log: TradeLog) -> list[EquityPoint]:
    """依出場時間累積已實現損益,產生權益曲線資料(供 HTML 報告畫圖)。

    只計「已平倉」的已實現損益 —— 與全工具口徑一致(未平倉浮動不算)。
    同時附上每點的回撤,方便圖上標示水下區間。這裡是單純的累加,
    不做任何推論。
    """
    ordered = list(log.sorted_by_time())
    points: list[EquityPoint] = []
    cum = 0.0
    peak = 0.0
    for i, t in enumerate(ordered, start=1):
        p = t.pnl or 0.0
        cum += p
        peak = max(peak, cum)
        points.append(EquityPoint(
            index=i,
            exit_time=t.exit_time.isoformat(),
            pnl=p,
            cum_pnl=cum,
            drawdown=peak - cum,
        ))
    return points


# ══════════════════════════════════════════════════════════════
# 3) 滾動期望值(描述統計,不附任何趨勢檢定)
# ══════════════════════════════════════════════════════════════
@dataclass
class RollingPoint:
    """滾動視窗的期望值(每筆平均損益)。"""

    index: int               # 視窗右端是第幾筆(1-based)
    exit_time: str
    window: int              # 視窗實際包含筆數
    rolling_expectancy: float
    rolling_return_pct: float

    def as_dict(self) -> dict:
        return self.__dict__.copy()


def rolling_expectancy(
    log: TradeLog, *, window: int = DEFAULT_ROLLING_WINDOW
) -> list[RollingPoint]:
    """滾動視窗期望值曲線(供 HTML 報告畫圖)。

    ⚠️ 這是**描述統計,不是趨勢檢定**。相鄰的滾動點彼此高度重疊、
       嚴重自我相關,對它做斜率/顯著性檢定會嚴重高估把握度。
       它的用途只有一個:讓使用者「看見」期望值大致的高低起伏,
       但任何「看起來在跌」都不可當成優勢衰退的證據 —— 那要交給 detect_decay。

    若總筆數不足一個完整視窗,回傳空清單(不硬湊、不用殘缺視窗製造假訊號)。
    """
    if window < 2:
        raise ValueError("window 至少為 2")
    ordered = list(log.sorted_by_time())
    n = len(ordered)
    if n < window:
        return []
    pnls = [t.pnl or 0.0 for t in ordered]
    rets = [t.return_pct for t in ordered]
    points: list[RollingPoint] = []
    for i in range(window - 1, n):
        seg_p = pnls[i - window + 1:i + 1]
        seg_r = rets[i - window + 1:i + 1]
        points.append(RollingPoint(
            index=i + 1,
            exit_time=ordered[i].exit_time.isoformat(),
            window=window,
            rolling_expectancy=sum(seg_p) / window,
            rolling_return_pct=sum(seg_r) / window,
        ))
    return points


# ══════════════════════════════════════════════════════════════
# 4) 優勢衰退偵測(單一、事先指定的比較)
# ══════════════════════════════════════════════════════════════
@dataclass
class DecayResult:
    """「早期 vs 近期」優勢變化的偵測結果。

    核心誠實原則:
      - 只切一次(前半 / 後半,依交易筆數對半分),不掃描切點。
      - 用 return_pct(報酬率)做檢定,而非金額 —— 否則『後期部位變大』
        會被誤讀成『優勢變強』,反之亦然。金額期望值另外附上供參考。
      - 雙尾檢定(問「有沒有變」),方向再由 diff 描述(進步 or 退步)。
      - 樣本不足就誠實回報 enough_data=False,不硬給結論。
    """

    enough_data: bool
    early_n: int
    recent_n: int
    early_expectancy: float          # 金額(描述用)
    recent_expectancy: float
    early_return_pct: float          # 報酬率(檢定用的口徑)
    recent_return_pct: float
    direction: str                   # "improving" | "declining" | "flat" | "unknown"
    p_value: float | None            # 雙尾;None 表示未做檢定
    is_significant_change: bool      # 是否統計上顯著不同
    headline: str
    caveats: list[str] = field(default_factory=list)
    test: TwoSampleResult | None = None

    def as_dict(self) -> dict:
        return {
            "enough_data": self.enough_data,
            "early_n": self.early_n,
            "recent_n": self.recent_n,
            "early_expectancy": self.early_expectancy,
            "recent_expectancy": self.recent_expectancy,
            "early_return_pct": self.early_return_pct,
            "recent_return_pct": self.recent_return_pct,
            "direction": self.direction,
            "p_value": self.p_value,
            "is_significant_change": self.is_significant_change,
            "headline": self.headline,
            "caveats": self.caveats,
        }


def detect_decay(log: TradeLog, *, alpha: float = 0.05) -> DecayResult:
    """偵測優勢是否隨時間顯著變化(早期一半 vs 近期一半)。

    這是**唯一**做顯著性檢定的趨勢功能,且刻意只做一次固定切點的比較,
    以避免多重比較 / 資料探勘。方向的判讀:
      - 顯著且近期較低 → declining(優勢疑似衰退,值得警覺)
      - 顯著且近期較高 → improving(帳面在進步,但仍非未來保證)
      - 不顯著        → flat(看不出明顯變化,注意:這不等於「沒有變化」)
    """
    ordered = list(log.sorted_by_time())
    n = len(ordered)

    common_caveats = [
        "此比較用『報酬率』而非金額,以免部位大小變化被誤讀成優勢變化。",
        "『看不出變化』不等於『沒有變化』—— 只是現有樣本還分辨不出來。",
        "這只是單一切點的描述性比較;是否為可延續的優勢,請一併看樣本外驗證。",
    ]

    if n < 2 * MIN_PER_HALF:
        return DecayResult(
            enough_data=False,
            early_n=0, recent_n=0,
            early_expectancy=0.0, recent_expectancy=0.0,
            early_return_pct=0.0, recent_return_pct=0.0,
            direction="unknown", p_value=None, is_significant_change=False,
            headline=(
                f"⚠️ 交易筆數不足(僅 {n} 筆,每段至少需 {MIN_PER_HALF} 筆):"
                "無法判斷優勢是否隨時間變化,請先累積更多交易。"
            ),
            caveats=["樣本太少時,任何『進步/退步』的說法都只是雜訊。"],
        )

    half = n // 2
    early, recent = ordered[:half], ordered[half:]
    early_ret = [t.return_pct for t in early]
    recent_ret = [t.return_pct for t in recent]
    early_m = compute_metrics(TradeLog(early, log.source))
    recent_m = compute_metrics(TradeLog(recent, log.source))

    test = welch_mean_test(early_ret, recent_ret, alpha=alpha)
    early_r = sum(early_ret) / len(early_ret)
    recent_r = sum(recent_ret) / len(recent_ret)

    if test is None:
        direction, sig, p = "unknown", False, None
        headline = "⚠️ 兩段資料變異異常,無法完成比較。"
    elif test.is_significant:
        if recent_r < early_r:
            direction = "declining"
            headline = (
                "🔻 優勢疑似衰退:近期的每筆報酬率,顯著低於早期。"
                "請提高警覺 —— 這可能是市場結構改變或方法失效的訊號。"
            )
        else:
            direction = "improving"
            headline = (
                "🔺 近期在進步:近期的每筆報酬率,顯著高於早期。"
                "但別高興太早,這仍是過去的表現,不是未來的保證。"
            )
        sig, p = True, test.p_value
    else:
        direction = "flat"
        p = test.p_value
        sig = False
        headline = (
            f"➖ 看不出顯著變化:近期與早期的每筆報酬率沒有統計上的顯著差異"
            f"(雙尾 p={p:.3f})。注意:這不代表『一定沒變』,只是樣本還分不出來。"
        )

    return DecayResult(
        enough_data=True,
        early_n=len(early), recent_n=len(recent),
        early_expectancy=early_m.expectancy, recent_expectancy=recent_m.expectancy,
        early_return_pct=early_r, recent_return_pct=recent_r,
        direction=direction, p_value=p, is_significant_change=sig,
        headline=headline, caveats=common_caveats, test=test,
    )


# ══════════════════════════════════════════════════════════════
# 5) 編排 + 文字輸出
# ══════════════════════════════════════════════════════════════
@dataclass
class TrendReport:
    """時間趨勢分析的完整產出。"""

    granularity: str
    buckets: list[PeriodBucket]
    equity: list[EquityPoint]
    rolling: list[RollingPoint]
    decay: DecayResult
    rolling_window: int

    def as_dict(self) -> dict:
        return {
            "granularity": self.granularity,
            "rolling_window": self.rolling_window,
            "buckets": [b.as_dict() for b in self.buckets],
            "equity": [e.as_dict() for e in self.equity],
            "rolling": [r.as_dict() for r in self.rolling],
            "decay": self.decay.as_dict(),
        }


def _auto_granularity(log: TradeLog) -> str:
    """資料橫跨很久(> 24 個月)時改用季,避免月桶太多且各自太小。"""
    months = {(t.exit_time.year, t.exit_time.month) for t in log}
    return "quarter" if len(months) > 24 else "month"


def analyze_trend(
    log: TradeLog,
    *,
    granularity: str = "auto",
    rolling_window: int = DEFAULT_ROLLING_WINDOW,
) -> TrendReport:
    """一次算好所有時間趨勢產物(分期彙總 / 權益曲線 / 滾動期望值 / 衰退偵測)。

    granularity: "auto"(預設)| "month" | "quarter"。
    """
    gran = _auto_granularity(log) if granularity == "auto" else granularity
    return TrendReport(
        granularity=gran,
        buckets=bucket_by_period(log, granularity=gran),
        equity=equity_curve(log),
        rolling=rolling_expectancy(log, window=rolling_window),
        decay=detect_decay(log),
        rolling_window=rolling_window,
    )


def _money(x: float) -> str:
    return f"{x:,.2f}"


def render_trend_text(report: TrendReport) -> str:
    """把 TrendReport 轉成純文字段落(風格對齊 core/report.py)。"""
    L: list[str] = []
    unit = "季" if report.granularity == "quarter" else "月"
    L.append(f"【📈 時間趨勢 — 我在進步還是退步?(依{unit}彙總)】")

    if not report.buckets:
        L.append("  沒有可彙總的交易。")
        return "\n".join(L)

    L.append(f"  期間            筆數   勝率     每筆期望值      總損益      狀態")
    L.append("  " + "─" * 64)
    for b in report.buckets:
        if b.too_few:
            status = "資料不足,不判讀"
            wr = exp = "  —  "
        else:
            status = "樣本少" if b.low_sample else ""
            wr = f"{b.win_rate:.0%}"
            exp = _money(b.expectancy)
        L.append(
            f"  {b.period_label:<12}  {b.n_trades:>4}   {wr:>5}   "
            f"{exp:>12}   {_money(b.total_pnl):>12}   {status}"
        )
    L.append(
        "  註:分期數字為『描述統計』,不對個別期間下優勢/運氣的結論;"
        "筆數過少的期間只列數字、不判讀。"
    )
    L.append("")

    # 權益曲線摘要(完整資料在 as_dict()['equity'],供 HTML 畫圖)
    if report.equity:
        last = report.equity[-1]
        max_dd = max((e.drawdown for e in report.equity), default=0.0)
        L.append("【💰 權益曲線(累積已實現損益)】")
        L.append(
            f"  共 {len(report.equity)} 筆,期末累積損益 {_money(last.cum_pnl)};"
            f"過程中最大回撤 {_money(max_dd)}。"
        )
        L.append("  (完整曲線資料可輸出給 HTML 報告畫圖。)")
        L.append("")

    # 滾動期望值(僅描述)
    if report.rolling:
        first_r = report.rolling[0].rolling_expectancy
        last_r = report.rolling[-1].rolling_expectancy
        L.append(f"【🔁 滾動期望值(每 {report.rolling_window} 筆一個視窗)】")
        L.append(
            f"  視窗期望值從 {_money(first_r)} 到 {_money(last_r)}。"
            "此為描述性曲線,相鄰點高度重疊,請勿把上下起伏當成趨勢證據。"
        )
        L.append("")

    # 衰退偵測
    d = report.decay
    L.append("【🔎 優勢是不是正在消失?(早期 vs 近期,單一檢定)】")
    L.append(f"  {d.headline}")
    if d.enough_data:
        L.append(
            f"  早期 {d.early_n} 筆:每筆報酬率 {d.early_return_pct:+.2%}"
            f"(金額期望值 {_money(d.early_expectancy)})"
        )
        L.append(
            f"  近期 {d.recent_n} 筆:每筆報酬率 {d.recent_return_pct:+.2%}"
            f"(金額期望值 {_money(d.recent_expectancy)})"
        )
        for c in d.caveats:
            L.append(f"    - {c}")
    return "\n".join(L)
