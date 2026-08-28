# Automated Taiwan Strategy Research Journal

## 2026-08-28

Research discipline: include 0.685% round-trip cost; use 2024-03-01~2025-03-31 as IS and 2025-04-01~2026-04-01 as OOS; reject hypotheses that only become attractive after seeing OOS; require robustness after removing the largest contributing stock.

### Existing frozen tests

- 09:30 sector-strength + RVOL + gain-band approach: apparent best OOS-like one-year result (+2%~+7%, hold 5d) was heavily dependent on 2408; removing it reduced average net return to roughly flat. Rejected as a standalone entry rule.
- First 20-day breakout + trend + RVOL + sector breadth + <=2% extension, 09:35 entry: OOS was very strong (41 trades, avg +3.20%, PF 4.49; after dropping top contributor 1504: 39 trades, avg +2.42%, PF 3.51), but IS was negative (55 trades, avg -0.62%, PF 0.69). This is regime-sensitive / unconfirmed, not a valid strategy claim.
- Compression-breakout version: too few observations (IS 4, OOS 2), rejected.
- Intraday-confirmation version (gap <=1.5%, 09:00→09:35 gain >=0.5%): IS 39 trades, avg -0.31%, PF 0.81. Rejected before using OOS.
- Market-regime breakout versions using prior market trend thresholds: no version with adequate evidence passed IS; rejected.

### Additional hypotheses screened this run

Using the same 25-stock cached 5-minute universe, screened simple interpretable long-only families: 20/60-day relative-strength leaders, pullback-and-reclaim, MA20 reclaim, simple 20-day breakout, oversold rebound, uptrend dip, and market-breadth-filtered breakouts. The common pattern was poor/negative IS performance and much stronger OOS performance. This indicates a material regime shift between the two windows and means OOS strength must not be used to retrofit the rule.

Notable rejected example: market-breadth-filtered 20-day breakout with >=70% of the universe above MA60 and 5-day hold passed IS superficially (46 trades, avg about +1.01%, PF about 1.81) but failed OOS (24 trades, avg about -0.71%, PF about 0.71). This is a useful falsification: simply adding a strong-market filter does not solve regime dependence.

### Current conclusion

No strategy has yet met the notification standard across IS + OOS + concentration robustness. Continue searching, but prioritize mechanisms that can survive both the weaker 2024~early-2025 regime and the stronger 2025~2026 regime rather than optimizing for the latter.