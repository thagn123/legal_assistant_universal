"""
Query intent classification.

Deterministic, pattern-based. No LLM required.
Classifies a user query into one of four intent categories used by the
reasoning engine to determine how to frame its response.

Intent taxonomy:
  lookup       — looking up a specific article, clause, or structural element
  explanation  — asking for the meaning or reasoning behind a provision
  comparison   — comparing two or more provisions or concepts
  compliance   — asking whether something is allowed/required/prohibited
  unknown      — cannot be classified (treated conservatively)

Design rules:
  - Never calls an LLM. Pattern matching only.
  - Patterns are evaluated in priority order: compliance > comparison > lookup > explanation.
  - Defaults to unknown if no pattern matches.
  - Both Vietnamese and English surface forms are covered.

Usage:
    from src.graphrag.query_intent import classify_intent, INTENT_LOOKUP

    intent = classify_intent("What does Article 5 say about payment?")
    # → "lookup"
"""

from __future__ import annotations

import re
from typing import List, Tuple

# ---------------------------------------------------------------------------
# Intent constants
# ---------------------------------------------------------------------------

INTENT_LOOKUP = "lookup"
INTENT_EXPLANATION = "explanation"
INTENT_COMPARISON = "comparison"
INTENT_COMPLIANCE = "compliance"
INTENT_UNKNOWN = "unknown"

ALL_INTENTS = (INTENT_LOOKUP, INTENT_EXPLANATION, INTENT_COMPARISON, INTENT_COMPLIANCE, INTENT_UNKNOWN)


# ---------------------------------------------------------------------------
# Pattern sets (compiled once at module load)
# ---------------------------------------------------------------------------

# Each pattern list is applied with re.IGNORECASE.
# Priority order for evaluation: compliance → comparison → lookup → explanation.

_COMPLIANCE_RAW: List[str] = [
    r"\b(comply|compliant|compliance|non-compliance)\b",
    r"\b(violat(?:e|es|ion|ing))\b",
    r"\b(allowed?|permit(?:ted|s)?|prohibit(?:ed|s)?|forbid(?:den)?)\b",
    r"\b(must|shall|required to|obliged to)\b.{0,30}\b(by law|under|pursuant)\b",
    r"\b(is it legal|legally required|legal obligation)\b",
    # Vietnamese
    r"\b(tuân thủ|vi phạm|được phép|bị cấm|có thể|có được phép|có buộc|bắt buộc)\b",
]

_COMPARISON_RAW: List[str] = [
    r"\b(compar(?:e|ing|ison))\b",
    r"\b(difference|differ(?:ent|ence)?|distinguish)\b",
    r"\bvs\.?\b",
    r"\bversus\b",
    r"\bbetween\b.{0,40}\band\b",
    # Vietnamese
    r"\b(so sánh|khác nhau|phân biệt|giữa)\b",
]

_LOOKUP_RAW: List[str] = [
    # Direct structural reference queries
    r"\b(article|điều)\s+\d",
    r"\b(clause|khoản)\s+\d",
    r"\b(section|mục)\s+\d",
    r"\b(point|điểm)\s+[a-z\d]",
    r"\b(chapter|chương)\s+\d",
    r"\b(annex|phụ lục)\b",
    # Lookup verbs
    r"\b(what does|what is|what are|nêu|cho biết|quy định)\b.{0,40}\b(article|điều|clause|khoản|section|mục)\b",
    r"\b(show me|find|look up|tell me about)\b",
    r"\b(content of|text of|wording of|nội dung)\b",
]

_EXPLANATION_RAW: List[str] = [
    r"\b(explain|explanation)\b",
    r"\bwhat does\b.{0,20}\bmean\b",
    r"\b(meaning of|meaning)\b",
    r"\b(how does|how do|how is|how are)\b",
    r"\b(why is|why does|why should)\b",
    r"\b(purpose of|rationale|reason for)\b",
    # Vietnamese
    r"\b(giải thích|nghĩa|tại sao|như thế nào|mục đích|lý do)\b",
]

# Compile patterns
_COMPLIANCE_PATS: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in _COMPLIANCE_RAW]
_COMPARISON_PATS: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in _COMPARISON_RAW]
_LOOKUP_PATS: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in _LOOKUP_RAW]
_EXPLANATION_PATS: List[re.Pattern] = [re.compile(p, re.IGNORECASE) for p in _EXPLANATION_RAW]

# Ordered evaluation: compliance → comparison → lookup → explanation
_PRIORITY_ORDER: List[Tuple[str, List[re.Pattern]]] = [
    (INTENT_COMPLIANCE, _COMPLIANCE_PATS),
    (INTENT_COMPARISON, _COMPARISON_PATS),
    (INTENT_LOOKUP, _LOOKUP_PATS),
    (INTENT_EXPLANATION, _EXPLANATION_PATS),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify_intent(query: str) -> str:
    """
    Classify the query into one of the intent categories.

    Evaluated in priority order: compliance → comparison → lookup → explanation.
    Returns INTENT_UNKNOWN if no pattern matches.

    Args:
        query: Raw query string, any language.

    Returns:
        One of: "lookup", "explanation", "comparison", "compliance", "unknown"
    """
    for intent, patterns in _PRIORITY_ORDER:
        for pat in patterns:
            if pat.search(query):
                return intent
    return INTENT_UNKNOWN


def matched_patterns(query: str) -> List[Tuple[str, str]]:
    """
    Return all (intent, pattern_source) pairs that matched the query.
    Useful for debugging classification decisions.

    Args:
        query: Raw query string.

    Returns:
        List of (intent, pattern_string) tuples for every match found.
    """
    matches: List[Tuple[str, str]] = []
    raw_pats = [
        (INTENT_COMPLIANCE, _COMPLIANCE_RAW),
        (INTENT_COMPARISON, _COMPARISON_RAW),
        (INTENT_LOOKUP, _LOOKUP_RAW),
        (INTENT_EXPLANATION, _EXPLANATION_RAW),
    ]
    for intent, raw_list in raw_pats:
        for pat_str in raw_list:
            if re.search(pat_str, query, re.IGNORECASE):
                matches.append((intent, pat_str))
    return matches
