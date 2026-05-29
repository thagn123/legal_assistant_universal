from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence

from src.evidence.evidence_normalizer import (
    aliases_for_schema,
    get_required_evidence,
    normalize_text,
)
from src.evidence.evidence_schemas import (
    CONTRADICTED,
    MISSING,
    PRESENT,
    UNCERTAIN,
    EvidenceFact,
    EvidenceSchema,
)


@dataclass(frozen=True)
class _Cue:
    status: str
    start: int
    end: int
    text: str
    after_alias: bool = False


_POSITIVE_BEFORE = [
    "toi da co",
    "toi co",
    "minh da co",
    "minh co",
    "chung toi da co",
    "chung toi co",
    "da co",
    "hien co",
    "co san",
    "san co",
    "dang co",
    "da chuan bi",
    "da nop",
    "da cung cap",
    "dang giu",
    "luu giu",
    "giu",
    "nam giu",
    "toi dang nam giu",
    "dung ten toi",
    "do toi dung ten",
    "cua toi",
    "cua gia dinh toi",
    "co",
]

_POSSESSIVE_AFTER = [
    "cua toi",
    "cua gia dinh toi",
    "do toi giu",
    "do toi dang giu",
    "thuoc ve toi",
    "dung ten toi",
    "bi tranh chap",
]

_NEGATIVE_BEFORE = [
    "chua co",
    "khong co",
    "khong co ban goc",
    "khong giu",
    "khong giu ban goc",
    "thieu",
    "bi mat",
    "mat",
    "chua xin duoc",
    "khong tim thay",
    "chua nop",
]

_NEGATIVE_AFTER = [
    "bi mat",
    "mat ban goc",
    "khong con",
    "khong giu ban goc",
    "khong co ban goc",
    "that lac",
]

_UNCERTAIN = [
    "khong ro co",
    "khong biet co",
    "chua ro co",
    "hinh nhu co",
    "co the co",
    "nghe noi co",
    "khong chac",
]

_OTHER_HOLDER_TERMS = [
    "anh trai",
    "chi gai",
    "em trai",
    "em gai",
    "bo toi",
    "me toi",
    "ben kia",
    "nguoi khac",
    "nguoi ban",
    "anh ay",
    "chi ay",
]


def extract_evidence_facts(
    text: str,
    domain: str = "general",
    facts: Optional[Sequence[str]] = None,
    evidence_items: Optional[Sequence[EvidenceSchema]] = None,
) -> List[EvidenceFact]:
    """Extract deterministic evidence possession facts from user text and fact lines."""
    schemas = list(evidence_items or get_required_evidence(domain, text))
    extracted: List[EvidenceFact] = []
    if text:
        extracted.extend(_extract_from_segment(text, schemas, source="situation", default_status=None))
    for fact in facts or []:
        extracted.extend(_extract_from_segment(fact, schemas, source="facts", default_status=PRESENT))
    return _dedupe_facts(extracted)


def aggregate_evidence_facts(facts: Iterable[EvidenceFact]) -> Dict[str, EvidenceFact]:
    grouped: Dict[str, List[EvidenceFact]] = {}
    for fact in facts:
        grouped.setdefault(fact.evidence_id, []).append(fact)

    merged: Dict[str, EvidenceFact] = {}
    for evidence_id, group in grouped.items():
        statuses = {f.status for f in group}
        if CONTRADICTED in statuses or (PRESENT in statuses and MISSING in statuses):
            status = CONTRADICTED
            confidence = 0.8
        elif MISSING in statuses:
            status = MISSING
            confidence = max(f.confidence for f in group if f.status == MISSING)
        elif PRESENT in statuses:
            status = PRESENT
            confidence = max(f.confidence for f in group if f.status == PRESENT)
        else:
            status = UNCERTAIN
            confidence = max(f.confidence for f in group)

        first = group[0]
        matched_text = "; ".join(dict.fromkeys(f.matched_text for f in group if f.matched_text))[:300]
        matched_alias = first.matched_alias
        signals: List[str] = []
        for fact in group:
            signals.extend(fact.signals)
        merged[evidence_id] = EvidenceFact(
            evidence_id=evidence_id,
            status=status,
            matched_text=matched_text,
            matched_alias=matched_alias,
            confidence=round(confidence, 2),
            source="+".join(sorted({f.source for f in group})),
            signals=list(dict.fromkeys(signals)),
        )
    return merged


def _extract_from_segment(
    segment: str,
    schemas: Sequence[EvidenceSchema],
    source: str,
    default_status: Optional[str],
) -> List[EvidenceFact]:
    folded = normalize_text(segment)
    if not folded:
        return []

    facts: List[EvidenceFact] = []
    for schema in schemas:
        for alias in aliases_for_schema(schema):
            alias_folded = normalize_text(alias)
            if not alias_folded:
                continue
            for match in re.finditer(rf"(?<!\w){re.escape(alias_folded)}(?!\w)", folded):
                status, confidence, signals = _status_for_occurrence(
                    folded=folded,
                    alias_start=match.start(),
                    alias_end=match.end(),
                    default_status=default_status,
                )
                facts.append(
                    EvidenceFact(
                        evidence_id=schema.evidence_id,
                        status=status,
                        matched_text=_snippet(segment, match.start(), match.end()),
                        matched_alias=alias,
                        confidence=confidence,
                        source=source,
                        signals=signals,
                    )
                )
    return facts


def _status_for_occurrence(
    folded: str,
    alias_start: int,
    alias_end: int,
    default_status: Optional[str],
) -> tuple[str, float, List[str]]:
    before = folded[max(0, alias_start - 80):alias_start]
    after = folded[alias_end:min(len(folded), alias_end + 80)]

    if _other_holder_uncertain(before):
        return UNCERTAIN, 0.72, ["held_by_other_person"]

    uncertain_before = _nearest_before(before, _UNCERTAIN, limit=45)
    uncertain_after = _nearest_after(after, ["khong", "khong ro", "khong chac"], limit=18)
    if uncertain_before or uncertain_after:
        return UNCERTAIN, 0.72, ["uncertain_cue"]

    pos_before = _nearest_before(before, _POSITIVE_BEFORE, limit=90)
    neg_before = _nearest_before(before, _NEGATIVE_BEFORE, limit=45)
    neg_after = _nearest_after(after, _NEGATIVE_AFTER, limit=42)

    if pos_before and neg_after:
        return CONTRADICTED, 0.82, [f"positive:{pos_before}", f"negative_after:{neg_after}"]
    if neg_before and not _is_negated_positive_only(neg_before, pos_before):
        if pos_before and _distance_to_end(before, pos_before) <= _distance_to_end(before, neg_before):
            return PRESENT, 0.86, [f"positive:{pos_before}"]
        return MISSING, 0.88, [f"negative:{neg_before}"]
    if neg_after:
        return MISSING, 0.8, [f"negative_after:{neg_after}"]
    if pos_before:
        return PRESENT, 0.9, [f"positive:{pos_before}"]
    # "sổ đỏ của tôi", "hợp đồng lao động của tôi bị tranh chấp" → PRESENT
    pos_after_poss = _nearest_after(after, _POSSESSIVE_AFTER, limit=30)
    if pos_after_poss and not neg_before and not neg_after:
        return PRESENT, 0.85, [f"possessive:{pos_after_poss}"]
    if default_status == PRESENT:
        return PRESENT, 0.78, ["fact_line_default_present"]
    return UNCERTAIN, 0.45, ["mentioned_without_possession_cue"]


def _nearest_before(text: str, phrases: Sequence[str], limit: int) -> Optional[str]:
    best: tuple[int, str] | None = None
    for phrase in phrases:
        pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)" if phrase != "co" else r"(?<!\w)co(?!\w)"
        for match in re.finditer(pattern, text):
            if phrase == "co" and _bare_co_is_negated(text, match.start()):
                continue
            distance = len(text) - match.end()
            if 0 <= distance <= limit and (best is None or distance < best[0]):
                best = (distance, phrase)
    return best[1] if best else None


def _nearest_after(text: str, phrases: Sequence[str], limit: int) -> Optional[str]:
    best: tuple[int, str] | None = None
    for phrase in phrases:
        pattern = rf"(?<!\w){re.escape(phrase)}(?!\w)"
        for match in re.finditer(pattern, text):
            distance = match.start()
            if 0 <= distance <= limit and (best is None or distance < best[0]):
                best = (distance, phrase)
    return best[1] if best else None


def _distance_to_end(text: str, phrase: str) -> int:
    idx = text.rfind(phrase)
    if idx < 0:
        return 999
    return len(text) - (idx + len(phrase))


def _bare_co_is_negated(text: str, start: int) -> bool:
    prefix = text[max(0, start - 12):start].strip()
    return bool(re.search(r"(khong|chua|chẳng|chang|chua tung)$", prefix))


def _is_negated_positive_only(negative: Optional[str], positive: Optional[str]) -> bool:
    return bool(negative and positive == "co" and negative.endswith("co"))


def _other_holder_uncertain(before: str) -> bool:
    if "giu" not in before:
        return False
    return any(term in before for term in _OTHER_HOLDER_TERMS)


def _snippet(original: str, start: int, end: int) -> str:
    left = max(0, start - 60)
    right = min(len(original), end + 80)
    snippet = original[left:right].strip()
    return re.sub(r"\s+", " ", snippet)


def _dedupe_facts(facts: List[EvidenceFact]) -> List[EvidenceFact]:
    seen: set[tuple[str, str, str, str]] = set()
    out: List[EvidenceFact] = []
    for fact in facts:
        key = (
            fact.evidence_id,
            fact.status,
            normalize_text(fact.matched_alias),
            normalize_text(fact.matched_text),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(fact)
    return out
