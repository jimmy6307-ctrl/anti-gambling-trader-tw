"""HTML 報告 + 分享圖卡 — 把分析結果變成可存檔、可傳給家人的鐵證。

用途:勸阻長輩跟單時,甩一張數據卡片比講一百句話有用。

安全與誠實的設計:
  - 所有動態內容一律 html.escape(quote=True),防 XSS。
  - **不畫「信心度儀表」**:p 值不是「優勢為真的機率」,把 1−p 畫成
    95% 信心度會與同頁的「信賴區間涵蓋 0」直接矛盾。改為直接呈現 CI 與原始 p。
  - **逐策略不發優勢徽章**:多重比較未校正會把運氣認證成優勢(見 per_tag)。
  - **不做未來報酬投射**:純外推正是詐騙話術本體。
  - 自包含、無外部資源(不載 CDN、不連網),可離線開啟。
"""

from __future__ import annotations

from html import escape as _esc


def h(x) -> str:
    """脈絡安全的跳脫(含引號,可放進屬性)。"""
    return _esc(str(x), quote=True)


def _equity_svg(pnls: list[float], width: int = 720, height: int = 220) -> str:
    """用 inline SVG 畫累積權益曲線(含最大回撤陰影)。零外部相依。"""
    if not pnls:
        return '<p class="muted">沒有交易資料可繪圖。</p>'

    equity, cum = [], 0.0
    for p in pnls:
        cum += p
        equity.append(cum)

    lo, hi = min(equity + [0.0]), max(equity + [0.0])
    span = (hi - lo) or 1.0
    pad = 20
    w, hgt = width - 2 * pad, height - 2 * pad

    def X(i: int) -> float:
        return pad + (i / max(1, len(equity) - 1)) * w

    def Y(v: float) -> float:
        return pad + (hi - v) / span * hgt

    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(equity))

    # 最大回撤區段(峰值 → 谷底)
    peak = equity[0]
    peak_i = 0
    best = (0.0, 0, 0)
    for i, v in enumerate(equity):
        if v > peak:
            peak, peak_i = v, i
        dd = peak - v
        if dd > best[0]:
            best = (dd, peak_i, i)
    dd_shade = ""
    if best[0] > 0:
        x1, x2 = X(best[1]), X(best[2])
        dd_shade = (
            f'<rect x="{x1:.1f}" y="{pad}" width="{max(1.0, x2 - x1):.1f}" '
            f'height="{hgt}" fill="#ef5350" opacity="0.12"/>'
        )

    zero_y = Y(0.0)
    return f"""<svg viewBox="0 0 {width} {height}" width="100%" height="{height}"
  role="img" aria-label="累積損益曲線">
  {dd_shade}
  <line x1="{pad}" y1="{zero_y:.1f}" x2="{width - pad}" y2="{zero_y:.1f}"
        stroke="#6b7280" stroke-dasharray="4 4" stroke-width="1"/>
  <polyline points="{pts}" fill="none" stroke="#2962ff" stroke-width="2"/>
</svg>
<p class="muted">紅色區塊 = 最大回撤區間;虛線 = 損益平衡點。</p>"""


def _verdict_color(level: str) -> str:
    return {
        "gambling": "#ef5350",
        "insufficient": "#f59e0b",
        "luck_suspected": "#eab308",
        "fragile_edge": "#eab308",
        "statistical_edge": "#26a69a",
    }.get(level, "#6b7280")


def render_html_report(result, *, title: str = "反詐投資王 — 交易績效誠實報告") -> str:
    """把 AnalysisResult 渲染成自包含 HTML。純 passthrough,不新增任何結論。"""
    v = result.verdict
    m = result.metrics
    oos = result.out_of_sample
    color = _verdict_color(v.level.value)

    # 逐策略表(只有描述統計,不發徽章)
    tag_rows = ""
    for tv in (result.tag_verdicts or []):
        note = "(樣本少)" if tv.low_sample else ""
        tag_rows += (
            f"<tr><td>{h(tv.tag)}</td><td class='num'>{tv.n_trades}</td>"
            f"<td class='num'>{tv.expectancy:,.2f}</td>"
            f"<td class='num'>{tv.total_pnl:,.2f}</td>"
            f"<td>{h(tv.descriptor)} {h(note)}</td></tr>"
        )
    tag_table = (
        f"""<h2>各策略體檢(描述統計)</h2>
<table><thead><tr><th>策略標籤</th><th>筆數</th><th>每筆期望值</th>
<th>總損益</th><th>狀態</th></tr></thead><tbody>{tag_rows}</tbody></table>
<p class="muted">刻意不對個別策略做「具優勢」認證 —— 對多個策略各做一次統計檢定,
會把運氣誤認成優勢(策略越多、誤判機率越高)。</p>"""
        if tag_rows else ""
    )

    # 跟單成績單
    guru = ""
    if result.follow_guru is not None:
        guru = (
            f'<h2>跟單 / 聽明牌的成績單</h2><div class="alert">'
            f"{h(result.follow_guru.message)}</div>"
        )

    # 樣本外(誠實措辭,不宣稱裁決含 OOS)
    oos_html = (
        f'<h2>樣本外驗證</h2><p>{h(oos.headline)}</p><ul>'
        + "".join(f"<li>{h(x)}</li>" for x in oos.interpretation)
        + "</ul>"
    )

    flags = "".join(
        f'<li><b>[{h(rf.severity)}]</b> {h(rf.message)}</li>' for rf in v.red_flags
    )
    flags_html = f"<h2>偵測到的警訊</h2><ul>{flags}</ul>" if flags else ""

    sig = v.significance
    pnls = [t.pnl or 0.0 for t in result.log]

    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{h(title)}</title>
<style>
:root{{color-scheme:dark}}
body{{margin:0;background:#0d0f14;color:#d1d4dc;
font-family:system-ui,"Microsoft JhengHei",sans-serif;line-height:1.7}}
.wrap{{max-width:820px;margin:0 auto;padding:24px}}
h1{{font-size:22px;margin:0 0 4px}}
h2{{font-size:16px;margin:28px 0 8px;border-bottom:1px solid #1e222d;padding-bottom:6px}}
.verdict{{background:#131722;border-left:5px solid {color};
padding:16px 18px;border-radius:8px;margin:16px 0}}
.verdict .lv{{color:{color};font-weight:700;font-size:18px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}
th,td{{padding:8px 10px;border-bottom:1px solid #1e222d;text-align:left}}
th{{color:#8b94a3;font-weight:500}}
td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px}}
.stat{{background:#131722;border:1px solid #1e222d;border-radius:8px;padding:12px 14px}}
.stat .k{{font-size:12px;color:#8b94a3}}
.stat .v{{font-size:19px;font-variant-numeric:tabular-nums;margin-top:2px}}
.alert{{background:#1a1310;border:1px solid #7f1d1d;border-radius:8px;padding:14px}}
.muted{{color:#6b7280;font-size:12px}}
.disclaimer{{margin-top:32px;padding-top:16px;border-top:1px solid #1e222d;
color:#6b7280;font-size:12px}}
</style></head><body><div class="wrap">

<h1>{h(title)}</h1>
<p class="muted">資料來源:{h(result.log.source)}</p>

<div class="verdict">
  <div class="lv">{h(v.level.badge)}</div>
  <div>{h(v.headline)}</div>
</div>

<h2>核心績效</h2>
<div class="grid">
  <div class="stat"><div class="k">交易筆數</div><div class="v">{m.total_trades}</div></div>
  <div class="stat"><div class="k">勝率</div><div class="v">{m.win_rate:.1%}</div></div>
  <div class="stat"><div class="k">盈虧比</div><div class="v">{m.payoff_ratio:.2f}</div></div>
  <div class="stat"><div class="k">每筆期望值</div><div class="v">{m.expectancy:,.2f}</div></div>
  <div class="stat"><div class="k">總損益</div><div class="v">{m.total_pnl:,.2f}</div></div>
  <div class="stat"><div class="k">最大回撤</div><div class="v">{m.max_drawdown_pct:.1%}</div></div>
</div>

<h2>累積損益曲線</h2>
{_equity_svg(pnls)}

<h2>這是優勢,還是運氣?</h2>
<table><tbody>
<tr><td>每筆平均損益</td><td class="num">{sig.mean:,.2f}</td></tr>
<tr><td>95% 信賴區間(雙尾)</td>
    <td class="num">[{sig.ci_low:,.2f}, {sig.ci_high:,.2f}]</td></tr>
<tr><td>t 檢定 p 值</td><td class="num">{sig.p_value_t:.4f}</td></tr>
<tr><td>Bootstrap p 值(單尾)</td><td class="num">{sig.p_value_bootstrap:.4f}</td></tr>
</tbody></table>
<p class="muted">我們刻意不把 1−p 畫成「信心度」儀表:p 值不是「優勢為真的機率」。
信賴區間是否涵蓋 0,才是更誠實的判讀方式。</p>

{flags_html}
{tag_table}
{guru}
{oos_html}

<div class="disclaimer">
本報告為統計分析工具的輸出,僅供教育與研究用途,<b>不構成任何投資建議</b>。<br>
投資有風險,盈虧自負。過去績效不代表未來表現。<br>
本報告不做任何未來報酬的投射 —— 那正是投資詐騙的話術本體。
</div>
</div></body></html>"""


def render_share_card(result, *, width: int = 600) -> str:
    """分享圖卡:一張可截圖傳給家人的鐵證卡片。"""
    v = result.verdict
    m = result.metrics
    color = _verdict_color(v.level.value)
    guru_line = ""
    if result.follow_guru is not None and result.follow_guru.expectancy < 0:
        guru_line = (
            f'<div class="guru">聽老師 / 跟單的 {result.follow_guru.n_trades} 筆交易,'
            f"合計 {result.follow_guru.total_pnl:,.0f}</div>"
        )

    return f"""<!doctype html>
<html lang="zh-Hant"><head><meta charset="utf-8">
<title>反詐投資王 — 分享圖卡</title>
<style>
body{{margin:0;background:#0d0f14;display:flex;align-items:center;
justify-content:center;min-height:100vh;font-family:system-ui,"Microsoft JhengHei",sans-serif}}
.card{{width:{width}px;background:#131722;border-radius:16px;padding:28px 30px;
border-top:6px solid {color};color:#d1d4dc;box-shadow:0 8px 40px rgba(0,0,0,.5)}}
.badge{{color:{color};font-size:24px;font-weight:800}}
.head{{margin:10px 0 18px;font-size:15px;line-height:1.6}}
.row{{display:flex;justify-content:space-between;padding:9px 0;
border-bottom:1px solid #1e222d;font-size:14px}}
.row b{{font-variant-numeric:tabular-nums}}
.guru{{margin-top:16px;padding:12px 14px;background:#1a1310;
border:1px solid #7f1d1d;border-radius:8px;font-size:13px;color:#fca5a5}}
.foot{{margin-top:18px;font-size:11px;color:#6b7280;line-height:1.6}}
</style></head><body>
<div class="card">
  <div class="badge">{h(v.level.badge)}</div>
  <div class="head">{h(v.headline)}</div>
  <div class="row"><span>交易筆數</span><b>{m.total_trades}</b></div>
  <div class="row"><span>勝率</span><b>{m.win_rate:.0%}</b></div>
  <div class="row"><span>盈虧比</span><b>{m.payoff_ratio:.2f}</b></div>
  <div class="row"><span>每筆期望值</span><b>{m.expectancy:,.0f}</b></div>
  <div class="row"><span>總損益</span><b>{m.total_pnl:,.0f}</b></div>
  {guru_line}
  <div class="foot">
    反詐投資王 · 用統計學判斷這是優勢還是賭博<br>
    本卡片為統計分析輸出,不構成投資建議。過去績效不代表未來表現。
  </div>
</div></body></html>"""
