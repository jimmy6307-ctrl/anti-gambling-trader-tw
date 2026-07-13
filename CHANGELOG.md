# 變更紀錄

本專案採 [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) 精神記錄重大變更。
每一輪修繕都經過多模型交叉審查(GPT 系 + Grok 系 + Claude)與對抗性驗證;
細節見各 commit 訊息。

## [Unreleased]

### Changed
- bootstrap p 值改為虛無假設置中重抽(shift method),修正「期望不為正的
  機率」的錯誤語意;型一誤差經蒙地卡羅校準(`experiments/`)
- 全庫清除絕對化/定罪式文案(未校準百分比、「必」字斷言、決定論措辭),
  統一為機率語氣與保守原則語意;新增 lint 測試防回歸
- 方法論引用的所有實驗數字改附固定 seed 重現腳本(`experiments/`)
- guru-check 複利歸謬改為「尺度示意」語意(GDP 為年度流量,非財富存量)
- 樣本外驗證報告明示前提:規則若看著全段歷史調整,結論會偏樂觀

### Added
- `docs/faq.md`:18 題答案先行的反詐與統計 FAQ
- `llms.txt`、`CITATION.cff`、`CONTRIBUTING.md`、`SECURITY.md`
- 官方求助資源連結(165 / 金管會證期局 / 投保中心,查核日期 2026-07)

## [0.1.0] - 2026-07-09(首次公開發布;此節為累計八輪多模型審查後的狀態)

### Added
- 統計裁決核心:期望值 / t 檢定 + bootstrap 雙檢定 / 樣本外驗證 /
  五級裁決(gambling → statistical_edge),勸退機制
- 反詐四件套:scan-text(話術掃描,支援簡體變體)、scam-check(互動問卷)、
  guru-check(宣稱機率檢驗)、forensics(假績效統計鑑識)、
  survivorship(倖存者偏差精確解)
- 風險工具:risk-sim(爆倉情境模擬,吸收態)、trend(優勢衰退偵測)
- 輸出:文字報告 / HTML 報告 / 分享圖卡 / JSON(--full 一鍵健檢)
- scaffold:13 種券商 × 4 種圖表庫的個人交易程式產生器(預設紙上模擬,
  真實下單雙閘門)
- 多市場:台股(張數×1000、當沖稅減半)、台股 ETF、台指期/選擇權
  (契約乘數白名單)、美股(SEC/FINRA 規費)、加密貨幣、外匯
- 測試套件(0.1.0 時為 200 個;現況見 README)

### Fixed(歷輪重大修復摘錄)
- 回撤百分比的兩層前視偏差(當下高水位 + 因果資本基準)
- 全勝樣本比率指標語意(0 → 不適用/∞;JSON 序列化 null)
- 裸幣代號劫持美股(SOL/ETHA)與幣幣對假陰性
- loader 靜默補 0 製造假交易;Big5 CSV 編碼回退與揭露
- format_fraction 端點捨入紀律(0.9996 不顯示 100%)
- scam-check 亂輸入不再被靜默當「否」;EOF 不給半套結論
