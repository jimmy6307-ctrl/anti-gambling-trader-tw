"""命令列介面。

用法:
    python -m core.cli analyze trades.csv
    python -m core.cli analyze trades.csv --market tw_stock --framework vectorbt
    python -m core.cli analyze trades.csv --json out.json --strategy strat.py
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .analyzer import analyze_file
from .models import Market


def _force_utf8_stdout() -> None:
    """確保中文在各平台終端機正確進出(尤其 Windows cp950)。

    stdin 也必須處理:Windows 上管線餵入的 UTF-8 中文會被 cp950 解碼成亂碼,
    導致 `cat 對話.txt | scan-text` 的詐騙關鍵字**靜默漏抓**(判「低風險」)——
    對一個反詐工具,因編碼漏抓詐騙是最諷刺的失敗。只對非 tty 的 stdin 重設,
    不動互動輸入;errors='replace' 避免真的餵入非 UTF-8 位元組時直接崩潰。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is not None:
            try:
                reconfigure(encoding="utf-8")
            except (ValueError, OSError):
                pass
    try:
        if not sys.stdin.isatty():
            reconfigure = getattr(sys.stdin, "reconfigure", None)
            if reconfigure is not None:
                reconfigure(encoding="utf-8", errors="replace")
    except (ValueError, OSError):
        pass


def _broker_choices() -> list[str]:
    """scaffold --broker 的可選值:paper + 註冊表所有券商(動態取得)。"""
    from .broker import BROKER_TEMPLATES
    return ["paper"] + list(BROKER_TEMPLATES.keys())


def _examples_dir() -> Path:
    """用 __file__ 定位 examples/,不依賴使用者的 cwd。"""
    # examples 放在 core/ 套件內並透過 package-data 打包 ——
    # 否則 pip 安裝後 site-packages 上一層沒有 examples/,demo 與 --example 全壞。
    return Path(__file__).resolve().parent / "examples"


# 範例對照:--example 值 → (檔案, 市場)
_EXAMPLES = {
    "tw": ("tw_stock_gambling.csv", Market.TW_STOCK),
    "us": ("us_stock_edge.csv", Market.US_STOCK),
    "crypto": ("crypto_luck.json", Market.CRYPTO),
}


def _example_path(key: str) -> tuple[str, Market]:
    fname, market = _EXAMPLES[key]
    return str(_examples_dir() / fname), market


def _parse_field_overrides(fields: list[str] | None) -> dict[str, str] | None:
    """解析 --field 標準名=欄位名。格式錯誤回傳 None(已印錯誤)。"""
    if not fields:
        return {}
    out: dict[str, str] = {}
    for item in fields:
        if "=" not in item:
            print(
                f"錯誤:--field 格式應為『標準名=你的欄位名』,但收到 {item!r}。\n"
                "  例:--field symbol=代號 --field entry_price=買價",
                file=sys.stderr,
            )
            return None
        std, col = item.split("=", 1)
        out[std.strip()] = col.strip()
    return out


def _analyze_with_overrides(target, market_hint, args, field_overrides):
    """依是否有 field_overrides 選擇載入路徑,回傳 AnalysisResult。"""
    from .analyzer import analyze_log
    from .ingest.loader import load_trades

    if field_overrides:
        log = load_trades(
            target,
            market_hint=market_hint,
            auto_estimate_costs=not args.no_cost_estimate,
            field_overrides=field_overrides,
        )
        return analyze_log(log, framework=args.framework, n_bootstrap=args.bootstrap)
    return analyze_file(
        target,
        market_hint=market_hint,
        framework=args.framework,
        auto_estimate_costs=not args.no_cost_estimate,
        n_bootstrap=args.bootstrap,
    )


def _print_next_steps(result, args, target) -> None:
    """依裁決結果,動態提示使用者接下來能做什麼。"""
    print("\n" + "─" * 70)
    print("下一步:")
    v = result.verdict
    if v.should_discourage:
        print("  • 先別加碼、別借錢、別重押 — 你的策略還沒通過驗證。")
        if result.follow_guru is not None and result.follow_guru.expectancy < 0:
            print("  • 你有跟單 / 聽明牌的虧損 → 執行 anti-gambling-trader scam-check 檢測是否遇到詐騙。")
    else:
        print(f"  • 想把這套邏輯變成可回測程式?執行 "
              f"anti-gambling-trader scaffold --from-analysis {target}")
    extras = []
    if not args.strategy:
        extras.append("--strategy out.py(產生可回測策略骨架)")
    if not args.json:
        extras.append("--json out.json(存結構化結果)")
    if extras:
        print(f"  • 本次只顯示報告。可加:{' / '.join(extras)}")
    print("─" * 70)


def _cmd_demo(args) -> int:
    """零參數,跑內建範例立刻看效果。"""
    if getattr(args, "edge", False):
        path, market = _example_path("us")
        intro = "▶ 這是一個『具統計優勢』的範例(美股季線突破策略):"
    else:
        path, market = _example_path("tw")
        intro = "▶ 這是一個『賭博型』的範例(台股當沖追高 + 聽明牌):"
    print(intro)
    print(f"  資料:{path}\n")
    try:
        result = analyze_file(path, market_hint=market)
    except (ValueError, FileNotFoundError) as exc:
        print(f"錯誤:找不到內建範例({exc})。", file=sys.stderr)
        return 1
    print(result.text_report)
    print("\n" + "─" * 70)
    if getattr(args, "edge", False):
        print("想看『賭博型』範例的對照?執行  anti-gambling-trader demo")
    else:
        print("想看『具優勢』範例的對照?執行  anti-gambling-trader demo --edge")
    print("準備好分析自己的資料了?執行  anti-gambling-trader init-template  產生空白範本。")
    print("─" * 70)
    return 0


# 空白 CSV 範本:標準中文欄名 + 兩行範例 + 說明註解
_TEMPLATE_CSV = """\
代號,方向,進場時間,出場時間,進場價,出場價,數量,手續費,策略
# 說明:把下面兩行範例換成你自己的交易。一列 = 一筆「已平倉」交易。
# 方向填「買/做多」或「賣/做空」;時間可用 2025-01-03 或 2025/01/03。
# 數量:台股可填股數;若你的欄位是「張」請改欄名為「張數」(會自動 ×1000)。
# 手續費可留空(會自動估算);策略欄建議填你的進場理由,日後才能揪出哪招在送錢。
2330,買,2025-01-03,2025-02-10,1000,1080,1000,,季線突破
2317,買,2025-01-15,2025-01-15,210,205,2000,,聽明牌當沖
"""


def _cmd_init_template(args) -> int:
    """產生空白交易紀錄範本。"""
    out = Path(args.out)
    if out.exists():
        print(f"錯誤:{out} 已存在,為避免覆蓋你的資料,請改用 --out 指定別的路徑。",
              file=sys.stderr)
        return 1
    out.write_text(_TEMPLATE_CSV, encoding="utf-8-sig")
    print(f"✅ 已產生空白交易紀錄範本:{out}\n")
    print("下一步:")
    print(f"  1. 用 Excel 或記事本打開 {out},把範例換成你自己的交易。")
    print(f"  2. 存檔後執行:anti-gambling-trader analyze {out}")
    print("\n提示:以 # 開頭的是說明列,分析時會自動略過,可保留或刪除。")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="anti-gambling-trader",
        description="反詐投資王 — 用統計學判斷你的交易是優勢還是賭博",
    )
    sub = p.add_subparsers(dest="command", required=True)

    a = sub.add_parser("analyze", help="分析一份交易紀錄")
    a.add_argument("file", nargs="?", help="交易紀錄檔(.csv / .json / .xlsx)")
    a.add_argument(
        "--example",
        choices=["tw", "us", "crypto"],
        help="不用自己的資料,直接分析內建範例(tw 台股 / us 美股 / crypto 加密貨幣)",
    )
    a.add_argument(
        "--market",
        choices=[m.value for m in Market],
        default=None,
        help="若所有交易同屬一個市場,可指定以提升準確度",
    )
    a.add_argument(
        "--field",
        action="append",
        metavar="標準名=你的欄位名",
        help="手動指定欄位對應(自動辨識失敗時),可重複。"
             "例:--field symbol=代號 --field entry_price=買價",
    )
    a.add_argument(
        "--framework",
        choices=["backtrader", "vectorbt", "generic"],
        default="backtrader",
        help="產生策略骨架的框架(預設 backtrader)",
    )
    a.add_argument(
        "--no-cost-estimate",
        action="store_true",
        help="不要自動估算手續費/稅(不建議:忽略成本會高估獲利)",
    )
    a.add_argument("--json", metavar="PATH", help="把結構化結果寫成 JSON 檔")
    a.add_argument("--strategy", metavar="PATH", help="把策略骨架寫成 .py 檔")
    a.add_argument("--html", metavar="PATH", help="輸出自包含的 HTML 報告(可存檔分享)")
    a.add_argument(
        "--card", metavar="PATH", help="輸出分享圖卡 HTML(截圖傳給家人的鐵證)"
    )
    a.add_argument(
        "--bootstrap", type=int, default=5000, help="bootstrap 重抽次數(預設 5000)"
    )

    # ── scaffold:產生個人交易程式專案 ──
    s = sub.add_parser("scaffold", help="產生一套屬於你的交易程式專案")
    s.add_argument("--name", default="my_trading_bot", help="專案名稱")
    s.add_argument(
        "--broker",
        choices=_broker_choices(),
        default="paper",
        help="券商(預設 paper 紙上模擬,不碰真錢;用 brokers 指令看完整清單)",
    )
    s.add_argument(
        "--chart",
        choices=["lightweight", "plotly", "mplfinance", "echarts"],
        default="lightweight",
        help="圖表庫(用 chart-preview 先看樣式)",
    )
    s.add_argument(
        "--market",
        choices=[m.value for m in Market],
        default=None,
        help="主要市場(省略時會從標的代號自動推斷)",
    )
    s.add_argument(
        "--symbols", default="AAPL", help="標的代號,逗號分隔(如 AAPL,MSFT)"
    )
    s.add_argument(
        "--from-analysis",
        metavar="PATH",
        help="先分析這份交易紀錄,把裁決嵌入專案(勸退時預設禁用真實下單)",
    )
    s.add_argument("--out", default=".", help="專案輸出目錄(預設目前目錄)")

    # ── chart-preview:產生圖表樣式預覽 ──
    cp = sub.add_parser("chart-preview", help="產生四種圖表庫的樣式預覽 HTML")
    cp.add_argument("--out", default="chart_preview.html", help="輸出 HTML 路徑")

    # ── brokers / charts:列出可用選項 ──
    sub.add_parser("brokers", help="列出可接入的券商範例框架")
    sub.add_parser("charts", help="列出可用的開源圖表庫")

    # ── scam-check:投資詐騙風險自我檢測 ──
    sub.add_parser(
        "scam-check",
        help="互動式檢測你是否遇到投資詐騙(假飆股群/假名師/保證獲利/詐騙幣)",
    )

    # ── demo:零參數,一行看效果 ──
    d = sub.add_parser("demo", help="不用準備資料,一行指令立刻看分析效果")
    d.add_argument(
        "--edge",
        action="store_true",
        help="改看『具優勢』的範例(預設看『賭博』範例)",
    )

    # ── init-template:產生空白 CSV 範本 ──
    it = sub.add_parser(
        "init-template", help="產生一份空白交易紀錄範本(照填即可分析)"
    )
    it.add_argument(
        "--out", default="trades_template.csv", help="範本輸出路徑"
    )

    # ── scan-text:詐騙話術文字偵測 ──
    st = sub.add_parser(
        "scan-text", help="貼上群組對話 / 廣告文案,掃描詐騙話術特徵"
    )
    st.add_argument("text", nargs="?", help="要掃描的文字(省略則從標準輸入讀)")
    st.add_argument("--file", metavar="PATH", help="從檔案讀取文字")

    # ── guru-check:假老師績效驗證器 ──
    gc = sub.add_parser(
        "guru-check", help="檢驗老師宣稱的績效:純靠運氣出現的機率有多高?"
    )
    gc.add_argument("--win-rate", type=float, help="宣稱的勝率(0.9 = 90%%)")
    gc.add_argument("--trades", type=int, help="宣稱基於幾筆交易(沒有就無法檢驗)")
    gc.add_argument("--winning-months", type=int, help="宣稱連續獲利幾個月")
    gc.add_argument("--total-months", type=int, help="完整紀錄總共幾個月")
    gc.add_argument("--monthly-return", type=float, help="宣稱的月報酬(0.2 = 20%%)")
    gc.add_argument("--payoff-ratio", type=float, help="宣稱的盈虧比")
    gc.add_argument("--gurus", type=int, default=1000, help="市面上有多少人自稱老師")
    gc.add_argument(
        "--null-win-prob", type=float, default=0.5,
        help="虛無假設下的單次勝率(預設 0.5;若標的長期上漲可調高至 0.55~0.62)",
    )

    # ── survivorship:倖存者偏差模擬器 ──
    sv = sub.add_parser(
        "survivorship", help="用數學算出「連贏 N 次的神人」有多容易靠運氣出現"
    )
    sv.add_argument("--traders", type=int, default=1000, help="群組人數")
    sv.add_argument("--trials", type=int, default=20, help="每人預測幾次")
    sv.add_argument("--streak", type=int, default=10, help="宣稱的連勝次數")

    # ── forensics:假績效統計鑑識 ──
    fo = sub.add_parser(
        "forensics", help="鑑識老師/平台宣稱的報酬序列是否有可疑徵兆"
    )
    fo.add_argument(
        "returns", nargs="?",
        help="報酬序列,逗號分隔(如 0.02,0.03,-0.01)。0.02 = 2%%",
    )
    fo.add_argument("--file", metavar="PATH", help="從檔案讀取(每行一個報酬)")
    fo.add_argument(
        "--periods-per-year", type=int, default=12, help="一年幾期(月=12,日=252)"
    )

    # ── risk-sim:風險情境模擬 ──
    rs = sub.add_parser(
        "risk-sim", help="用你的損益分布模擬未來情境(爆倉比例、最壞回撤)"
    )
    rs.add_argument("file", nargs="?", help="交易紀錄檔")
    rs.add_argument("--example", choices=["tw", "us", "crypto"], help="用內建範例")
    rs.add_argument("--equity", type=float, help="起始權益(未給則粗估)")
    rs.add_argument("--future-trades", type=int, default=200, help="模擬未來幾筆")
    rs.add_argument("--paths", type=int, default=5000, help="模擬幾條路徑")

    # ── trend:時間趨勢分析 ──
    tr = sub.add_parser("trend", help="月報趨勢與優勢衰減偵測")
    tr.add_argument("file", nargs="?", help="交易紀錄檔")
    tr.add_argument("--example", choices=["tw", "us", "crypto"], help="用內建範例")

    return p


def main(argv: list[str] | None = None) -> int:
    _force_utf8_stdout()
    args = _build_parser().parse_args(argv)

    if args.command == "analyze":
        # 決定要分析哪個檔案:--example 範例 > 指定檔案 > 無檔案導流
        target = args.file
        market_hint = Market(args.market) if args.market else None
        if args.example:
            target, market_hint = _example_path(args.example)
        elif not target:
            print(
                "你還沒提供交易資料檔。\n"
                "  • 想先看效果?     執行  anti-gambling-trader demo\n"
                "  • 用內建範例分析?  加  --example tw|us|crypto\n"
                "  • 不知道格式?     執行  anti-gambling-trader init-template "
                "產生空白範本照填",
                file=sys.stderr,
            )
            return 1

        # 解析 --field 欄位覆寫
        field_overrides = _parse_field_overrides(args.field)
        if field_overrides is None:
            return 1

        try:
            result = _analyze_with_overrides(
                target, market_hint, args, field_overrides
            )
        except (ValueError, FileNotFoundError, ImportError) as exc:
            print(f"錯誤: {exc}", file=sys.stderr)
            return 1

        # 終端機輸出完整報告
        print(result.text_report)

        if args.json:
            Path(args.json).write_text(
                json.dumps(result.as_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"\n[已輸出 JSON 結果] {args.json}")

        if args.strategy:
            Path(args.strategy).write_text(result.strategy_code, encoding="utf-8")
            print(f"[已輸出策略骨架] {args.strategy}")
            if result.verdict.should_discourage:
                print(
                    "  注意:由於裁決為『應勸退』,骨架中的安全閘門預設為啟用 — "
                    "執行時會中止,逼你先把策略驗證好。"
                )

        if args.html:
            from .report_html import render_html_report

            Path(args.html).write_text(render_html_report(result), encoding="utf-8")
            print(f"[已輸出 HTML 報告] {args.html}(用瀏覽器打開)")

        if args.card:
            from .report_html import render_share_card

            Path(args.card).write_text(render_share_card(result), encoding="utf-8")
            print(f"[已輸出分享圖卡] {args.card}(用瀏覽器打開後截圖)")

        # ── 下一步引導(讓使用者知道接下來能做什麼)──
        _print_next_steps(result, args, target)

        # 以裁決結果決定 exit code:勸退時回傳非 0,方便腳本判斷
        return 2 if result.verdict.should_discourage else 0

    if args.command == "demo":
        return _cmd_demo(args)

    if args.command == "init-template":
        return _cmd_init_template(args)

    if args.command == "scaffold":
        return _cmd_scaffold(args)

    if args.command == "chart-preview":
        from .charts import build_preview_page

        out = build_preview_page(args.out)
        print(f"✅ 圖表樣式預覽已產生:{out}")
        print("   用瀏覽器打開,挑一個你喜歡的樣式,再用 scaffold --chart <key> 產生專案。")
        return 0

    if args.command == "brokers":
        from .broker import list_brokers

        print("可接入的券商範例框架(scaffold --broker <key>):\n")
        print(f"  {'paper':10s} 紙上模擬 PaperBroker(預設,不碰真錢,完整可用)")
        for t in list_brokers():
            print(f"  {t.key:10s} {t.name}  [{t.market}]")
            print(f"  {'':10s}   安裝: {t.sdk_install}")
        return 0

    if args.command == "charts":
        from .charts import list_chart_libs

        print("可用的開源圖表庫(scaffold --chart <key>):\n")
        for lib in list_chart_libs():
            print(f"  {lib.key:12s} {lib.name}  [{lib.license}, {lib.kind}]")
            print(f"  {'':12s}   {lib.blurb}")
        return 0

    if args.command == "scam-check":
        from .antiscam import run_scam_check

        result = run_scam_check()
        # 高風險時回傳非 0,方便腳本判斷
        return 2 if result.risk_level in ("極高", "高") else 0

    if args.command == "scan-text":
        return _cmd_scan_text(args)

    if args.command == "guru-check":
        return _cmd_guru_check(args)

    if args.command == "survivorship":
        from .survivorship import guru_illusion, render_guru_illusion

        g = guru_illusion(
            n_traders=args.traders, n_trials=args.trials, streak=args.streak
        )
        print(render_guru_illusion(g))
        return 0

    if args.command == "forensics":
        return _cmd_forensics(args)

    if args.command == "risk-sim":
        return _cmd_risk_sim(args)

    if args.command == "trend":
        return _cmd_trend(args)

    return 0


def _read_file_text(path_str: str) -> str | None:
    """讀文字檔,對散戶友善:自動處理 BOM 與 Big5/cp950,錯誤給人話而非 traceback。

    回傳 None 表示讀取失敗(錯誤訊息已印到 stderr,呼叫端直接 return 1)。
    """
    p = Path(path_str)
    try:
        # utf-8-sig 順便吃掉 Windows 記事本常見的 UTF-8 BOM
        return p.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="cp950")   # 台灣常見的 Big5 舊檔
        except (UnicodeDecodeError, OSError):
            print(
                f"錯誤:無法解讀 {path_str} 的文字編碼。"
                "請用記事本或 Excel 將檔案另存為 UTF-8 後再試。",
                file=sys.stderr,
            )
            return None
    except FileNotFoundError:
        print(f"錯誤:找不到檔案 {path_str}", file=sys.stderr)
        return None
    except OSError as exc:
        print(f"錯誤:無法讀取 {path_str}({exc})", file=sys.stderr)
        return None


def _read_text_input(args) -> str | None:
    """從參數 / 檔案 / 標準輸入取得文字。"""
    if getattr(args, "file", None):
        return _read_file_text(args.file)
    if getattr(args, "text", None):
        return args.text
    if not sys.stdin.isatty():
        return sys.stdin.read()
    return None


def _cmd_scan_text(args) -> int:
    from .antiscam.text_scanner import render_scan, scan_text

    text = _read_text_input(args)
    if not text:
        print(
            "請提供要掃描的文字。用法:\n"
            '  anti-gambling-trader scan-text "老師帶單保證獲利,快加VIP"\n'
            "  anti-gambling-trader scan-text --file 對話紀錄.txt\n"
            "  cat 對話.txt | anti-gambling-trader scan-text",
            file=sys.stderr,
        )
        return 1
    r = scan_text(text)
    print(render_scan(r))
    return 2 if r.risk_level in ("極高", "高") else 0


def _cmd_guru_check(args) -> int:
    from .antiscam.guru_claim import analyze_guru_claim, render_guru_claim

    a = analyze_guru_claim(
        claimed_win_rate=args.win_rate,
        claimed_trades=args.trades,
        claimed_winning_months=args.winning_months,
        total_months=args.total_months,
        claimed_monthly_return=args.monthly_return,
        payoff_ratio=args.payoff_ratio,
        n_gurus_in_market=args.gurus,
        null_win_prob=args.null_win_prob,
    )
    print(render_guru_claim(a))
    bad = a.verdict in (
        "宣稱自相矛盾", "宣稱在數學上不可能持續", "可由倖存者偏差解釋",
        "與純運氣無法區分",
    )
    return 2 if bad else 0


def _cmd_forensics(args) -> int:
    from .forensics import analyze_returns, render_forensics

    raw: str | None = None
    if args.file:
        raw = _read_file_text(args.file)
        if raw is None:
            return 1
    elif args.returns:
        raw = args.returns
    if not raw:
        print(
            "請提供報酬序列。用法:\n"
            "  anti-gambling-trader forensics 0.02,0.031,-0.005,0.028,...\n"
            "  anti-gambling-trader forensics --file 老師的月報酬.txt",
            file=sys.stderr,
        )
        return 1
    try:
        vals = [
            float(x.strip())
            for x in raw.replace("\n", ",").split(",")
            if x.strip() and not x.strip().startswith("#")
        ]
    except ValueError as exc:
        print(f"錯誤:報酬序列格式無法解析({exc})", file=sys.stderr)
        return 1

    f = analyze_returns(vals, periods_per_year=args.periods_per_year)
    print(render_forensics(f))
    return 2 if f.suspicion_level in ("高度可疑", "可疑") else 0


def _load_for_tool(args):
    """risk-sim / trend 共用的資料載入。"""
    from .ingest.loader import load_trades

    if getattr(args, "example", None):
        path, market = _example_path(args.example)
        return load_trades(path, market_hint=market)
    if not getattr(args, "file", None):
        return None
    return load_trades(args.file)


def _cmd_risk_sim(args) -> int:
    from .montecarlo import render_scenario, simulate_ruin_scenario

    try:
        log = _load_for_tool(args)
    except (ValueError, FileNotFoundError, ImportError) as exc:
        print(f"錯誤: {exc}", file=sys.stderr)
        return 1
    if log is None:
        print("請提供交易紀錄檔,或用 --example tw|us|crypto", file=sys.stderr)
        return 1

    pnls = [t.pnl or 0.0 for t in log]
    try:
        s = simulate_ruin_scenario(
            pnls,
            start_equity=args.equity,
            n_future_trades=args.future_trades,
            n_paths=args.paths,
        )
    except ValueError as exc:
        # simulate 的參數驗證訊息已是清楚的繁中,直接轉述,不給 traceback
        print(f"錯誤: {exc}", file=sys.stderr)
        return 1
    if s is None:
        print("交易筆數太少(< 10),無法做有意義的情境模擬。", file=sys.stderr)
        return 1
    print(render_scenario(s))
    return 2 if s.ruin_fraction > 0.1 else 0


def _cmd_trend(args) -> int:
    from .trend import analyze_trend, render_trend_text

    try:
        log = _load_for_tool(args)
    except (ValueError, FileNotFoundError, ImportError) as exc:
        print(f"錯誤: {exc}", file=sys.stderr)
        return 1
    if log is None:
        print("請提供交易紀錄檔,或用 --example tw|us|crypto", file=sys.stderr)
        return 1
    print(render_trend_text(analyze_trend(log)))
    return 0


def _cmd_scaffold(args) -> int:
    """處理 scaffold 指令:產生個人交易程式專案。"""
    from .scaffold import ScaffoldOptions
    from .scaffold.generator import write_project

    from .ingest.loader import infer_market

    verdict = None
    inferred_market = None
    inferred_symbols = None
    if args.from_analysis:
        try:
            result = analyze_file(args.from_analysis)
            verdict = result.verdict
            print(f"[已分析交易紀錄] 裁決:{verdict.headline}")
            if verdict.should_discourage:
                print("  → 專案將預設禁用真實下單,逼你先把策略驗證好。\n")
            # 從分析結果繼承市場與標的,使用者連 --market --symbols 都能省
            markets = [m for m in result.log.markets if m != Market.UNKNOWN]
            if markets:
                inferred_market = markets[0].value
            syms = sorted({t.symbol for t in result.log})[:5]
            if syms:
                inferred_symbols = syms
        except (ValueError, FileNotFoundError, ImportError) as exc:
            print(f"警告:分析交易紀錄失敗({exc}),改以無裁決方式產生。", file=sys.stderr)

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if inferred_symbols and args.symbols == "AAPL":
        symbols = inferred_symbols   # 使用者沒自訂 symbols 時,用分析來的

    # market 推斷優先序:--market 指定 > --from-analysis 繼承 > 從標的代號推斷
    market = args.market or inferred_market
    if market is None and symbols:
        market = infer_market(symbols[0]).value
        if market != "unknown":
            print(f"[自動推斷市場] 依標的 {symbols[0]} 判斷為:{market}\n")
    market = market or "us_stock"

    opts = ScaffoldOptions(
        project_name=args.name,
        broker=args.broker,
        chart=args.chart,
        market=market,
        symbols=symbols or ["AAPL"],
        verdict=verdict,
    )
    try:
        root = write_project(opts, args.out)
    except (ValueError, OSError) as exc:
        # ScaffoldOptions.validate() 的訊息已是清楚的繁中(非法專案名/標的),
        # 直接轉述而非丟 traceback 給散戶。
        print(f"錯誤: {exc}", file=sys.stderr)
        return 1
    print(f"✅ 個人交易程式專案已產生:{root}\n")
    print("下一步:")
    print(f"  cd {root}")
    print("  pip install -r requirements.txt")
    print("  python main.py            # 先用紙上模擬跑一遍(不碰真錢)")
    print("\n提醒:")
    print("  - 在 strategy.py 填入你的進出場規則(寫不出明確規則,本身就是警訊)。")
    print("  - 要接真實券商,填 brokers/ 下的範例框架,並承擔風險自負。")
    print("  - 真實下單預設被安全閘門封鎖,需明確解除。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
