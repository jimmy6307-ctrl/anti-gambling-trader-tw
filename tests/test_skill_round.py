# -*- coding: utf-8 -*-
"""技能層優化輪的回歸測試。

守住的教訓:
  1. 骨架編譯:_entry_logic_hint 曾硬編 8 格縮排,導致 9 種組合有 6 種
     產出 IndentationError 的骨架 —— 而且從來沒有測試真的去編譯過產出。
     這裡把 3 個內建範例 × 3 個框架全部產一次、全部 compile() 一次。
  2. --full 一鍵健檢:主報告後必須接月報趨勢與風險情境(或誠實的略過訊息),
     HTML 版必須帶「情境非預測」警語,不能只給數字。
  3. 下一步導流:沒帶 --full 時要主動告訴使用者 trend / risk-sim 的存在。
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.analyzer import analyze_file  # noqa: E402
from core.cli import _example_path  # noqa: E402
from core.strategy.skeleton import generate_skeleton  # noqa: E402

_FRAMEWORKS = ("backtrader", "vectorbt", "generic")
_EXAMPLE_KEYS = ("tw", "us", "crypto")


def _run_cli(*argv: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "core.cli", *argv],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        cwd=str(Path(__file__).resolve().parent.parent),
        env={"PYTHONUTF8": "1", "PYTHONIOENCODING": "utf-8",
             **__import__("os").environ},
        timeout=600,
    )


def test_all_skeleton_combos_compile():
    """3 範例 × 3 框架 = 9 種骨架,每一種都必須是合法 Python。"""
    for key in _EXAMPLE_KEYS:
        path, market = _example_path(key)
        result = analyze_file(path, market_hint=market, n_bootstrap=500)
        for fw in _FRAMEWORKS:
            code = generate_skeleton(result.profile, result.verdict, framework=fw)
            try:
                compile(code, f"<skeleton:{key}:{fw}>", "exec")
            except SyntaxError as e:  # pragma: no cover - 失敗時給可讀訊息
                raise AssertionError(
                    f"骨架無法編譯:example={key} framework={fw} — {e}"
                ) from e


def test_skeleton_entry_hint_indented_correctly():
    """進場提示在 backtrader 是 12 格、generic 是 4 格(曾經全錯成 8 格)。"""
    path, market = _example_path("tw")
    result = analyze_file(path, market_hint=market, n_bootstrap=500)
    bt_code = generate_skeleton(result.profile, result.verdict, framework="backtrader")
    ge_code = generate_skeleton(result.profile, result.verdict, framework="generic")
    assert "\n            signal = False" in bt_code, "backtrader 提示應為 12 格縮排"
    assert "\n    signal = False" in ge_code, "generic 提示應為 4 格縮排"


def test_analyze_full_appends_trend_and_risk():
    """--full 必須在主報告後接趨勢與風險情境;範例 tw 為賭博 → exit 2。"""
    with tempfile.TemporaryDirectory() as td:
        html = str(Path(td) / "full.html")
        p = _run_cli("analyze", "--example", "tw", "--full",
                     "--equity", "500000", "--html", html)
        assert p.returncode == 2, f"tw 範例應勸退(exit 2),得到 {p.returncode}"
        assert "時間趨勢" in p.stdout, "--full 缺少月報趨勢區塊"
        assert "風險情境模擬" in p.stdout, "--full 缺少風險情境區塊"
        h = Path(html).read_text(encoding="utf-8")
        assert "月報趨勢" in h, "--full --html 應包含趨勢區塊"
        assert "風險情境模擬" in h, "--full --html 應包含風險情境區塊"
        assert "不是「預測」" in h, "HTML 風險區塊必須帶「情境非預測」警語"


def test_analyze_without_full_suggests_trend_and_risksim():
    """沒帶 --full 時,下一步導流必須提示 trend 與 risk-sim 的存在。"""
    p = _run_cli("analyze", "--example", "tw")
    assert "trend" in p.stdout, "下一步應導流 trend"
    assert "risk-sim" in p.stdout, "下一步應導流 risk-sim"
    assert "--full" in p.stdout, "下一步應提示 --full 一次看完"


def test_html_without_full_has_no_extra_blocks():
    """沒帶 --full 時,HTML 保持精簡 —— 不得出現趨勢/風險區塊。"""
    with tempfile.TemporaryDirectory() as td:
        html = str(Path(td) / "plain.html")
        p = _run_cli("analyze", "--example", "tw", "--html", html)
        assert p.returncode == 2
        h = Path(html).read_text(encoding="utf-8")
        assert "月報趨勢" not in h
        assert "風險情境模擬" not in h


if __name__ == "__main__":
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for fn in fns:
        try:
            fn()
            print(f"  ✅ {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  ❌ {fn.__name__}: {e}")
    print(f"\n{len(fns) - failed}/{len(fns)} 通過")
    sys.exit(1 if failed else 0)
