"""
Formal language detection with jurisdiction and confidence scoring.

Design rules:
- Local-only: no API calls, no ML models loaded at import time.
- Deterministic: same input always produces the same output.
- Returns confidence alongside language code so callers can gate on quality.

Usage:
    from src.retrieval.language_detector import detect_language, LanguageDetectionResult

    result = detect_language("Điều 1. Giải thích thuật ngữ")
    result.language        # "vi"
    result.confidence      # 0.92
    result.jurisdiction    # "VN"
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional

try:
    from pydantic import BaseModel
    _USE_PYDANTIC = True
except ImportError:
    from src.utils.compat import BaseModel  # type: ignore
    _USE_PYDANTIC = False


# ---------------------------------------------------------------------------
# Result object
# ---------------------------------------------------------------------------

if _USE_PYDANTIC:
    class LanguageDetectionResult(BaseModel):
        language: str = "unknown"
        confidence: float = 0.0
        jurisdiction: Optional[str] = None
        script: str = "unknown"
        signals: List[str] = []
else:
    from dataclasses import dataclass as _dc, field as _field

    @_dc
    class LanguageDetectionResult:  # type: ignore[no-redef]
        language: str = "unknown"
        confidence: float = 0.0
        jurisdiction: Optional[str] = None
        script: str = "unknown"
        signals: List[str] = _field(default_factory=list)


# ---------------------------------------------------------------------------
# Vietnamese signals
# ---------------------------------------------------------------------------

# Vietnamese tonal diacritic characters (unique to Vietnamese among Latin scripts)
_VI_DIACRITICS_RE = re.compile(
    "["
    "àáảãạăắặằẳẵ"
    "âấầẩẫậèéẻẽẹ"
    "êếềểễệìíỉĩị"
    "òóỏõọôốồổỗộ"
    "ơớờởỡợùúủũụ"
    "ưứừửữựỳýỷỹỵđ"
    "ÀÁẢÃẠĂẮẶẰẲẴ"
    "ÂẤẦẨẪẬÈÉẺẼẸ"
    "ÊẾỀỂỄỆÌÍỈĨỊ"
    "ÒÓỎÕỌÔỐỒỔỖỘ"
    "ƠỚỜỞỠỢÙÚỦŨỤ"
    "ƯỨỪỬỮỰỲÝỶỸỴĐ]",
    re.UNICODE,
)

# Vietnamese legal structural terms — use \\b so the regex engine sees \b (word boundary)
_VI_STRUCTURAL_TERMS = [
    "\\bđiều\\b",
    "\\bkhoản\\b",
    "\\bđiểm\\b",
    "\\bchương\\b",
    "\\bmục\\b",
    "\\bphần\\b",
    "\\bphụ\\s*lục\\b",
]
_VI_STRUCTURAL_RE = re.compile("|".join(_VI_STRUCTURAL_TERMS), re.IGNORECASE | re.UNICODE)

_VI_CONTENT_TERMS = [
    "\\bhợp\\s*đồng\\b",
    "\\bnghĩa\\s*vụ\\b",
    "\\bthanh\\s*toán\\b",
    "\\bpháp\\s*luật\\b",
    "\\bnghị\\s*định\\b",
    "\\bthông\\s*tư\\b",
    "\\bquyết\\s*định\\b",
    "\\bquy\\s*định\\b",
    "\\bbên\\s*[ab]\\b",
    "\\bcộng\\s*hòa\\b",
    "\\bviệt\\s*nam\\b",
    "\\btòa\\s*án\\b",
    "\\btrọng\\s*tài\\b",
    "\\bbồi\\s*thường\\b",
]
_VI_CONTENT_RE = re.compile("|".join(_VI_CONTENT_TERMS), re.IGNORECASE | re.UNICODE)

_VI_JURISDICTION_TERMS = re.compile(
    "\\b(việt\\s*nam|VIAC|TAND|UBND|HĐND|Bộ\\s+Tư\\s+pháp|Luật\\s+Việt\\s+Nam)\\b",
    re.IGNORECASE | re.UNICODE,
)


# ---------------------------------------------------------------------------
# English signals
# ---------------------------------------------------------------------------

_EN_STRUCTURAL_TERMS = [
    r"\barticle\b",
    r"\bclause\b",
    r"\bsection\b",
    r"\bchapter\b",
    r"\bschedule\b",
    r"\bannex\b",
    r"\bappendix\b",
    r"\bparagraph\b",
    r"\bsubsection\b",
]
_EN_STRUCTURAL_RE = re.compile("|".join(_EN_STRUCTURAL_TERMS), re.IGNORECASE)

_EN_CONTENT_TERMS = [
    r"\bagreement\b",
    r"\bcontract\b",
    r"\bobligation\b",
    r"\bpayment\b",
    r"\bwarranty\b",
    r"\bindemnif",
    r"\btermination\b",
    r"\bgoverning\s+law\b",
    r"\barbitration\b",
    r"\bjurisdiction\b",
    r"\bliabilit",
    r"\bconfidential",
    r"\bintellectual\s+property\b",
    r"\bforce\s+majeure\b",
    r"\bparty\s+[ab]\b",
    r"\bhereby\b",
    r"\bhereinafter\b",
    r"\bwhereas\b",
    r"\bnotwithstanding\b",
]
_EN_CONTENT_RE = re.compile("|".join(_EN_CONTENT_TERMS), re.IGNORECASE)

_EN_US_JURISDICTION_RE = re.compile(
    r"\b(united\s+states|u\.s\.|federal|u\.s\.c\.|u\.s\.\s+code)\b",
    re.IGNORECASE,
)
_EN_GB_JURISDICTION_RE = re.compile(
    r"\b(united\s+kingdom|u\.k\.|england\s+and\s+wales|scots\s+law)\b",
    re.IGNORECASE,
)
_EN_EU_JURISDICTION_RE = re.compile(
    r"\b(european\s+union|EU|GDPR|directive\s+\d{4}/\d+/EC)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Core detection function
# ---------------------------------------------------------------------------


def detect_language(text: str, sample_limit: int = 4000) -> LanguageDetectionResult:
    """Detect the primary language of a text string."""
    if not text or not text.strip():
        return LanguageDetectionResult(language="unknown", confidence=0.0, signals=["empty_input"])

    sample = text[:sample_limit]
    signals: List[str] = []
    vi_score: float = 0.0
    en_score: float = 0.0

    vi_diacritic_matches = _VI_DIACRITICS_RE.findall(sample)
    diacritic_density = len(vi_diacritic_matches) / max(len(sample), 1)
    if diacritic_density > 0.05:
        vi_score += 0.5
        signals.append("vi_diacritics_high")
    elif diacritic_density > 0.01:
        vi_score += 0.25
        signals.append("vi_diacritics_low")

    vi_struct_hits = len(_VI_STRUCTURAL_RE.findall(sample))
    if vi_struct_hits >= 3:
        vi_score += 0.3
        signals.append(f"vi_structural_terms:{vi_struct_hits}")
    elif vi_struct_hits >= 1:
        vi_score += 0.15
        signals.append(f"vi_structural_terms:{vi_struct_hits}")

    vi_content_hits = len(_VI_CONTENT_RE.findall(sample))
    if vi_content_hits >= 3:
        vi_score += 0.25
        signals.append(f"vi_content_keywords:{vi_content_hits}")
    elif vi_content_hits >= 1:
        vi_score += 0.1
        signals.append(f"vi_content_keywords:{vi_content_hits}")

    en_struct_hits = len(_EN_STRUCTURAL_RE.findall(sample))
    if en_struct_hits >= 3:
        en_score += 0.35
        signals.append(f"en_structural_terms:{en_struct_hits}")
    elif en_struct_hits >= 1:
        en_score += 0.2
        signals.append(f"en_structural_terms:{en_struct_hits}")

    en_content_hits = len(_EN_CONTENT_RE.findall(sample))
    if en_content_hits >= 3:
        en_score += 0.3
        signals.append(f"en_content_keywords:{en_content_hits}")
    elif en_content_hits >= 1:
        en_score += 0.15
        signals.append(f"en_content_keywords:{en_content_hits}")

    if diacritic_density == 0.0 and en_score > 0:
        en_score += 0.1
        signals.append("ascii_only_bias_en")

    jurisdiction: Optional[str] = None
    script: str = "ascii"
    if diacritic_density > 0:
        script = "latin_diacritics"

    if vi_score > 0 and _VI_JURISDICTION_TERMS.search(sample):
        jurisdiction = "VN"
        signals.append("jurisdiction:VN")
    elif en_score > 0:
        if _EN_US_JURISDICTION_RE.search(sample):
            jurisdiction = "US"
            signals.append("jurisdiction:US")
        elif _EN_GB_JURISDICTION_RE.search(sample):
            jurisdiction = "GB"
            signals.append("jurisdiction:GB")
        elif _EN_EU_JURISDICTION_RE.search(sample):
            jurisdiction = "EU"
            signals.append("jurisdiction:EU")

    vi_score = min(vi_score, 1.0)
    en_score = min(en_score, 1.0)

    DOMINANCE_THRESHOLD = 0.25

    if vi_score == 0.0 and en_score == 0.0:
        return LanguageDetectionResult(
            language="unknown", confidence=0.0,
            jurisdiction=jurisdiction, script=script, signals=signals,
        )

    if vi_score >= en_score + DOMINANCE_THRESHOLD:
        if jurisdiction is None:
            jurisdiction = "VN"
        return LanguageDetectionResult(
            language="vi", confidence=round(min(vi_score, 1.0), 3),
            jurisdiction=jurisdiction, script="latin_diacritics", signals=signals,
        )

    if en_score >= vi_score + DOMINANCE_THRESHOLD:
        return LanguageDetectionResult(
            language="en", confidence=round(min(en_score, 1.0), 3),
            jurisdiction=jurisdiction, script="ascii", signals=signals,
        )

    if jurisdiction is None and vi_score > 0:
        jurisdiction = "VN"
    return LanguageDetectionResult(
        language="mixed", confidence=round((vi_score + en_score) / 2, 3),
        jurisdiction=jurisdiction,
        script="latin_diacritics" if vi_score > 0 else "ascii",
        signals=signals,
    )


def detect_languages_from_blocks(texts: list) -> LanguageDetectionResult:
    """Detect language from multiple text blocks. Aggregates scores."""
    if not texts:
        return LanguageDetectionResult(language="unknown", confidence=0.0)

    vi_total = 0.0
    en_total = 0.0
    jurisdiction_votes: Dict[str, int] = {}
    all_signals: List[str] = []

    for text in texts:
        r = detect_language(text)
        if r.language == "vi":
            vi_total += r.confidence
        elif r.language == "en":
            en_total += r.confidence
        elif r.language == "mixed":
            vi_total += r.confidence * 0.5
            en_total += r.confidence * 0.5
        if r.jurisdiction:
            jurisdiction_votes[r.jurisdiction] = jurisdiction_votes.get(r.jurisdiction, 0) + 1
        all_signals.extend(r.signals)

    n = len(texts)
    vi_avg = vi_total / n
    en_avg = en_total / n

    best_jurisdiction: Optional[str] = None
    if jurisdiction_votes:
        best_jurisdiction = max(jurisdiction_votes, key=jurisdiction_votes.get)  # type: ignore

    DOMINANCE = 0.15
    if vi_avg >= en_avg + DOMINANCE:
        return LanguageDetectionResult(
            language="vi", confidence=round(min(vi_avg, 1.0), 3),
            jurisdiction=best_jurisdiction or "VN", script="latin_diacritics",
            signals=list(set(all_signals))[:20],
        )
    if en_avg >= vi_avg + DOMINANCE:
        return LanguageDetectionResult(
            language="en", confidence=round(min(en_avg, 1.0), 3),
            jurisdiction=best_jurisdiction, script="ascii",
            signals=list(set(all_signals))[:20],
        )
    return LanguageDetectionResult(
        language="mixed", confidence=round((vi_avg + en_avg) / 2, 3),
        jurisdiction=best_jurisdiction,
        script="latin_diacritics" if vi_avg > 0 else "ascii",
        signals=list(set(all_signals))[:20],
    )
