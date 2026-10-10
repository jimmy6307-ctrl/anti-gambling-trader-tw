# 2026-10-10 — TPEx second official endpoint crosscheck (data only)

No old strategy was rerun. No previously viewed period was treated as a clean holdout.

## Confirmed from latest completed GitHub Actions evidence

- Quality audit run 37933153124, job 113828576781, 2026-10-09 12:54–12:55 UTC: TWSE MI_INDEX four predeclared dates passed (1020, 1049, 1071, 1081; total 4221 listed security-days).
- In the same run the TPEx historical official daily parser passed all four dates (821, 837, 864, 873; total 3395 OTC security-days). A second run 37933145824 reproduced exactly the same four counts.
- Combined observations: 7616 across four sampled trading dates. These are NOT a full historical common-stock universe and do not establish an executable strategy.
- Quality-evidence artifact ID 11616199637; raw SHA256 and UTC fetch times are archived by the workflow. The TPEx step succeeded (not merely continue-on-error). The legacy strategy job was skipped.

## New independent-report anchor probe prepared

- Discovered TPEx historical per-stock monthly JSON endpoint `st43_result.php`, with `aaData` rows [ROC date, volume, turnover, open, high, low, close, ...], separately from the all-market daily report `stk_wn1430_result.php`.
- Added `research/tw_tpex_individual_anchor_gate.py` and synthetic contract tests; five **predeclared** OTC codes 3105, 5347, 6488, 8069, 8299 on 2026-10-07. Compare exact OHLC from monthly vs official same-day marketwide snapshot, preserving raw response, UTC fetch time and SHA256. No dynamic selection of convenient matching tickers.
- A second official TPEx report is an **official daily crosscheck**, not an independent minute/tick vendor. If one code is absent or the endpoint has changed, mark BLOCKED and investigate, not silently replace the code or tune the sample.
- New workflow step is quarantined and fail-closed. A successful CI job alone does not certify the probe; read its manifest/report.

## Remaining mandatory gates

Independent 1/5-minute or tick data (including 13:30 auction and bar timestamp semantics), as-of corporate actions, historical security types and exchange membership, next-tradable-bar fills, costs/volume/overlap, and genuinely untouched OOS. Do not calculate or advertise strategy edge until these pass.

**NO CONFIRMED EDGE. Do not notify user.**

## Live check outcome (2026-10-10, correction to prepared-probe status)

- GitHub Actions run **37966526624** executed the new probe. Its synthetic unit tests passed; **all five live per-stock calls failed**.
- Downloaded artifact **11633188139** and inspected actual raw bytes, not merely job status. Every response was a **TPEx-branded HTML `404` page** beginning `<!DOCTYPE html><html ...><title>404 - 證券櫃檯買賣中心</title>`, even though the HTTP request did not raise an HTTP error. The parser correctly rejected non-JSON; 0/5 anchors passed.
- Therefore historical `st43_result.php` documented in old tutorials is **not a verified live endpoint in October 2026**. This is an API migration/source-discovery failure, NOT evidence of a mismatch in official stock prices. Do not relabel 0/5 as passed or use third-party reprints as independent official anchors.
- Disabled repeated live calls to this known-dead endpoint in the CI workflow; kept parser contract tests and source file for reproducibility. Next work: identify a **current** official individual-stock historical report/API, verify response date and schema with one test before scheduling five anchors, or seek independent licensed data. The TPEx marketwide historical daily source remains independently verified for four dates.
- GitHub Actions overall job showed success because this exploratory step was `continue-on-error`; always read the data-gate **manifest**, not the workflow badge, to determine data quality.

**DATA GATE STILL BLOCKED; NO CONFIRMED EDGE. Do not notify user.**
