# 2026-10-08 TWSE official-close audit

GitHub Actions run 37772309794 obtained TWSE official daily data. For 2330 on 2026-03-31, the official closing price was 1760, but the archived last five-minute bar at 13:25 closed at 1765. Data gate: FAIL.

Five predeclared stocks (2330, 2317, 2881, 2603, 1519) across three months gave 60 matched stock-days: 42/60 archived last-bar closes disagreed with official closes. All 60 had volume differences over 10% (median absolute relative difference 20.53%). The archive's 09:00 bars reported zero volume on about 94%-95% of sampled days. Differences in volume scope require further research; they do not alone establish corruption.

Workflow changed: ordinary pushes now run data-quality audits only; old contaminated backtests require explicit manual opt-in. No new trading edge is confirmed. Independent minute data, point-in-time universe, corporate actions, next-bar execution, and genuinely unseen OOS remain unresolved.

Evidence: https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/37772309794
