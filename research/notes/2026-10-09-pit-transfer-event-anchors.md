# 2026-10-09 — 歷史上市／上櫃板別事件與防止未來資訊洩漏（資料品質）

## 這輪新增、非重複的工作

既有四日 TWSE + TPEx 官方日線抽樣，已發現 6423、6589、5236 的板別變化；但四個日期不能告訴我們精確生效日。這輪找到了兩個有日期的事件錨點：

- **6423 億而得-創：2026-01-22 終止 TWSE 創新板上市**。TWSE 官方「終止上市公司」表列 115年01月22日；公司 2026-01-16 重大訊息亦載明同日起轉 TPEx 上櫃。這是板別轉換，**不是永久退市或歸零**。官方：https://www.twse.com.tw/company/suspendListingCsvAndHtml?lang=zh&type=html；公司公告轉載：https://tw.stock.yahoo.com/news/%E5%85%AC%E5%91%8A-%E5%84%84%E8%80%8C%E5%BE%97-%E5%89%B5%E6%99%AE%E9%80%9A%E8%82%A1%E8%82%A1%E7%A5%A8%E5%88%9D%E6%AC%A1%E4%B8%8A%E6%AB%83%E6%9A%A8%E7%B5%82%E6%AD%A2%E5%89%B5%E6%96%B0%E6%9D%BF%E8%B2%B7%E8%B3%A3%E6%97%A5%E6%9C%9F-084233340.html
- **6589 台康生技：2025-07-21 由 TPEx 轉 TWSE 上市**。TWSE 官方上市典禮日期與公司 2025-07-16 公告一致。官方：https://webpro.twse.com.tw/WebPortal/vod/103/2B367D96A28E-71ADDDF7-65D3-11F0-9965/；公司公告轉載：https://tw.stock.yahoo.com/news/%E5%85%AC%E5%91%8A-%E5%8F%B0%E5%BA%B7%E7%94%9F%E6%8A%80%E6%99%AE%E9%80%9A%E8%82%A1%E8%82%A1%E7%A5%A8%E4%B8%8A%E5%B8%82%E6%9A%A8%E7%B5%82%E6%AD%A2%E4%B8%8A%E6%AB%83%E8%B2%B7%E8%B3%A3%E6%97%A5%E6%9C%9F-124124625.html

這兩個事件均與先前官方四日市場快照出現的市場別吻合；**只驗證特定代號與日期，不能外推到所有歷史成分股**。5236 凌陽創新於 2026-07-16 轉板仍待找到同等強度官方生效公告，暫不納入確定事件表。

## 新增程式（研究 branch，不動 main）

- `research/tw_pit_exchange_gate.py`：以有來源的 **[起始日, 結束日)** 歷史板別區間為依據，拒絕同股票重疊板別、同日同市場重複、觀測市場不符、缺乏板別證據；保留非普通股標記。沒有證據的股票必須維持 UNKNOWN，不能用今天的市場別回填。
- `research/test_tw_pit_exchange_gate.py`：合成資料檢查 6423 轉板邊界、板別錯誤、重複、重疊及未知代號。先前本機完整原型 9 項合成測試通過；已提交的精簡版測試需再由 CI 驗證。
- `evidence_published` 是**事後蒐集資料的發表日期**，不能當成當時可得的交易訊號。歷史板別事實可事後核對，但任何「事先已知轉板」策略必須另驗證當時公告可得時間。

## 其他官方可用事件來源（待歷史覆蓋與實際格式驗證）

- TWSE 最近上市公司（含股票上市買賣日期）：https://data.gov.tw/dataset/11542
- TWSE 終止上市公司：https://data.gov.tw/en/datasets/11543
- TPEx 終止上櫃公司：https://www.tpex.org.tw/zh-tw/mainboard/listed/delisted.html
- TPEx 歷史暫停／恢復交易：https://data.gov.tw/dataset/48665
- TWSE 除權息預告：https://data.gov.tw/dataset/89748
- TPEx 除權息計算結果：https://data.gov.tw/dataset/11633

以上部分資料集可能只提供「近期或當日」而非完整歷史；不可因找到端點就宣稱可回補所有歷史事件。仍須保存來源原始檔、取得時間與 SHA256、處理停牌／下市／轉板及權息時點，並取得獨立分鐘／逐筆資料。

**裁決：僅完成兩檔轉板事件的日期錨點與離線驗證規格。全市場 PIT universe、獨立分鐘資料、集合競價、可成交價、資金配置與乾淨 OOS 仍 BLOCKED；NO CONFIRMED EDGE；不通知使用者。**
