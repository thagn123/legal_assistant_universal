"""
Canonical reference ID generator and matcher.

Canonical IDs are stable, language-independent keys attached to legal
structure objects (Article, Clause, Section) so that cross-language queries
can match them regardless of surface language.

Example:
  Article with label "Điều 1" → canonical_id = "article_1"
  Article with label "Article 1" → canonical_id = "article_1"   (same ID)
  Clause with label "Khoản 3" under Article 5 → "article_5_clause_3"
  Clause with label "Clause 3(a)" under Article 5 → "article_5_clause_3_a"

Design rules:
  - IDs are generated from label text using the query_normalizer patterns.
  - If a label cannot be parsed, a fallback sequential ID is generated.
  - Every canonical_id is unique within a document.
  - Parent context is encoded in the ID for clauses and points.
  - IDs are always lowercase snake_case.

Usage:
    from src.retrieval.canonical_references import CanonicalRefBuilder

    builder = CanonicalRefBuilder(document_id="doc_abc")
    article_id = builder.article_ref("Điều 1")            # → "article_1"
    clause_id  = builder.clause_ref("Khoản 3", "Điều 1") # → "article_1_clause_3"
    section_id = builder.section_ref("Chương II")         # → "chapter_2"
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Set

from src.retrieval.query_normalizer import _REF_PATTERN, _ref_match_to_canonical, normalise_number
from src.retrieval.legal_aliases import canonical_term


# ---------------------------------------------------------------------------
# Label → canonical ID
# ---------------------------------------------------------------------------


def label_to_canonical_id(label: str) -> Optional[str]:
    """
    Convert a structure label to a canonical ID.

    Returns None if the label cannot be parsed.

    Examples:
        label_to_canonical_id("Điều 1")         → "article_1"
        label_to_canonical_id("Article 5")      → "article_5"
        label_to_canonical_id("Khoản 3")        → "clause_3"
        label_to_canonical_id("Clause 3(a)")    → "clause_3_a"
        label_to_canonical_id("Chương II")      → "chapter_2"
        label_to_canonical_id("Section IV")     → "section_4"
        label_to_canonical_id("Điểm b")         → "point_b"
    """
    if not label:
        return None
    m = _REF_PATTERN.search(label.lower())
    if m:
        return _ref_match_to_canonical(m)
    return None


def make_canonical_id(
    level: str,
    number: str,
    subletter: Optional[str] = None,
    parent_canonical: Optional[str] = None,
) -> str:
    """
    Build a canonical ID from its components.

    Args:
        level:            canonical hierarchy level ("article", "clause", etc.)
        number:           Arabic or Roman numeral string
        subletter:        optional sub-point letter ("a", "b", "c")
        parent_canonical: canonical ID of parent structure (prepended)

    Examples:
        make_canonical_id("article", "1")          → "article_1"
        make_canonical_id("clause", "3", "a")      → "clause_3_a"
        make_canonical_id("clause", "3", "a",
                          parent_canonical="article_5")
                                                    → "article_5_clause_3_a"
    """
    num_str = normalise_number(number)
    parts = []
    if parent_canonical:
        parts.append(parent_canonical)
    parts.append(level)
    parts.append(num_str)
    if subletter:
        parts.append(subletter.lower())
    return "_".join(parts)


# ---------------------------------------------------------------------------
# Reference builder — tracks used IDs and generates fallbacks
# ---------------------------------------------------------------------------


class CanonicalRefBuilder:
    """
    Stateful builder that generates canonical IDs for one document's structures.

    Tracks used IDs to prevent collisions. When a label cannot be parsed, it
    falls back to a sequential counter.

    Usage:
        builder = CanonicalRefBuilder(document_id="doc_abc123")
        ref = builder.article_ref("Điều 5")    # → "article_5"
        ref = builder.clause_ref("Khoản 3", parent_label="Điều 5")
        # → "article_5_clause_3"
    """

    def __init__(self, document_id: str) -> None:
        self.document_id = document_id
        self._used_ids: Set[str] = set()
        self._counters: Dict[str, int] = {}

    # ── Internal helpers ─────────────────────────────────────────────────

    def _make_unique(self, base_id: str) -> str:
        """Ensure the ID is unique within the document; append suffix if needed."""
        if base_id not in self._used_ids:
            self._used_ids.add(base_id)
            return base_id
        suffix = 2
        while f"{base_id}_{suffix}" in self._used_ids:
            suffix += 1
        unique = f"{base_id}_{suffix}"
        self._used_ids.add(unique)
        return unique

    def _next_counter(self, level: str) -> int:
        self._counters[level] = self._counters.get(level, 0) + 1
        return self._counters[level]

    def _fallback_id(self, level: str, canonical_parent: Optional[str] = None) -> str:
        """Generate a fallback sequential ID when label cannot be parsed."""
        n = self._next_counter(level)
        base = f"{level}_{n}"
        if canonical_parent:
            base = f"{canonical_parent}_{base}"
        return self._make_unique(base)

    # ── Public methods ───────────────────────────────────────────────────

    def section_ref(self, label: str) -> str:
        """
        Generate canonical ID for a section/chapter/part from its label.

        Examples:
            section_ref("Chương I")  → "chapter_1"
            section_ref("Part II")   → "part_2"
            section_ref("Mục 3")     → "section_3"
        """
        parsed = label_to_canonical_id(label)
        if parsed:
            return self._make_unique(parsed)
        return self._fallback_id("section")

    def article_ref(self, label: str) -> str:
        """
        Generate canonical ID for an article from its label.

        Examples:
            article_ref("Điều 1")   → "article_1"
            article_ref("Article 5")→ "article_5"
        """
        parsed = label_to_canonical_id(label)
        if parsed:
            return self._make_unique(parsed)
        return self._fallback_id("article")

    def clause_ref(
        self,
        label: str,
        parent_label: Optional[str] = None,
        parent_canonical: Optional[str] = None,
    ) -> str:
        """
        Generate canonical ID for a clause from its label and optional parent.

        Args:
            label:            e.g. "Khoản 3", "Clause 3(a)"
            parent_label:     e.g. "Điều 5" — used to derive parent canonical if
                              parent_canonical not supplied
            parent_canonical: explicit parent canonical ID (preferred over parent_label)

        Examples:
            clause_ref("Khoản 3", parent_label="Điều 5")
            → "article_5_clause_3"

            clause_ref("Clause 3(a)", parent_canonical="article_5")
            → "article_5_clause_3_a"
        """
        effective_parent: Optional[str] = parent_canonical
        if not effective_parent and parent_label:
            effective_parent = label_to_canonical_id(parent_label)

        parsed = label_to_canonical_id(label)
        if parsed:
            if effective_parent and not parsed.startswith(effective_parent):
                full = f"{effective_parent}_{parsed}"
            else:
                full = parsed
            return self._make_unique(full)
        return self._fallback_id("clause", canonical_parent=effective_parent)

    def point_ref(
        self,
        label: str,
        parent_clause_canonical: Optional[str] = None,
    ) -> str:
        """
        Generate canonical ID for a point (sub-clause) from its label.

        Examples:
            point_ref("Điểm a", "article_5_clause_3")
            → "article_5_clause_3_point_a"
        """
        parsed = label_to_canonical_id(label)
        if parsed:
            if parent_clause_canonical and not parsed.startswith(parent_clause_canonical):
                full = f"{parent_clause_canonical}_{parsed}"
            else:
                full = parsed
            return self._make_unique(full)
        return self._fallback_id("point", canonical_parent=parent_clause_canonical)


# ---------------------------------------------------------------------------
# Canonical reference set helpers
# ---------------------------------------------------------------------------


def refs_from_structure_path(path: List[str]) -> List[str]:
    """
    Extract canonical references from a structure path list.

    A structure path is a list of labels like:
        ["Chương I", "Điều 5", "Khoản 3"]

    Returns canonical IDs in order:
        ["chapter_1", "article_5", "clause_3"]

    Args:
        path: list of structure label strings

    Returns:
        List of canonical IDs (may be shorter than path if some labels
        cannot be parsed).
    """
    result: List[str] = []
    for label in path:
        cid = label_to_canonical_id(label)
        if cid:
            result.append(cid)
    return result


def canonical_refs_for_chunk(
    structure_path: List[str],
    content: str,
) -> List[str]:
    """
    Build the full set of canonical references for a chunk.

    Combines:
    1. Refs derived from the structure path
    2. Refs extracted from the chunk content text

    Args:
        structure_path: list of structure label strings for this chunk
        content:        chunk content text

    Returns:
        Deduplicated list of canonical IDs.
    """
    from src.retrieval.query_normalizer import extract_refs

    refs: List[str] = []
    seen: Set[str] = set()

    # From structure path
    for ref in refs_from_structure_path(structure_path):
        if ref not in seen:
            refs.append(ref)
            seen.add(ref)

    # From content text
    for ref in extract_refs(content):
        if ref not in seen:
            refs.append(ref)
            seen.add(ref)

    return refs
