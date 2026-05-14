"""
Query normalizer — converts legal reference surface forms into canonical IDs.

Canonical IDs are stable, language-independent strings used as retrieval keys.
They are attached to chunks and graph nodes so that a query in any language
can match content regardless of the source language.

Normalisation rules:
  "Article 1"        → "article_1"
  "Art. 1"           → "article_1"
  "Điều 1"           → "article_1"
  "Clause 3(a)"      → "clause_3_a"
  "Khoản 3 Điểm a"   → "clause_3_a" (when context gives article)
  "Section II"       → "section_2"
  "Mục II"           → "section_2"
  "Chapter I"        → "chapter_1"
  "Chương I"         → "chapter_1"

Design rules:
  - No AI required — pure regex + alias lookup.
  - Roman numerals are converted to integers.
  - Letter suffixes (a, b, c) are preserved as-is.
  - Canonical form is always: {level}_{number}[_{subletter}]
  - Input is always normalised to lowercase before matching.
  - Unknown references are returned as-is (not silently dropped).

Usage:
    from src.retrieval.query_normalizer import normalize_query, extract_refs

    normalize_query("Điều 5")          # → "article_5"
    normalize_query("Art. 3(b)")       # → "article_3_b"
    normalize_query("Article 2")       # → "article_2"
    normalize_query("Chapter III")     # → "chapter_3"

    extract_refs("See Article 5, Clause 2(a) and Section IV")
    # → ["article_5", "clause_2_a", "section_4"]
"""

from __future__ import annotations

import re
from typing import List, Optional

from src.retrieval.legal_aliases import canonical_term

# ---------------------------------------------------------------------------
# Roman numeral converter
# ---------------------------------------------------------------------------

_ROMAN = {
    "m": 1000, "cm": 900, "d": 500, "cd": 400,
    "c": 100,  "xc": 90,  "l": 50,  "xl": 40,
    "x": 10,   "ix": 9,   "v": 5,   "iv": 4,
    "i": 1,
}
_ROMAN_RE = re.compile(
    r"^(?:m{0,4})(?:cm|cd|d?c{0,3})(?:xc|xl|l?x{0,3})(?:ix|iv|v?i{0,3})$",
    re.IGNORECASE,
)


def roman_to_int(s: str) -> Optional[int]:
    """Convert a Roman numeral string to int, or return None if not a Roman numeral."""
    s = s.strip().lower()
    if not s or not _ROMAN_RE.match(s):
        return None
    result = 0
    i = 0
    keys = list(_ROMAN.keys())
    while i < len(s):
        if i + 1 < len(s) and s[i:i+2] in _ROMAN:
            result += _ROMAN[s[i:i+2]]
            i += 2
        elif s[i] in _ROMAN:
            result += _ROMAN[s[i]]
            i += 1
        else:
            return None  # unexpected character
    return result if result > 0 else None


# ---------------------------------------------------------------------------
# Number normaliser (Arabic or Roman → plain int string)
# ---------------------------------------------------------------------------


def normalise_number(s: str) -> str:
    """
    Convert a number string (Arabic or Roman) to a plain integer string.
    Returns the original string lowercased if conversion fails.

    Examples:
        normalise_number("3")    → "3"
        normalise_number("III")  → "3"
        normalise_number("iv")   → "4"
        normalise_number("abc")  → "abc"  (not a number — preserved as subpoint)
    """
    s = s.strip()
    # Try plain integer first
    try:
        return str(int(s))
    except ValueError:
        pass
    # Try Roman numeral
    roman = roman_to_int(s)
    if roman is not None:
        return str(roman)
    # Preserve as-is (likely a subpoint label like "a", "b", "c")
    return s.lower()


# ---------------------------------------------------------------------------
# Reference pattern: <term> <number> [(<subpoint>)]
# ---------------------------------------------------------------------------

# Matches things like:
#   "Article 1", "Điều 3", "Art. 2(a)", "Khoản 5b", "Section IV", "Mục II.3"
# Groups: (term_word) (main_number) (subletter_optional)
_REF_PATTERN = re.compile(
    r"""
    (?P<term>
        điều | khoản | điểm | chương | mục | phần |           # Vietnamese
        article | art\.? | clause | cl\.? | section | sec\.? | sect\.? |
        chapter | chap\.? | part | annex | paragraph | para\.? |
        subsection                                             # English
    )
    \s*
    (?P<number>[IVXLCDM]+|[0-9]+(?:\.[0-9]+)?)               # Roman or Arabic (with optional .sub)
    \s*
    (?:\((?P<subletter>[a-z0-9]+)\)|(?P<suffix>[a-z])(?=\s|$))?   # (a) or trailing letter
    """,
    re.IGNORECASE | re.VERBOSE | re.UNICODE,
)


def _ref_match_to_canonical(m: re.Match) -> Optional[str]:
    """Convert a regex match from _REF_PATTERN to a canonical ID string."""
    term_raw = m.group("term").strip().rstrip(".")
    canonical = canonical_term(term_raw)
    if not canonical:
        return None

    number_raw = m.group("number")
    number_str = normalise_number(number_raw)

    subletter = m.group("subletter") or m.group("suffix") or ""
    if subletter:
        return f"{canonical}_{number_str}_{subletter.lower()}"
    return f"{canonical}_{number_str}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def normalize_query(query: str) -> str:
    """
    Attempt to normalize a legal reference query string to a canonical ID.

    If the entire query is a legal reference, return the canonical ID.
    If the query contains a reference among other words, extract and return
    the first canonical ID found.
    If no reference is found, return the query lowercased and stripped.

    Examples:
        normalize_query("Article 1")     → "article_1"
        normalize_query("Điều 1")        → "article_1"
        normalize_query("Art. 3(b)")     → "article_3_b"
        normalize_query("Chapter III")   → "chapter_3"
        normalize_query("Mục II")        → "section_2"
        normalize_query("payment terms") → "payment terms"
    """
    stripped = query.strip()
    m = _REF_PATTERN.search(stripped.lower())
    if m:
        canonical = _ref_match_to_canonical(m)
        if canonical:
            return canonical
    return stripped.lower()


def extract_refs(text: str) -> List[str]:
    """
    Extract all canonical legal references from a block of text.

    Returns a list of canonical IDs in order of appearance, deduplicated
    while preserving order.

    Example:
        extract_refs("See Article 5, Clause 2(a) and Section IV")
        → ["article_5", "clause_2_a", "section_4"]
    """
    seen: set[str] = set()
    result: List[str] = []
    for m in _REF_PATTERN.finditer(text.lower()):
        canonical = _ref_match_to_canonical(m)
        if canonical and canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result


def query_to_search_terms(query: str) -> List[str]:
    """
    Decompose a query string into retrieval search terms.

    Returns the canonical ID (if the query is a reference) plus the
    original words for keyword fallback, deduplicated.

    Example:
        query_to_search_terms("Article 1 payment")
        → ["article_1", "article", "1", "payment"]

        query_to_search_terms("nghĩa vụ thanh toán")
        → ["nghĩa", "vụ", "thanh", "toán"]
    """
    terms: List[str] = []
    # Extract canonical reference if present
    m = _REF_PATTERN.search(query.lower())
    if m:
        canonical = _ref_match_to_canonical(m)
        if canonical:
            terms.append(canonical)
    # Add individual words (lowercased, non-empty)
    for word in re.split(r"[\s,;.:()\[\]]+", query.lower()):
        word = word.strip()
        if word and word not in terms:
            terms.append(word)
    return terms
