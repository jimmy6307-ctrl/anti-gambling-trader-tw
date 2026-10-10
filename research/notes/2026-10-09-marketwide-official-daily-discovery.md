# 2026-10-09 — 官方全市場歷史日線來源擴充（僅品質研究）

## 已有證據（避免重複）

- 既有 25 檔 Yahoo 衍生 5 分 K 歷史最晚只到 2026-04-01，缺少正式收盤集合競價；2026-10-08 官方逐日核對 320 個股票交易日，241 筆最後棒收盤不等於官方收盤。舊策略回測不能視為可執行。
- 2025-04~2026-04 已多次檢視，不可重當乾淨 OOS。先前熱門、突破、拉回與跳空等假說皆未通過門檻。
- `voidful/tw_stocker` 舊專案／fork 文件明言來源是 Yahoo Finance，5 分鐘資料以 Yahoo 近 60 日為基礎累積。直接改用 Yahoo Finance/yfinance 再抓一份 **不是獨立分 K 來源**，不能算雙來源交叉驗證。來源：https://github.com/way503678/tw_stocker ；https://github.com/voidful/tw_stocker 。

## 新發現：可免費查詢歷史「當日全上市」的 TWSE 官方端點

`https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date=20261007&type=ALLBUT0999&response=json`

- 與 `STOCK_DAY`（每股每月）不同，`MI_INDEX` 的「每日收盤行情」表提供指定日期當日的全上市證券盤後 OHLCV、交易股數與筆數，能建立較大範圍的 **當時有成交上市股票日線觀測**。不能直接當成完整歷史股票池，因為不含上櫃、停牌無成交、已下市證券在其他日期的記錄；須另外取得上市異動與權息事件。
- 歷史查詢會有非交易日 HTTP 200 但 `stat != OK`，且 JSON `tables` 表位置曾變動；必須按標題及欄位名稱解析，不可硬用 `tables[8]`。參考：https://floviq.tw/articles/twse-holiday-api-behavior-layers/ 及 https://www.kbwen.com/2021/08/29/python-爬取每日股價1/ 。
- 已新增 `research/tw_marketwide_daily_gate.py` 與 `research/test_tw_marketwide_daily_gate.py`。固定抽樣 2024-08-05、2025-10-01、2026-03-31、2026-10-07；每個日期抓全上市當日成交快照，與同日 `STOCK_DAY` 的 2330 開高低收逐項核對，保存原始 JSON、SHA256、UTC 取得時間、CSV。嚴格拒絕日期錯置、表格欄位變動、重複代碼、OHLC 不合理、觀測數少於 900 或官方端點不一致。
- 本輪在無外網的本機環境不能向 TWSE 取回正式回應；新程式的實際遠端抓取 **尚未驗證成功**。先前 GitHub Actions runner 能連到 TWSE，後續應於該 runner 執行並保留 artifact。未宣稱已有新的官方全市場資料；程式只是品質關卡準備。

## 下一步硬限制

1. 先在可連 TWSE 的 runner 執行此全市場日線品質關卡，檢查原始回應與欄位；任何資料漂移都要 fail-closed。
2. 補上 TPEx 官方歷史當日收盤資料及上市／上櫃／停牌／下市時點紀錄，避免倖存者偏差；官方日線僅為價格錨點。
3. 獨立分 K／逐筆需不同上游（例如 Fugle 授權歷史行情或 Shioaji）；先核對時間戳、13:30 集合競價及下一根實際可成交價。
4. 權息一致化、成本、部位重疊與資金占用完成前，**不執行新策略績效認證**；新增 2026-04 後資料隔離，禁止為既有規則調參數。

**結論：DATA GATE BLOCKED；NO CONFIRMED EDGE；不通知使用者。**
