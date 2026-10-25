# 2026-10-08 — 官方收盤撮合與新資料隔離

證交所官方文件確認 09:00–13:25 逐筆撮合、13:25–13:30 僅接受委託，13:30 集合競價決定收盤價，必要時延後至 13:33。舊 5 分 K 最後一棒不能當正式收盤價，也不能僅憑時間戳判定棒首/棒末。來源：https://www.twse.com.tw/zh/about/company/guide.html 及 https://shl.twse.com.tw/page/library/trade/2.html。

新增 research/tw_official_daily_quarantine.py：擷取 2330、2317、2881、2603、1519 在 2026-04 至 2026-09 的 TWSE 官方日線；保存原始回應、SHA256、擷取時間、OHLC 檢查與錯誤。接入現有 source quality audit，輸出至 research_output/tw_source_quality/official_daily_2026。新增資料只作品質錨點，不拿來調參數或計算策略績效。

仍缺獨立分 K/逐筆、權息、歷史股票池、下一棒可成交價、資金占用、真正封存樣本外。DATA GATE BLOCKED；NO CONFIRMED EDGE；不通知使用者。

## 執行結果（GitHub Actions）

2026-10-08 官方日線擷取成功：30/30 個股票月份，620 筆股票交易日；資料驗證標記 PASS_OFFICIAL_DAILY_ONLY，未發現請求或解析錯誤。完整原始回應、SHA256、擷取時間與 CSV 保留在品質證據 artifact。執行：https://github.com/jimmy6307-ctrl/anti-gambling-trader-tw/actions/runs/37781401605 。這僅表示官方日線錨點取得成功，不代表分 K 或策略品質通過。仍維持 DATA GATE BLOCKED 與不通知。
