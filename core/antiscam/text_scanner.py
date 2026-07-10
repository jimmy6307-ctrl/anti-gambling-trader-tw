"""詐騙話術文字偵測 — 貼上群組對話,掃描話術特徵。

設計原則(這些限制比功能本身更重要):

  1. **不給假百分比。** 只給序數等級(極高/高/中/低/資訊不足)。
     「87.3% 是詐騙」這種數字沒有經過任何標註語料校準,是假精準。

  2. **不用關鍵字密度。** 密度(命中詞 ÷ 總字數)可被「長文夾一個關鍵字」
     稀釋規避,也會讓短促高壓的正常訊息灌到高分。改用
     **「命中了幾種相異的話術類別」** —— 這對長度穩健,也難以操弄。

  3. **雙向否定視窗。** 中文的否定/警示詞常出現在關鍵字**之後**:
     「保證獲利?那都是騙人的」。只看關鍵字前方會把反詐教育文誤判成詐騙。

  4. **討論守門(discussion gate)。** 出現「這是詐騙嗎」「小心」「不要相信」
     這類討論/警示語境時降級,避免把反詐討論本身判成詐騙。

  5. **單一類別上限。** 同一類別重複命中不加成,防止靠複製貼上灌分。

  6. **不做統計顯著性檢定。** 單一則文字沒有抽樣模型,p 值在此無定義。
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .patterns import SCAM_PATTERNS, ScamPattern, find_pattern

# 零寬字元(U+200B/200C/200D、BOM、word joiner):詐騙文案可夾在關鍵字中間規避比對
_ZERO_WIDTH = re.compile(r"[​‌‍⁠﻿]")

# 簡體 → 繁體對照(防盲區):詐騙集團常用簡體發文(「保证获利」「老师带单」),
# 而詞庫全為繁體 —— 實測簡體版核心話術原本 0 命中、判「低風險」,完全繞過偵測。
# 只收「簡體專用字」(在繁體中不作為獨立常用字出現的),**刻意排除**
# 干/里/面/后/发 這類簡繁共用但意義不同的字,避免誤改正常繁體文。
# 涵蓋範圍 = 詞庫 + 警示詞 + 守門詞 + 自我否認詞實際用到的異形字。
_S2T = str.maketrans(
    "证获稳赚赔风险师带单报内线飙级进讯学员见图对帐账财冻缴税储砖载汇额时"
    "错过没现场仅谢骗别当话术质举检诈团吗么断识请问这会机着",
    "證獲穩賺賠風險師帶單報內線飆級進訊學員見圖對帳帳財凍繳稅儲磚載匯額時"
    "錯過沒現場僅謝騙別當話術質舉檢詐團嗎麼斷識請問這會機著",
)

_SENTENCE_DELIM = re.compile(r"[。!?!?\n；;]+")

# ── 話術詞庫:(片語, 對應的詐騙型態代碼, 權重) ────────────────
# 權重 3 = 近乎鐵證的詐騙用語;2 = 強烈可疑;1 = 需搭配其他訊號
_LEXICON: list[tuple[str, str, int]] = [
    # 保證獲利 / 高勝率話術
    ("保證獲利", "guaranteed_return", 3),
    ("穩賺不賠", "guaranteed_return", 3),
    ("穩賺", "guaranteed_return", 2),
    ("包賺", "guaranteed_return", 3),
    ("零風險", "guaranteed_return", 3),
    ("保本", "guaranteed_return", 2),
    ("穩定獲利", "guaranteed_return", 1),
    ("月配息", "guaranteed_return", 1),
    ("翻倍", "guaranteed_return", 1),
    ("躺著賺", "guaranteed_return", 2),
    # 假飆股群 / 假老師
    ("老師帶單", "fake_stock_group", 3),
    ("帶單", "fake_stock_group", 2),
    ("報明牌", "fake_stock_group", 2),
    ("明牌", "fake_stock_group", 1),
    ("內線", "fake_stock_group", 3),
    ("飆股", "fake_stock_group", 1),
    ("升級vip", "fake_stock_group", 3),
    ("升級 vip", "fake_stock_group", 3),
    ("進二群", "fake_stock_group", 3),
    ("二群", "fake_stock_group", 2),
    ("加客服", "fake_stock_group", 2),
    ("私訊我", "fake_stock_group", 1),
    ("跟單", "fake_stock_group", 1),
    # 假名師 / 假績效
    ("學員見證", "fake_guru", 2),
    ("獲利截圖", "fake_guru", 2),
    ("對帳單", "fake_guru", 1),
    ("財富自由", "fake_guru", 1),
    ("素人翻身", "fake_guru", 2),
    ("跟著老師", "fake_guru", 2),
    # 詐騙幣 / 假平台
    ("解凍金", "fake_platform", 3),
    ("刷流水", "fake_platform", 3),
    ("出金要繳稅", "fake_platform", 3),
    ("繳稅才能出金", "fake_platform", 3),
    ("平台儲值", "fake_platform", 3),
    ("入金", "fake_platform", 2),
    ("搬磚套利", "fake_platform", 3),
    ("下載app", "fake_platform", 1),
    ("匯款到", "fake_platform", 2),
]

# 結構性話術訊號:急迫、稀缺、權威、社會證明
_STRUCTURAL: list[tuple[str, str, int]] = [
    ("名額有限", "urgency", 2),
    ("限時", "urgency", 1),
    ("最後機會", "urgency", 2),
    ("錯過就沒有", "urgency", 2),
    ("現在不進場", "urgency", 2),
    ("僅限今天", "urgency", 2),
    ("恭喜學員", "social_proof", 2),
    ("感謝老師", "social_proof", 2),
    ("又賺了", "social_proof", 1),
]

# 警示詞:句中出現時,代表這句在「揭穿 / 警告 / 求證」詐騙,而非施行詐騙。
# 中文的否定常在關鍵字**之後**(「保證獲利?都是騙人的」),所以用句子層級判斷。
_WARNING_MARKERS = (
    "都是騙人", "是騙人的", "都是假", "是假的", "別信", "不要信", "不要相信",
    "不可信", "小心", "當心", "留意", "警惕", "陷阱", "手法", "話術",
    "質疑", "拆穿", "揭穿", "舉報", "檢舉", "報警", "165",
    "是詐騙", "都是詐騙", "常見的詐騙", "詐騙集團", "受害",
)

# ⚠️ 自我否認:詐騙犯自己說「我們不是詐騙」。這**不是**否定,反而是警訊
# (protesting too much)。必須在判定警示語境前先剔除,否則會被規避。
_SELF_DENIAL = (
    "不是詐騙", "並非詐騙", "絕不是詐騙", "不是騙人", "不是老鼠會", "不是吸金",
)

# 討論守門詞:整段文字若明顯是在「討論/教育/求證」詐騙,整體降級
_DISCUSSION_MARKERS = (
    "是詐騙嗎", "是不是詐騙", "怎麼判斷", "如何辨識", "反詐", "防詐",
    "請問這", "有人遇過", "求證", "165", "分享一下經驗", "提醒大家",
    "典型手法", "常見手法", "請小心", "詐騙手法",
)

# 句子太長時,退回「關鍵字前後 N 字元」的視窗(雙向)
_NEG_WINDOW = 20
_LONG_SENTENCE = 60


@dataclass(frozen=True)
class Hit:
    """一次話術命中。"""

    phrase: str
    category: str          # 詐騙型態代碼 或 結構性訊號名
    weight: int
    position: int
    negated: bool          # 附近有否定/警示詞 → 不計分
    sentence: str


@dataclass
class TextScanResult:
    """文字掃描結果。刻意只給序數等級,不給假百分比。"""

    risk_level: str                     # 極高 / 高 / 中 / 低 / 資訊不足
    headline: str
    distinct_categories: int            # 命中的相異話術類別數(主要判準)
    effective_score: int                # 內部分數(僅供門檻,不對外呈現為百分比)
    hits: list[Hit] = field(default_factory=list)
    negated_hits: list[Hit] = field(default_factory=list)
    is_discussion: bool = False
    matched_patterns: list[ScamPattern] = field(default_factory=list)
    advice: list[str] = field(default_factory=list)
    annotated_sentences: list[tuple[str, list[str]]] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {
            "risk_level": self.risk_level,
            "headline": self.headline,
            "distinct_categories": self.distinct_categories,
            "is_discussion": self.is_discussion,
            "hits": [
                {"phrase": h.phrase, "category": h.category, "weight": h.weight}
                for h in self.hits
            ],
            "matched_patterns": [p.code for p in self.matched_patterns],
            "advice": self.advice,
        }


def _split_sentences(text: str) -> list[str]:
    parts = _SENTENCE_DELIM.split(text)
    return [p.strip() for p in parts if p.strip()]


def _sentence_spans(text: str) -> list[tuple[int, int]]:
    """回傳每個句子的 (start, end) 位置區間,用於把命中位置對回正確的句子。

    舊版用「第一個含該片語的句子」,當同一片語出現多次時會對錯句子,
    導致警示語境判定用錯上下文。
    """
    spans: list[tuple[int, int]] = []
    last = 0
    for m in _SENTENCE_DELIM.finditer(text):
        if m.start() > last:
            spans.append((last, m.start()))
        last = m.end()
    if last < len(text):
        spans.append((last, len(text)))
    return spans


def _sentence_at(spans: list[tuple[int, int]], text: str, pos: int) -> str:
    """取出位置 pos 所在的句子(小寫文本)。"""
    for a, b in spans:
        if a <= pos < b:
            return text[a:b].strip()
    return text[max(0, pos - 20):pos + 20]


def _strip_self_denial(s: str) -> str:
    """把「不是詐騙」這類自我否認先拿掉,免得它被當成警示語境。"""
    out = s
    for d in _SELF_DENIAL:
        out = out.replace(d, "")
    return out


def _has_self_denial(text_lower: str) -> bool:
    return any(d in text_lower for d in _SELF_DENIAL)


def _is_warning_context(sentence_lower: str, text_lower: str,
                        start: int, end: int) -> bool:
    """這個關鍵字是不是出現在「揭穿/警告詐騙」的語境?

    中文的否定與警示詞可能在關鍵字前也可能在後(「老師帶單…都是詐騙手法」),
    所以用**整句**判斷,而不是固定字元視窗 —— 這是先前誤判反詐教育文的根因。
    句子過長時才退回雙向字元視窗,避免整段長文被單一警示詞抹平。
    """
    cleaned = _strip_self_denial(sentence_lower)
    if len(cleaned) <= _LONG_SENTENCE:
        return any(w in cleaned for w in _WARNING_MARKERS)
    lo = max(0, start - _NEG_WINDOW)
    hi = min(len(text_lower), end + _NEG_WINDOW)
    window = _strip_self_denial(text_lower[lo:hi])
    return any(w in window for w in _WARNING_MARKERS)


def scan_text(text: str) -> TextScanResult:
    """掃描一段文字的詐騙話術特徵。

    Returns:
        TextScanResult(序數風險等級 + 逐句標註 + 對應的反詐金句)
    """
    raw = (text or "").strip()
    if len(raw) < 4:
        return TextScanResult(
            risk_level="資訊不足",
            headline="文字太短,無法判斷。請貼上完整的對話或文案。",
        )

    # ── 正規化(防規避):純標準庫,零依賴 ──
    # (a) NFKC:全形拉丁字母/數字/標點 → 半形(「ＶＩＰ」→「vip」、「保　證」的全形空白)
    # (b) 移除零寬字元:詐騙文案可在關鍵字中間夾 U+200B 等,肉眼看不出、比對卻失效
    norm = unicodedata.normalize("NFKC", raw)
    norm = _ZERO_WIDTH.sub("", norm)
    # 簡→繁正規化:str.translate 是 1:1 等長替換,不位移任何 position,
    # 因此 _sentence_spans 的座標對應不會壞;繁體輸入經過此步完全不變。
    norm = norm.translate(_S2T)
    lower = norm.lower()
    sentences = _split_sentences(norm)
    sentence_spans = _sentence_spans(lower)

    # 討論守門:先剔除「我們不是詐騙」這類自我否認,免得詐騙犯用它觸發降級
    lower_clean = _strip_self_denial(lower)
    is_discussion = any(m in lower_clean for m in _DISCUSSION_MARKERS)

    hits: list[Hit] = []
    negated: list[Hit] = []
    all_terms = [(p, c, w) for p, c, w in _LEXICON] + [
        (p, c, w) for p, c, w in _STRUCTURAL
    ]

    for phrase, category, weight in all_terms:
        # 掃描「所有」出現位置,不能只看第一個就 break:
        # 攻擊情境:「保證獲利?都是騙人的…不,我們真的保證獲利!」——
        # 第一次出現在警示語境會被排除,若就此 break,第二次真正的話術會漏抓。
        # 只要有任何一個 occurrence 不在警示語境,就算一次有效命中(仍只計一次分)。
        best_hit: Hit | None = None
        for m in re.finditer(re.escape(phrase.lower()), lower):
            sent = _sentence_at(sentence_spans, lower, m.start())
            neg = _is_warning_context(sent, lower, m.start(), m.end())
            h = Hit(phrase, category, weight, m.start(), neg, sent)
            if not neg:
                best_hit = h
                break            # 找到有效命中即可(同片語只計一次分)
            if best_hit is None:
                best_hit = h     # 暫存被否定的,若全部被否定就歸 negated
        if best_hit is not None:
            (negated if best_hit.negated else hits).append(best_hit)

    # 「我們不是詐騙」是 protesting too much —— 當作額外警訊,而非否定
    self_denial = _has_self_denial(lower)
    if self_denial:
        hits.append(Hit("(自稱不是詐騙)", "self_denial", 2, 0, False, raw[:40]))

    # ── 計分:單一類別只取該類別的最高權重(上限),避免同類堆疊灌分 ──
    per_category_max: dict[str, int] = {}
    for h in hits:
        per_category_max[h.category] = max(per_category_max.get(h.category, 0), h.weight)

    effective = sum(per_category_max.values())
    distinct = len(per_category_max)
    has_hard_evidence = any(w >= 3 for w in per_category_max.values())

    # ── 序數等級:主要看「命中幾種相異類別」,而非密度或總分 ──
    # 討論守門的例外:即使有求證/提醒語境,若同時命中 3 種以上相異話術類別,
    # 更可能是詐騙文案「夾帶」一句求證語來規避偵測 —— 不降級。
    if is_discussion and not has_hard_evidence and distinct < 3:
        level = "低"
        headline = (
            "這段文字看起來像是在『討論或警告』詐騙,而不是詐騙本身。"
            "(偵測到求證 / 提醒的語境)"
        )
    elif has_hard_evidence and distinct >= 2:
        level = "極高"
        headline = "🚨 極高風險:出現多種典型詐騙話術,且含近乎鐵證的用語。"
    elif has_hard_evidence or distinct >= 3:
        level = "高"
        headline = "⚠️ 高風險:出現典型的投資詐騙話術。"
    elif distinct >= 2 or effective >= 3:
        level = "中"
        headline = "🟡 中度可疑:出現一些常見的詐騙話術特徵,請提高警覺。"
    elif distinct >= 1:
        level = "低"
        headline = "🟢 低風險:僅出現少量可疑用語,可能是一般投資討論。"
    else:
        level = "低"
        headline = "🟢 未偵測到明顯的詐騙話術。但話術會演化,仍請保持警覺。"

    # ── 對應的反詐金句 ──
    scam_codes = {h.category for h in hits}
    matched = [p for p in SCAM_PATTERNS if p.code in scam_codes]

    advice: list[str] = []
    if level in ("極高", "高"):
        advice.append("不要匯款、不要下載對方指定的 App、不要『升級』。")
        advice.append("保留對話與匯款紀錄。台灣可撥打 165 反詐騙諮詢專線查證。")
    for p in matched:
        advice.append(f"【{p.name}】{p.rebuttal}")
    if negated:
        advice.append(
            f"註:有 {len(negated)} 處關鍵字附近出現否定/警示詞"
            "(如「都是騙人的」),已判定為討論而非話術,未計入風險。"
        )

    # ── 逐句標註 ──
    annotated: list[tuple[str, list[str]]] = []
    for s in sentences:
        found = [h.phrase for h in hits if h.phrase.lower() in s.lower()]
        if found:
            annotated.append((s, found))

    return TextScanResult(
        risk_level=level,
        headline=headline,
        distinct_categories=distinct,
        effective_score=effective,
        hits=hits,
        negated_hits=negated,
        is_discussion=is_discussion,
        matched_patterns=matched,
        advice=advice,
        annotated_sentences=annotated,
    )


def render_scan(r: TextScanResult) -> str:
    """輸出可讀報告。"""
    L = ["=" * 60, "        詐騙話術文字偵測", "=" * 60, ""]
    L.append(f"【風險等級】{r.risk_level}")
    L.append(f"  {r.headline}")
    L.append("")
    if r.annotated_sentences:
        L.append("【逐句標註】")
        for s, phrases in r.annotated_sentences[:10]:
            L.append(f"  「{s[:40]}」")
            L.append(f"      ↳ 命中話術:{', '.join(phrases)}")
        L.append("")
    if r.advice:
        L.append("【反詐提醒】")
        for a in r.advice:
            L.append(f"  • {a}")
        L.append("")
    L.append("─" * 60)
    L.append("註:本工具用『命中幾種相異話術類別』判斷,不給假精準的百分比。")
    L.append("    話術會演化,未命中不代表安全。最終請以 165 專線查證為準。")
    return "\n".join(L)
