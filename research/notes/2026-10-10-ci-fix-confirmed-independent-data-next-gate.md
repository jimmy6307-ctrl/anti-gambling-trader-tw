# 2026-10-10 — CI 修復複核、資料閘門與授權來源優先順序

**狀態：DATA GATE BLOCKED；STRATEGY BLOCKED；無確認交易優勢。** 本輪不重跑既有 25 檔 5 分 K，也不把已檢視的 2025-04～2026-04 稱為未見樣本外。

## 重新核對當前分支（2026-10-10 20:44～20:45 台灣時間）

- 分支 `backtest-intraday-bands-20260819` head `9c1d4d5741304e6149665d2fce91283fc48a50d2`；GitHub Actions runs `38053060385`、`38053056311` 均為 completed/success，`legacy_exploration` 為 skipped。
- `research/tw_auction_execution_gate.py` 已有 `signal_rows[0]["volume_lots"] <= 0` → `ValueError("signal bar has zero volume")`；此修正**確實已提交**，不能再沿用「未修復」的舊敘述。
- run `38053060385` job `114215933387` 的 auction contract **18/18 tests passed**，包括 `test_zero_volume_signal_bar_rejected`；09:35 bar-start 訊號 09:36 才可觀測，09:37 才是嚴格較晚的 indicative 候選。此測試只證明合成資料契約，並**非實際成交**。
- 同一 CI 中官方日線資料步驟回報 `PASS_OFFICIAL_DAILY_ONLY`（30/30 stock-months、620 stock-days）；TWSE marketwide 4/4 日期、4221 列。這些是**日線品質**成果，不是獨立分 K/逐筆通過。
- 舊 5 分 K 對官方 TWSE 日線的固定樣本依然是 320 stock-days 中 **241 日收盤不同、315 日成交量誤差超過 10%**。不能把舊來源的 09:35、前收、突破、出場價視為可執行且可信；成交量差異也可能含涵蓋範圍／集合競價／單位差異，尚未歸因，不能直接說全部為原始檔造假。
- GitHub Actions 整體成功只代表步驟完成；資料品質報告明確寫 `strategy_gate=BLOCKED`。無策略通過、無新 P&L。

## 可取得的獨立分鐘／逐筆來源（文件核對，非授權實測）

1. **Shioaji 官方歷史行情**：https://sinotrade.github.io/zh/tutor/market_data/historical/ 。文件列股票 Ticks/Kbars 歷史期間自 2020-03-02 起，單次 Kbars 查詢有期間限制；需合法帳戶憑證、查詢額度及實際 raw response。Shioaji `ts` 使用台灣 wall-clock 編碼的特殊慣例（參見既有 `2026-10-10-ci-zero-volume-and-shioaji-clock-contract.md`），不能直接以 UTC epoch 轉 +8 小時。
2. **Fugle 官方歷史 K 棒**：https://developer.fugle.tw/docs/data/http-api/historical/candles/ 。分 K 自 2023-05-23、ISO8601 `+08:00`；整股分 K volume 單位「張」、日 K 為「股」；須 `X-API-KEY`，無憑證不可聲稱已取得或驗證。
3. **TWSE E-Shop 歷史逐筆／委託簿**：https://eshop.twse.com.tw/en/category/main/41 。交易所列有付費盤中歷史交易／委託簿產品，可能用於少量日期的官方第三方錨點；價格與授權條件應以實際詢價／產品說明為準，不代表已購得。

## 下一輪必須做到

- 先查 branch 最新 CI 和原始 quality manifest；不得因綠色 badge 宣稱資料可交易。
- 若能合法取得 **同股票、同日期** 的 Shioaji ticks 與 Fugle 1m，事前固定 TWSE/TPEx 樣本與日期，保存 raw bytes、SHA256、擷取時間、來源與權限；逐筆對 09:35 timestamp、09:00 零量、13:30 收盤集合競價、volume 單位與交易範圍。
- 逐筆能證明訊號完成時間與實際下單時序前，`indicative_next_bar` 一律只作 ex-post diagnostic；不可升格為 fill。
- 官方 PIT 成分、除權息 as-of、完整交易成本、部位重疊、資金占用與真正未見 holdout 仍未齊；保持 BLOCKED，**不通知使用者交易策略**。
