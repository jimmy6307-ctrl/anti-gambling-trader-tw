# 2026-09-02 — trailing-edge regime gate

Goal: test an explicit regime-adaptation mechanism without using OOS to tune thresholds.

Frozen base signal: `B20_SECTOR_LOWEXT`, 09:35 entry, 5-day hold, 0.685% round-trip cost. To avoid multiple same-day signals dominating the meta filter, signals were equal-weighted to one daily return. Meta rule: enable new entries only when the mean net return of the latest 20 *completed/observable* signal-days is positive; require at least 10 observable prior signal-days. A conservative +10 calendar-day availability lag was used so the 5-trading-day outcome could not leak into the decision.

Results (daily equal-weight signal returns):

- IS base: 42 signal-days, avg -0.99%, PF 0.50.
- IS adaptive gate: only 6 enabled signal-days, avg -3.34%, PF 0.02. **Fail.**
- OOS base (diagnostic only after IS fail): 35 signal-days, avg +3.47%, PF 5.77.
- OOS adaptive gate (diagnostic only): 25 enabled signal-days, avg +4.20%, PF 6.52.

Decision: **rejected**. A trailing realized-edge switch does not rescue the weak 2024~early-2025 regime and actually makes the IS sample worse. The OOS improvement is not admissible evidence because IS failed first.

Implication for next run: do not keep tuning the trailing window or threshold. The next useful hypothesis should change the economic mechanism rather than optimize this gate—e.g. cross-sectional relative-strength/sector leadership with a slower weekly rebalance, or a market-neutral/relative formulation if the available data supports it.