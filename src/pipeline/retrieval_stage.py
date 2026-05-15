"""
Stage 8: Retrieval smoke test

Multilingual retrieval smoke test over chunks using the RetrievalEngine.

Design rules:
- queries is always a LOCAL copy; config.smoke_test_queries is never mutated.
- All-queries-fail → STATUS_WARNING (never STATUS_FAIL from smoke test alone).
- Cross-language hit rate is computed separately and logged but does not gate status.
- Uses RetrievalEngine with canonical ref + alias expansion.
"""

from __future__ import annotations

from typing import Dict, List

from src.pipeline.interfaces import StageContext, StageOutput
from src.schemas.chunk import Chunk, ChunkSet
from src.schemas.document import CanonicalDocument
from src.schemas.evaluation import STATUS_PASS, STATUS_WARNING
from src.retrieval.retrieval_engine import RetrievalEngine


# ---------------------------------------------------------------------------
# Stage 8: Retrieval smoke test
# ---------------------------------------------------------------------------


def stage_retrieval_smoke_test(ctx: StageContext) -> StageOutput:
    """
    Multilingual retrieval smoke test over chunks using the RetrievalEngine.

    Upgrades over the previous keyword-only test:
    - Uses RetrievalEngine with canonical ref + alias expansion
    - Generates language-appropriate primary queries
    - Also tests cross-language queries (English queries against a VI doc, and vice versa)
    - Logs retrieval diagnostics via ctx.logger

    Design rules:
    - queries is always a LOCAL copy; config.smoke_test_queries is never mutated.
    - All-queries-fail → STATUS_WARNING (never STATUS_FAIL from smoke test alone).
    - Cross-language hit rate is computed separately and logged but does not gate status.
    """
    if not ctx.config.enable_retrieval_smoke_test:
        return StageOutput(
            stage_name="retrieval_smoke_test",
            status="skipped",
            summary="Retrieval smoke test disabled by config.",
        )

    chunk_set: ChunkSet = ctx.get("chunk_set")
    if chunk_set is None or not chunk_set.chunks:
        return StageOutput(
            stage_name="retrieval_smoke_test",
            status=STATUS_WARNING,
            summary="No chunks available for smoke test.",
            warnings=["chunk_set is empty; no retrieval test possible"],
        )

    document: CanonicalDocument = ctx.get("document")

    # Build the multilingual retrieval engine (debug=True for logging)
    engine = RetrievalEngine(chunk_set, debug=True)

    # ----------------------------------------------------------------
    # Step 1: Determine document language
    # ----------------------------------------------------------------
    doc_lang = "en"
    if document:
        if document.profile.language_detection:
            ld = document.profile.language_detection
            if ld.confidence >= 0.5 and ld.language not in ("unknown",):
                doc_lang = ld.language
        elif document.profile.languages:
            doc_lang = document.profile.languages[0]

    # ----------------------------------------------------------------
    # Step 2: Build primary queries (in document language)
    # Always work with a LOCAL copy — never mutate config
    # ----------------------------------------------------------------
    primary_queries: List[str] = list(ctx.config.smoke_test_queries)  # copy, not reference

    if not primary_queries:
        primary_queries = _build_adaptive_queries(doc_lang, document)

    # ----------------------------------------------------------------
    # Step 3: Build cross-language queries (opposite language)
    # These test canonical ref matching across language boundaries
    # ----------------------------------------------------------------
    cross_lang_queries: List[str] = []
    if document and document.articles:
        if doc_lang == "vi":
            for art in document.articles[:3]:
                if art.number:
                    cross_lang_queries.append(f"Article {art.number}")
        elif doc_lang == "en":
            for art in document.articles[:3]:
                if art.number:
                    cross_lang_queries.append(f"Điều {art.number}")

    # ----------------------------------------------------------------
    # Step 4: Run primary retrieval
    # ----------------------------------------------------------------
    primary_results: List[int] = []
    failed_primary: List[str] = []

    for query in primary_queries[:10]:
        hits = engine.search(query)
        primary_results.append(len(hits))
        if not hits:
            failed_primary.append(query)

        # Log retrieval diagnostics
        if engine.last_debug_log:
            log = engine.last_debug_log
            ctx.logger.info(
                f"Smoke query: {query!r} → {len(hits)} hits "
                f"(canonical={log.canonical_hits}, alias={log.alias_hits}, "
                f"keyword={log.keyword_hits})",
                stage="retrieval_smoke_test",
            )

    avg_hits = sum(primary_results) / max(1, len(primary_results))
    hit_rate = (len(primary_queries) - len(failed_primary)) / max(1, len(primary_queries))

    # ----------------------------------------------------------------
    # Step 5: Run cross-language retrieval (advisory, not gating)
    # ----------------------------------------------------------------
    cross_lang_results: Dict[str, List] = {}
    for query in cross_lang_queries[:5]:
        hits = engine.search(query)
        cross_lang_results[query] = hits
        if engine.last_debug_log:
            log = engine.last_debug_log
            ctx.logger.info(
                f"Cross-lang query: {query!r} → {len(hits)} hits "
                f"(canonical={log.canonical_hits}, alias={log.alias_hits})",
                stage="retrieval_smoke_test",
            )

    cross_lang_hit_rate = 0.0
    if cross_lang_queries:
        cross_hits = sum(1 for r in cross_lang_results.values() if r)
        cross_lang_hit_rate = cross_hits / len(cross_lang_queries)

    # ----------------------------------------------------------------
    # Step 6: Determine status (primary queries only gate status)
    # ----------------------------------------------------------------
    if hit_rate >= 0.6:
        status = STATUS_PASS
    else:
        status = STATUS_WARNING

    # Build warnings
    warnings: List[str] = [f"No results for query: '{q}'" for q in failed_primary]
    if cross_lang_queries and cross_lang_hit_rate < 0.5:
        failed_cross = [q for q, r in cross_lang_results.items() if not r]
        for q in failed_cross:
            warnings.append(f"Cross-language query missed: '{q}'")

    summary = (
        f"Tested {len(primary_queries)} queries ({doc_lang}) — "
        f"{len(primary_queries) - len(failed_primary)} hit, {len(failed_primary)} missed "
        f"(hit rate {hit_rate:.0%}, avg {avg_hits:.1f} chunks/query)"
    )
    if cross_lang_queries:
        summary += (
            f" | Cross-lang: {int(cross_lang_hit_rate * 100)}% "
            f"({len(cross_lang_queries)} queries)"
        )

    ctx.put("cross_lang_retrieval_results", cross_lang_results)

    return StageOutput(
        stage_name="retrieval_smoke_test",
        status=status,
        summary=summary,
        warnings=warnings,
        output_summary={
            "doc_language": doc_lang,
            "queries_tested": len(primary_queries),
            "queries_with_results": len(primary_queries) - len(failed_primary),
            "queries_failed": failed_primary,
            "avg_result_count": round(avg_hits, 1),
            "hit_rate": round(hit_rate, 3),
            "cross_lang_queries_tested": len(cross_lang_queries),
            "cross_lang_hit_rate": round(cross_lang_hit_rate, 3),
        },
    )


def _keyword_search(query: str, chunk_set: ChunkSet) -> List[Chunk]:
    """Simple case-insensitive keyword search over chunk content. Used as fallback."""
    query_lower = query.lower()
    return [c for c in chunk_set.chunks if query_lower in c.content.lower()]


def _build_adaptive_queries(doc_lang: str, document: CanonicalDocument) -> List[str]:
    """
    Build smoke-test queries based on the document's actual structure.

    Only includes structural-level terms (chương/chapter, mục/section, etc.) when
    that level actually appears in the document's section labels. This prevents
    false-positive warnings for levels the document simply does not use.
    Body-content terms (điều/article, khoản/clause, payment keywords, etc.) are
    included whenever the corresponding structure objects exist.
    """
    queries: List[str] = []

    if doc_lang == "vi":
        if document and document.articles:
            queries.extend(["điều", "hợp đồng", "bên", "nghĩa vụ", "thanh toán"])
        if document and document.clauses:
            queries.append("khoản")
        # Only add section-level structural terms if that level is present in labels
        if document and document.sections:
            labels = [s.label.lower() for s in document.sections if s.label]
            if any("chương" in l for l in labels):
                queries.append("chương")
            if any("mục" in l and "chương" not in l for l in labels):
                queries.append("mục")
            if any("phần" in l for l in labels):
                queries.append("phần")

    elif doc_lang == "mixed":
        queries.extend(["điều", "article", "hợp đồng", "agreement"])
        if document and document.clauses:
            queries.extend(["khoản", "clause"])

    else:  # English default
        if document and document.articles:
            queries.extend(["article", "agreement", "obligation", "payment"])
        if document and document.clauses:
            queries.append("clause")
        if document and document.sections:
            labels = [s.label.lower() for s in document.sections if s.label]
            if any("chapter" in l for l in labels):
                queries.append("chapter")
            if any("section" in l and "chapter" not in l for l in labels):
                queries.append("section")
            if any("part" in l for l in labels):
                queries.append("part")

    # Fallback: if no structure detected, use a safe minimal set
    if not queries:
        queries = ["article", "clause"] if doc_lang == "en" else ["điều", "khoản"]

    return queries
