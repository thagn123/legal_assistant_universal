"""
Multilingual evaluation metrics.

Computes MultilingualMetrics from a document's processed artifacts:
  - primary language and confidence from the document profile
  - canonical ref coverage across chunks
  - cross-language retrieval hit rate (from smoke test results)
  - alias edge count from the graph

Usage:
    from src.evaluation.multilingual_metrics import compute_multilingual_metrics

    metrics = compute_multilingual_metrics(
        document=canonical_document,
        chunk_set=chunk_set,
        graph=graph_subgraph,
        cross_lang_results={"Article 1": [result1], "Điều 1": [result1]},
    )
"""

from __future__ import annotations

from typing import Dict, List, Optional

from src.schemas.chunk import ChunkSet
from src.schemas.document import CanonicalDocument
from src.schemas.evaluation import MultilingualMetrics
from src.schemas.graph import GraphSubgraph


def compute_multilingual_metrics(
    document: Optional[CanonicalDocument] = None,
    chunk_set: Optional[ChunkSet] = None,
    graph: Optional[GraphSubgraph] = None,
    cross_lang_results: Optional[Dict[str, list]] = None,
) -> MultilingualMetrics:
    """
    Compute multilingual quality metrics from pipeline artifacts.

    Args:
        document:           CanonicalDocument from structuring stage.
        chunk_set:          ChunkSet from chunking stage.
        graph:              GraphSubgraph from graph building stage.
        cross_lang_results: Dict mapping query string → list of RetrievalResult.
                            Used to compute cross-language hit rate.

    Returns:
        MultilingualMetrics instance.
    """
    m = MultilingualMetrics()

    # ── Language and jurisdiction ────────────────────────────────────────
    if document is not None:
        if document.profile.language_detection:
            ld = document.profile.language_detection
            m.primary_language = ld.language
            m.language_confidence = ld.confidence
            m.jurisdiction = ld.jurisdiction
        elif document.profile.languages:
            # Fallback: use profiler language list
            m.primary_language = document.profile.languages[0] if document.profile.languages else "unknown"
        elif document.metadata.languages:
            m.primary_language = document.metadata.languages[0] if document.metadata.languages else "unknown"

    # ── Canonical ref coverage ───────────────────────────────────────────
    if chunk_set is not None:
        total_canonical_refs = 0
        chunks_with_refs = 0
        chunks_with_language = 0

        for chunk in chunk_set.chunks:
            # canonical_refs field
            refs = getattr(chunk, "canonical_refs", None) or []
            total_canonical_refs += len(refs)
            if refs:
                chunks_with_refs += 1

            # language field
            lang = getattr(chunk, "language", None) or ""
            if lang:
                chunks_with_language += 1

        m.canonical_refs_generated = total_canonical_refs
        m.chunks_with_canonical_refs = chunks_with_refs
        m.chunks_with_language_field = chunks_with_language

    # ── Alias edges ──────────────────────────────────────────────────────
    if graph is not None:
        alias_count = sum(1 for e in graph.edges if e.edge_type == "ALIAS_OF")
        m.alias_edges_added = alias_count

    # ── Cross-language retrieval ─────────────────────────────────────────
    if cross_lang_results is not None:
        m.cross_lang_queries_tested = len(cross_lang_results)
        m.cross_lang_queries_hit = sum(
            1 for results in cross_lang_results.values() if results
        )
        if m.cross_lang_queries_tested > 0:
            m.cross_lang_hit_rate = round(
                m.cross_lang_queries_hit / m.cross_lang_queries_tested, 3
            )

    return m


def compute_chunk_language_distribution(chunk_set: ChunkSet) -> Dict[str, int]:
    """
    Count how many chunks are in each language.

    Returns a dict like {"vi": 12, "en": 3, "": 1}.
    """
    distribution: Dict[str, int] = {}
    for chunk in chunk_set.chunks:
        lang = getattr(chunk, "language", "") or ""
        distribution[lang] = distribution.get(lang, 0) + 1
    return distribution


def compute_canonical_ref_coverage(chunk_set: ChunkSet) -> float:
    """
    Fraction of chunks that have at least one canonical_ref.

    Returns 0.0 if there are no chunks.
    """
    if not chunk_set.chunks:
        return 0.0
    chunks_with_refs = sum(
        1 for c in chunk_set.chunks
        if (getattr(c, "canonical_refs", None) or [])
    )
    return round(chunks_with_refs / len(chunk_set.chunks), 3)


def compute_cross_lang_hit_rate(
    engine,                    # RetrievalEngine (not typed to avoid circular import)
    document: CanonicalDocument,
    opposite_lang_queries: List[str],
) -> float:
    """
    Test whether a set of queries in the opposite language retrieve results.

    For a Vietnamese document, `opposite_lang_queries` would be English queries
    like ["Article 1", "payment terms"] and vice versa.

    Returns fraction of queries that returned ≥1 result.

    Args:
        engine:                  Configured RetrievalEngine over the chunk set.
        document:                CanonicalDocument (used for language context in logs).
        opposite_lang_queries:   Queries in the non-primary language.

    Returns:
        Float 0.0–1.0.
    """
    if not opposite_lang_queries:
        return 0.0
    return engine.hit_rate(opposite_lang_queries, min_results=1)
