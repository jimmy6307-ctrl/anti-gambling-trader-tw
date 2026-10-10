# 台股策略研究假說（2026-09-16）

本檔只記錄下一輪要驗證的假說，不代表已通過回測。

## 文獻交叉檢查後優先級

1. **52 週高點 / 中期動能 + 市場狀態**：台灣文獻顯示 52 週高點動能有歷史證據，但效果受市場狀態與時期影響；因此不能單獨當買點，下一輪加入大盤 regime filter。
2. **低週轉率贏家（early momentum）**：台灣研究多次指出低週轉率 winner 可能優於單純價格動能；這與上一輪『高 RVOL 追價』失敗方向相反，值得優先測。
3. **波動度縮放 momentum**：2026 年研究（1993-2025、含下市公司）指出 volatility scaling 對台灣 TS/CS momentum 的風險調整績效重要；下一輪可測固定風險部位，而不是每筆等權。
4. **產業動能只作輔助，不作核心**：舊台灣研究對產業效果證據不一致；保留為 filter / ranking feature，不再直接視為 edge。

## 凍結測試順序

A. 52-week-high proximity + 6M market uptrend + low turnover winner
B. 20/60-day first breakout + market uptrend + low/normal turnover（與 high RVOL 版本對照）
C. A/B 加 volatility-scaled position sizing

## 驗收

- 先用 IS 選單一規則，再一次性開 OOS。
- 扣完整交易成本。
- OOS PF > 1.2、平均淨報酬 > 0。
- 移除最大貢獻股票後仍為正且 PF 不崩潰。
- 月份分布不能只靠少數月份。
- 若上述任一核心條件失敗，標記淘汰，不事後微調 OOS 參數救結果。
