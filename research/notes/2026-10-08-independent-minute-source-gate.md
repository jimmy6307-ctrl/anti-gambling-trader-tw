# 2026-10-08 — 獨立分 K 資料來源可行性與品質關卡（研究，不是交易訊號）

## 先前研究狀態（延續既有日誌）

目前沒有通過樣本內、真正未見樣本外、交易成本與集中度檢驗的台股短線／波段策略。2025-04～2026-04 已多次檢視，**不得再宣稱乾淨 OOS**。舊版 5 分 K 最後棒與 13:30 官方收盤不一致，任何以前收盤、均線、新高、出場價為基礎的漂亮績效都只可作反證，不可當成可下單的優勢。

## 2026-10-08 查核到的獨立來源（文件證據；尚未取得付費原始資料）

1. **TWSE 官方日成交**：`https://www.twse.com.tw/rwd/zh/afterTrading/STOCK_DAY?date=20260301&stockNo=2330&response=json`。逐月逐股官方 OHLCV 可作日收盤與日量錨點；官方資訊服務說明集中市場一般交易時段為 09:00～13:30。注意日成交量與純盤中分 K 的範圍可能不同，不能以量差直接判定資料損壞。
   - 官方介紹：https://www.twse.com.tw/zh/products/information/information.html
   - 官方 OpenAPI：https://openapi.twse.com.tw/
2. **Fugle 股票 Historical Candles**：官方文件明列 **1/3/5/10/15/30/60 分 K**，股票分 K **自 2023-05-23** 起，日期區間可查；需 `X-API-KEY`。這與玉山證券介面文件「分 K 只回近 5 日」的限制不同，不能混為一談。日 K 可用 `adjusted`，但分 K 的 `adjusted` 不適用。
   - https://developer.fugle.tw/docs/data/http-api/historical/candles/
   - https://developer.fugle.tw/docs/data/http-api/getting-started/
   - https://www.esunsec.com.tw/trading-platforms/api-trading/docs/market-data/http-api/historical/candles/
3. **FinMind `TaiwanStockKBar` / `TaiwanStockPriceTick`**：分 K 個股涵蓋 **2019-01-01～現在**，但 `TaiwanStockKBar` 僅 sponsor；一次查單一交易日；逐筆資料另有權限與資料量限制。分 K 的 `volume` 上市/上櫃為**張**，興櫃為**股**，必須按當時市場別正規化。歷史 `TaiwanStockInfo` 轉板有重複市場別，不能用當前市場別回填歷史。
   - https://finmind.github.io/tutor/TaiwanMarket/Technical/
   - 2026-10-05 修正公告：https://finmind.github.io/WhatIsNew/ （2020～2023 部分重複逐筆／14:30 假成交列已重製；曾下載者需重新抓）
4. **TWSE Data E-Shop**：提供官方歷史**成交檔、委託檔、揭示檔**訂購，可作權威逐筆基準，但有授權與費用，不能假設免費可取得。
   - https://www.twse.com.tw/zh/products/dataeshop.html

## 執行門檻（資料通過前禁止策略優勢宣告）

- A. 官方日線核對：預先指定 2330、2317、2881、2603、1519；2024-08、2025-10、2026-03、2026-04 各取數個固定交易日，**強制含 2026-03-31 的 2330**，對比來源當日最後棒收盤價、開高低與成交量。官方 13:30 收盤價是唯一日線錨點。
- B. 分 K 獨立對照：至少兩個來源（舊 CSV + Fugle/FinMind/官方成交檔）同一天 09:00、09:05、09:30、13:20、13:25、13:30；確認時間戳是**棒首或棒末**、是否含收盤集合競價、無成交棒如何填值、是否缺失。
- C. 每個訊號在**可觀測資訊完成後**才下單：下一根可成交 K 棒開盤價；停牌、漲跌停、零量、低流動性不可硬假設成交。
- D. 日線均線／突破採官方價與權息事件一致口徑；不能把「還原後歷史」與「實際可成交價格」混用。
- E. 股票池需按**當日已上市/上櫃**狀態重建，包含後來下市者；持倉跨日占用、同日多檔同向相關性、重疊訊號、交易成本與滑價一併計算。
- F. 凍結規則後，只能用**尚未研究的新增時間區間**或預先保留的獨立資料做 OOS；2025-04～2026-04 只作已污染探索期。

## 本輪實際進度與阻礙

已核實獨立來源的公開文件、更新公告與取得限制；未取得 Fugle API key、FinMind sponsor 授權或官方逐筆成交檔，因此**尚未能做逐筆／分 K 的獨立數值交叉驗證**。研究環境對 TWSE 官方 API 的直接網路請求失敗（DNS/存取限制），不能假裝已完成官方比對。下一輪優先使用可聯網的研究 runner 執行官方日線抽樣對帳，保存原始回應、取得時間、來源版本、差異 CSV 與資料品質報告。不得再盲目重跑舊策略。

**裁決：DATA GATE BLOCKED；NO CONFIRMED EDGE；不通知使用者。**
