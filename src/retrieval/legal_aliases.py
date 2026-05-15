"""
Legal term alias table — Vietnamese / English / canonical.

This module is the single source of truth for cross-language equivalence.
It maps surface forms from both Vietnamese and English legal discourse to
canonical internal keys (e.g. "article", "clause", "section").

Design rules:
- Canonical keys are always lowercase English strings (snake_case for compounds).
- All surface forms are lowercased before matching.
- Aliases are additive: adding new forms never removes existing ones.
- No AI inference — only explicit, curated equivalences from legal sources.

Usage:
    from src.retrieval.legal_aliases import TERM_ALIASES, canonical_term, aliases_for

    canonical_term("điều")   # → "article"
    canonical_term("Khoản")  # → "clause"
    aliases_for("article")   # → {"article", "điều", "art.", "art", ...}
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Optional, Set

# ---------------------------------------------------------------------------
# Core alias table
# ---------------------------------------------------------------------------
# Structure: canonical_key → set of surface aliases (all lowercase)
#
# Canonical keys correspond to the legal hierarchy level they represent.
# Both Vietnamese and English surface forms are included.

TERM_ALIASES: Dict[str, FrozenSet[str]] = {

    # ── Structural hierarchy ──────────────────────────────────────────────

    "chapter": frozenset({
        # English
        "chapter", "chap.", "chap",
        # Vietnamese
        "chương",
    }),

    "part": frozenset({
        # English
        "part", "pt.",
        # Vietnamese
        "phần",
    }),

    "section": frozenset({
        # English
        "section", "sec.", "sec", "sect.", "sect",
        # Vietnamese
        "mục",
    }),

    "article": frozenset({
        # English
        "article", "art.", "art", "articles",
        # Vietnamese
        "điều",
    }),

    "clause": frozenset({
        # English
        "clause", "cl.", "cl", "paragraph", "para.", "para", "subsection",
        # Vietnamese
        "khoản",
    }),

    "point": frozenset({
        # English
        "point", "pt", "subpoint", "item",
        # Vietnamese
        "điểm",
    }),

    "annex": frozenset({
        # English
        "annex", "annex.", "schedule", "appendix", "exhibit",
        # Vietnamese
        "phụ lục", "phụ-lục",
    }),

    # ── Document / contract parties ───────────────────────────────────────

    "party_a": frozenset({
        "party a", "bên a", "side a",
    }),

    "party_b": frozenset({
        "party b", "bên b", "side b",
    }),

    # ── Common legal concepts ─────────────────────────────────────────────

    "contract": frozenset({
        "contract", "agreement", "hợp đồng", "hd",
    }),

    "obligation": frozenset({
        "obligation", "duty", "nghĩa vụ", "trách nhiệm",
    }),

    "payment": frozenset({
        "payment", "fee", "remuneration", "thanh toán", "phí",
    }),

    "confidentiality": frozenset({
        "confidentiality", "nda", "non-disclosure", "bảo mật", "bí mật",
    }),

    "intellectual_property": frozenset({
        "intellectual property", "ip", "copyright", "sở hữu trí tuệ", "quyền tác giả",
    }),

    "termination": frozenset({
        "termination", "cancellation", "rescission", "chấm dứt", "hủy bỏ",
    }),

    "dispute": frozenset({
        "dispute", "arbitration", "litigation", "tranh chấp", "trọng tài",
    }),

    "governing_law": frozenset({
        "governing law", "applicable law", "choice of law", "luật áp dụng",
    }),

    "liability": frozenset({
        "liability", "indemnity", "indemnification", "bồi thường", "trách nhiệm pháp lý",
    }),

    "force_majeure": frozenset({
        "force majeure", "act of god", "bất khả kháng",
    }),

    "defined_term": frozenset({
        "definition", "defined term", "means", "giải thích", "thuật ngữ", "định nghĩa",
    }),

    # ── Procedural terms ─────────────────────────────────────────────────

    "notice": frozenset({
        "notice", "notification", "thông báo",
    }),

    "amendment": frozenset({
        "amendment", "modification", "sửa đổi", "bổ sung",
    }),

    "effectiveness": frozenset({
        "effective date", "entry into force", "hiệu lực", "ngày có hiệu lực",
    }),

    "warranty": frozenset({
        "warranty", "guarantee", "representation", "bảo đảm", "bảo hành",
    }),

    "penalty": frozenset({
        "penalty", "fine", "sanction", "phạt", "xử phạt",
    }),
}

# ---------------------------------------------------------------------------
# Reverse index: surface form → canonical key
# Built once at module load from TERM_ALIASES above.
# ---------------------------------------------------------------------------

_SURFACE_TO_CANONICAL: Dict[str, str] = {}
for _key, _aliases in TERM_ALIASES.items():
    for _alias in _aliases:
        _SURFACE_TO_CANONICAL[_alias.lower()] = _key
    # The canonical key itself maps to itself
    _SURFACE_TO_CANONICAL[_key.lower()] = _key


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def canonical_term(surface: str) -> Optional[str]:
    """
    Return the canonical key for a surface form, or None if unknown.

    Case-insensitive. Strips surrounding whitespace.

    Examples:
        canonical_term("Điều")  → "article"
        canonical_term("Art.")  → "article"
        canonical_term("mục")   → "section"
        canonical_term("xyz")   → None
    """
    return _SURFACE_TO_CANONICAL.get(surface.strip().lower())


def aliases_for(canonical: str) -> FrozenSet[str]:
    """
    Return all surface aliases for a canonical key, including the key itself.
    Returns empty frozenset if the canonical key is unknown.

    Example:
        aliases_for("article") → frozenset({"article", "điều", "art.", "art", ...})
    """
    return TERM_ALIASES.get(canonical.lower(), frozenset())


def all_aliases_for_canonical(canonical: str) -> Set[str]:
    """
    Like aliases_for but also includes the canonical key itself.
    """
    result: Set[str] = set(aliases_for(canonical))
    result.add(canonical)
    return result


def is_hierarchy_term(surface: str) -> bool:
    """
    Return True if the surface form maps to a structural hierarchy canonical key
    (chapter, part, section, article, clause, point, annex).
    """
    HIERARCHY_KEYS = {"chapter", "part", "section", "article", "clause", "point", "annex"}
    key = canonical_term(surface)
    return key in HIERARCHY_KEYS if key else False


def expand_query_terms(surface_terms: list[str]) -> Set[str]:
    """
    Given a list of surface query terms, return the expanded set including
    all multilingual aliases for each recognized term.

    Unknown terms are returned unchanged, subject to these filters:
    - Empty strings are skipped.
    - Pure numeric strings ("1", "23") are skipped: they appear in nearly every
      chunk and inflate alias hit counts without adding retrieval precision.
      Numeric context is already encoded in the canonical ref ID (e.g. "article_1").
    - Single-character tokens are skipped.

    Example:
        expand_query_terms(["Điều", "payment"])
        → {"điều", "article", "art.", "art", "payment", "thanh toán", "phí", ...}

        expand_query_terms(["article_1", "article", "1"])
        → {"article_1", "article", "điều", "art.", "art", "articles"}
        # "1" is filtered — its role is already captured by "article_1"
    """
    expanded: Set[str] = set()
    for term in surface_terms:
        term_lower = term.strip().lower()
        # Skip empty, single-char, and pure-numeric tokens — too broad to be useful
        if not term_lower or len(term_lower) < 2 or term_lower.isdigit():
            continue
        canonical = canonical_term(term_lower)
        if canonical:
            expanded.update(all_aliases_for_canonical(canonical))
        else:
            expanded.add(term_lower)
    return expanded
