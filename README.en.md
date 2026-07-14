# Anti-Gambling Trader (反詐投資王)

[繁體中文](README.md)

**Wondering whether that investment group is a scam, whether the "guru" calling trades can be trusted, or whether your trading profits come from skill or luck?**
This is a free, open-source statistical tool: feed it your trade history (Taiwan stocks / US stocks / crypto),
and it uses expectancy, significance testing and out-of-sample validation to tell you honestly — whether your profit is a **repeatable edge**
or **luck plus survivorship bias (gambling)**. It also has built-in scam-language scanning, fake-performance forensics and fake-guru claim checking.
All analysis runs on your own computer; nothing is uploaded to any server.

> A tool that is **honest to the point of being unlikable**. It will not tell you "you will make money" —
> if your record is not suited to long-term investing, it will plainly talk you out of it.
> 👉 In a hurry for answers? Start with the **[FAQ](docs/faq.md)** (currently in Traditional Chinese):
> Is this investment group a scam? Is a 90% win rate believable? Is it normal to be asked to
> "pay tax before withdrawal"? What to do if you have been scammed?

**TL;DR** — An honest, open-source (MIT) trading-performance analyzer for
Taiwan/US stocks and crypto. It uses expectancy, significance tests (t-test +
centered bootstrap) and out-of-sample validation to tell whether your P&L is a
repeatable edge or survivorship-biased luck — and it will actively discourage you
if it's the latter. Includes scam-language scanning, fake-performance forensics
and a guru-claim probability checker. Pure Python stdlib, all analysis stays local.

## 👶 Never used a command line? Start here

If you have never installed Python, opened a terminal, or used AI, read the
**[beginner quickstart guide docs/quickstart.md](docs/quickstart.md)** (in Traditional Chinese) —
it starts from "how to install Python and open a terminal", walks you through step by step in about 15 minutes,
and shows you how to operate this tool conversationally with AI (Claude Code).

## 🛡 This tool's anti-fraud mission

Taiwan is full of **fake hot-stock groups, fake "second-stage" groups, fake VIP groups, fake gurus,
fake performance screenshots, "guaranteed profit" sales pitches, scam coins and fake investment platforms**.
Most of them rely on the same trick: using **survivorship bias** and **cherry-picked screenshots**
to make you believe there is a sure-win shortcut.

The name "Anti-Gambling Trader" (literally "Anti-Fraud Investment King" in Chinese) is not for show —
the real reason this tool exists is to **use statistics and mathematics to expose these schemes**.
What scams fear most is you calmly putting their promises to a mathematical test.

```bash
# 貼上群組對話，掃描詐騙話術（不給假百分比，只給風險等級）
anti-gambling-trader scan-text "老師帶單保證獲利，快加VIP客服"

# 檢驗老師的宣稱：「勝率90%、月報酬20%」純靠運氣出現的機率是多少？
anti-gambling-trader guru-check --win-rate 0.9 --trades 10 --monthly-return 0.2

# 用數學算出「連贏10次的神人」有多容易靠運氣出現
anti-gambling-trader survivorship

# 鑑識老師/平台宣稱的報酬序列是否有可疑徵兆（過度平滑、高得可疑的夏普）
anti-gambling-trader forensics --file 老師的月報酬.txt

# 互動式自我檢測
anti-gambling-trader scam-check
```

See the **[anti-scam guide docs/anti-scam.md](docs/anti-scam.md)** and the **[FAQ](docs/faq.md)** (both in Traditional Chinese).

> 🆘 **Suspect you are being scammed right now?** Stop transferring money immediately, call the
> **165 anti-fraud hotline**, or visit the [165 anti-fraud portal](https://165.npa.gov.tw).
> To verify licensed operators: [金管會證期局 (FSC Securities and Futures Bureau)](https://www.sfb.gov.tw);
> for securities/futures dispute assistance: [投保中心 (SFIPC)](https://www.sfipc.org.tw).
> (Official links last verified: 2026-07)
> *Note for non-Taiwan readers: 165 is Taiwan's national anti-fraud police hotline, and the
> 金管會 (Financial Supervisory Commission, FSC) is Taiwan's financial regulator.*
> This tool is a statistical aid, **not forensic evidence for legal proceedings**; official channels always come first.

---

Supports **Taiwan stocks / US stocks / crypto**, imports trade records from **CSV / JSON / Excel**, and automatically:

- Computes **win rate, payoff ratio, expectancy, profit factor, max drawdown, Sharpe / Sortino**
- Uses **statistical significance testing (t-test + bootstrap)** to judge "edge or luck"
- Uses **out-of-sample validation** to expose overfitting and survivorship bias
- Scans for **gambling warning signs** (small wins / large losses, profits overly concentrated in a few trades, long losing streaks, pure day trading…)
- **Per-strategy checkup**: descriptive statistics for each of your approaches (breakout / dip buying / tips from others…), pinpointing **which one is giving money away**
  (deliberately does not certify individual strategies as "edges" — uncorrected multiple comparisons would mistake luck for edge; see the methodology)
- **Counterfactual analysis**: computes "what the overall result would look like if you dropped your worst approach"
- **Break-even numbers**: tells you "what win rate / payoff ratio you would need for expectancy to turn positive"
- **Anti-fraud detection**: isolates the "guru-following / copy-trade" trades and computes their expectancy separately — testing with your own numbers whether following the calls actually pays
- **Risk scenario simulation**: simulates future paths from your own P&L distribution to see what fraction of paths blow up the account
- **Time trends**: monthly reports and edge-decay detection ("your expectancy turned negative in the last three months")
- **HTML report + shareable card**: black-and-white numbers you can save, screenshot and send to family
- Reverse-engineers your trading logic into a **backtestable strategy skeleton** (backtrader / vectorbt / generic)
- If the verdict is **not suited to long-term investing, it explicitly talks you out of it**

Supported markets: Taiwan stocks, Taiwan ETFs, **TAIEX futures / options (with contract multipliers)**, US stocks, crypto, **forex**.

## Why this exists

Most retail traders lose money because they mistake "good luck" for "skill" —
and fraud rings exploit exactly this cognitive weakness, harvesting you with fake groups, fake gurus and fake screenshots.
A stretch of paper profits is often statistically indistinguishable from "pure luck". The sole purpose of this tool
is to **let the math tell you the truth** before you lose more money or get harvested by a scam.

## Installation

The core engine is **pure Python standard library, zero external dependencies**.

```bash
git clone https://github.com/mars-tw/anti-gambling-trader-tw.git
cd anti-gambling-trader-tw
pip install -e .            # 安裝本體（之後可用 anti-gambling-trader 指令）

# 以下為可選依賴：
# pip install openpyxl       # 只有要讀 Excel (.xlsx) 才需要
# pip install backtrader     # 只有要實際跑回測骨架才需要（或 vectorbt）
```

Requirements: Python 3.10+. Run all commands from the project root (the directory containing `core/`);
on macOS / Linux, if `python` points to Python 2, use `python3` instead.

## Quick start (30 seconds)

```bash
# 0. 還沒有自己的資料？一行指令立刻看效果：
python -m core.cli demo               # 看「賭博型」範例
python -m core.cli demo --edge        # 看「具優勢」範例

# 1. 不知道資料格式？產生一份空白範本照填：
python -m core.cli init-template      # 產生 trades_template.csv

# 2. 分析你自己的資料（市場會自動推斷）：
python -m core.cli analyze 你的交易.csv

# 3. 欄位自動辨識失敗？手動指定對應：
python -m core.cli analyze 你的交易.csv --field symbol=代號 --field entry_price=買價

# 進階：輸出 JSON 結果與策略骨架
python -m core.cli analyze --example us --json result.json --strategy my_strategy.py
```

After installing the package, every `python -m core.cli` above can be replaced with the shorter `anti-gambling-trader`.

> If Chinese characters / emoji render incorrectly in a Windows terminal: in PowerShell run `$env:PYTHONUTF8=1` first, then run the command;
> on macOS / Linux, prefix the command with `PYTHONUTF8=1`.

## Input format

Column names are **auto-detected, in Chinese or English**. At minimum you need enough information to compute per-trade P&L:
(symbol + entry price + exit price + quantity) or (symbol + pnl).

| Standard field | Accepted column names (partial examples) | Required? |
|----------|--------------------------|--------|
| symbol | 代號 / ticker / 股票代號 / pair | Required |
| side | 方向 / 買賣 / side / long_short | Optional (defaults to long) |
| entry_time / exit_time | 進場時間 / 出場時間 / open_time | Recommended |
| entry_price / exit_price | 進場價 / 出場價 / 買價 / 賣價 | Either these or pnl |
| quantity | 數量 / 股數 / 張數 / qty | Either these or pnl |
| fees | 手續費 / 費用 / commission | Optional (estimated automatically if missing) |
| pnl | 損益 / 盈虧 / 已實現損益 / profit | Either this or prices |
| tag | 策略 / strategy / 進場理由 | Optional (strongly recommended) |

> **Strongly consider filling in `tag` (strategy label)**: the tool computes win rates for each approach separately,
> helping you see "which approach actually works and which one is just giving money away".

## The five verdict levels

| Level | Meaning | Discouragement |
|------|------|------|
| 🟥 `gambling` | Sample expectancy is negative — with the method unchanged, the long-run statistical expectation is a loss | ✅ Strongly discouraged |
| 🟧 `insufficient` | Sample too small to distinguish skill from luck | ✅ Discouraged from sizing up |
| 🟨 `luck_suspected` | Profitable on paper, but statistically looks like luck | ✅ Highly doubtful |
| 🟨 `fragile_edge` | A statistical signal exists but the structure is fragile and high-risk | ✅ Caution |
| 🟩 `statistical_edge` | Positive expectancy that passes significance testing (out-of-sample validation reported separately) | ❌ Not discouraged (still no guarantee) |

## How it separates "edge" from "gambling"

1. **Expectancy**: average win/loss per trade. **A negative *true* expectancy means a long-run loss in expectation (by mathematical definition);**
   **a negative *sample* expectancy is "treated as gambling until shown otherwise" (a conservative principle) — it is an estimate, so the verdict comes with uncertainty tests attached.**
2. **Significance testing**: t-test + centered bootstrap (shift method) resampling; only when both give p < 0.05 does it count as "not luck". The p-value = "the probability of results this good arising by pure luck if there were no edge", not "the probability that an edge exists". Deliberately conservative.
3. **Out-of-sample validation**: trades are split at a single chronological cut into an earlier segment (about 70%, in-sample) and a later segment (about 30%, out-of-sample); if the edge in the earlier segment disappears in the later one → overfitting / survivorship bias.
4. **Gambling-pattern scan**: negative expectancy, results propped up by one outsized win, small wins / large losses, extreme drawdowns, long losing streaks, pure day trading…

## Build your own trading program

Beyond the single-file strategy skeleton, this tool can also use an **interactive scaffold**
to generate a complete, runnable personal trading-program project for you.

```bash
# 1. 先挑圖表樣式（四種開源圖表庫並排預覽）
python -m core.cli chart-preview          # 產生 chart_preview.html，用瀏覽器打開挑選

# 2. 看看有哪些券商 / 圖表可選
python -m core.cli brokers
python -m core.cli charts

# 3. 產生專案（建議帶 --from-analysis 先驗證，把裁決嵌入專案）
python -m core.cli scaffold --name my_bot --broker binance --chart lightweight \
    --market crypto --symbols "BTCUSDT,ETHUSDT" --from-analysis my_trades.csv

# 4. 跑起來（預設紙上模擬，不碰真錢）
cd my_bot && pip install -r requirements.txt && python main.py
```

**Available brokers** (you connect the API yourself, filling in keys and the order implementation; run the `brokers` command for the full list):

| key | Broker | Market |
|-----|------|------|
| `paper` | Paper trading (default; fully functional, no real money) | All |
| `shioaji` | SinoPac Shioaji | Taiwan stocks |
| `yuanta` | Yuanta SPARK API | Taiwan stocks / futures |
| `fubon` | Fubon Next-Gen API | Taiwan stocks / sub-brokerage |
| `kgi` | KGI SUPER PY | Taiwan + US stocks |
| `tw_futures` | Capital / President / Masterlink futures-style | Taiwan futures |
| `ibkr` | Interactive Brokers | US stocks / global |
| `alpaca` | Alpaca | US stocks |
| `tradier` | Tradier (REST API) | US stocks |
| `binance` | Binance | Crypto |
| `okx` | OKX | Crypto |
| `bybit` | Bybit | Crypto |
| `ccxt` | ccxt (one interface for 100+ exchanges) | Crypto |

> Most Taiwan broker APIs require signing a risk-disclosure statement in person and an application review
> (often several business days); some require installing certificates or components. Each template's notes flag the key
> prerequisites, but the broker's official documentation is authoritative.

**Available open-source chart libraries**: `lightweight` (TradingView, Apache-2.0), `plotly` (MIT),
`mplfinance` (BSD), `echarts` (Apache-2.0).

### Three-layer safety design (protecting your money)

1. **Paper trading by default**: generated projects default to `PaperBroker`, which fully simulates matching without touching real money.
2. **Live-order safety gate**: orders to a real broker are blocked unless you personally call
   `confirm_live_trading(i_understand_the_risk=True)` AND change `ALLOW_LIVE_TRADING`
   to `True` in `main.py`.
3. **Verdict linkage**: if your trade history is judged to be gambling, the generated project **disables live trading by default**.

> This tool generates code to help you, but it will **never place real-money orders for you, never fill in your API keys,
> and never disarm the safety gate for you**. Real financial trading must be performed by you, at your own full responsibility.
> Automating unverified gambling only loses money faster.

## Project structure

```
core/
  models.py            # 統一資料模型（Trade / TradeLog，含契約乘數）
  markets.py           # 市場規格：契約乘數白名單、代號辨識、槓桿標註
  analyzer.py          # 高階一行式進入點
  cli.py               # 命令列介面（14 個指令）
  report.py            # 中文文字報告
  report_html.py       # HTML 報告 + 分享圖卡（XSS 安全、自包含）
  ingest/              # 匯入層：CSV/JSON/Excel 自動辨識 + 各市場成本模型
  metrics/             # 績效指標（performance / breakeven 轉正數字）
  verdict/             # 統計裁決引擎 + 顯著性檢定（真正的 t 分布，純標準庫）
  strategy/            # 交易模式反推 + 策略骨架 + per_tag 描述統計/反事實/跟單抽算
  backtest/            # 樣本外驗證（holdout_validate）
  trend/               # 時間趨勢：月報彙總 + 優勢衰減偵測（單一固定切點，防 p-hacking）
  montecarlo/          # 風險情境模擬：爆倉比例、最壞回撤、連虧機率
  survivorship.py      # 倖存者偏差模擬器（精確 DP，非模擬近似）
  forensics/           # 假績效統計鑑識（runs test / Lo 校正夏普 / 尾數卡方）
  antiscam/            # 反詐核心：特徵庫 + scam-check + 話術偵測 + 假老師驗證器
  broker/              # 券商抽象層 + PaperBroker + 12 種券商範本（共 13 種券商選項）
  charts/              # 四種開源圖表庫範本 + 樣式預覽
  scaffold/            # 個人交易程式專案產生器（產出自包含 broker_lib）
.claude/skills/anti-gambling-trader/SKILL.md   # Claude Code 技能包裝
core/examples/       # 三市場範例資料(隨套件打包,pip 安裝後 demo 仍可用)
tests/                 # 12 個測試檔，206 個測試
```

> **Things we deliberately do not do**: no Benford's-law test (returns include negatives and do not span
> orders of magnitude, so the premise does not hold), no uncalibrated fake percentages like "87% likely a scam",
> no Kelly position-sizing advice, no "confidence" gauges, no future-return projections.
> See the [methodology](docs/methodology.md) (in Traditional Chinese).

## Tests

```bash
# 用 pytest 一次跑全部（推薦）
python -m pytest tests/ -v

# 不裝 pytest 時，每個檔有內建執行器，需逐一執行：
python tests/test_core.py
python tests/test_trading_tools.py
python tests/test_antiscam.py
python tests/test_usability.py
python tests/test_engine.py
python tests/test_debate_fixes.py
python tests/test_trend.py
python tests/test_expansion.py
python tests/test_skill_round.py
python tests/test_round7.py
python tests/test_round8.py
```

## Author

好棒棒反詐協會 - 免費顧問 阿軒割割
(roughly: "the 'Awesome Anti-Fraud Association' — free consultant 'A-Hsuan the Cutter'", a tongue-in-cheek community handle)

> Honesty statement: the byline above is a community pseudonym, and the "好棒棒反詐協會" is **not** a registered
> legal entity or official organization. This project's credibility does not come from titles; it comes from:
> public source code, reproducible experiments (`experiments/`, fixed seeds), the
> [full methodology](docs/methodology.md), and 206 automated tests.
> Anyone is welcome to examine and challenge it — which is exactly what this tool asks the "gurus" to do.

## License

MIT License — open source, free to use. See [LICENSE](LICENSE).

## ⚠️ Disclaimer

This tool is for **statistical analysis and education**; its output **does not constitute investment advice of any kind**.
Investing involves risk, and profits and losses are your own. Past performance does not indicate future results.
The author accepts no responsibility for decisions anyone makes based on this tool, or for their consequences.

For the full disclaimer, see [DISCLAIMER.md](DISCLAIMER.md).
