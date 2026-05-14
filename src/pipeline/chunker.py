"""
Stage 6: Chunking

Structure-aware chunk generation implementing the decision tree from
docs/chunking/chunking-strategies.md.

Design rules:
- Legal structure (articles, clauses) is never split at the wrong boundary.
- Tables produce one chunk per table (never merged into text).
- Chunks include hierarchy path in content so keyword searches on
  structure terms always hit ("điều", "chương", "article", etc.).
- Language metadata is derived from the document's formal language detection.
"""

from __future__ import annotations

from typing import List

from src.config import ChunkingStrategy
from src.pipeline.interfaces import StageContext, StageOutput
from src.schemas.chunk import Chunk, ChunkSet, ChunkingDecision
from src.schemas.document import Article, CanonicalDocument, DocumentProfile
from src.schemas.evaluation import STATUS_FAIL, STATUS_PASS, STATUS_WARNING
from src.utils import trace as T
from src.retrieval.canonical_references import canonical_refs_for_chunk


# ---------------------------------------------------------------------------
# Stage 6: Chunking
# ---------------------------------------------------------------------------


def stage_chunking(ctx: StageContext) -> StageOutput:
    """
    Apply chunking strategy from docs/chunking/chunking-strategies.md.
    Preserves legal structure: articles and clauses are never split at the wrong boundary.
    """
    document: CanonicalDocument = ctx.get("document")
    if document is None:
        return StageOutput(
            stage_name="chunking",
            status=STATUS_FAIL,
            summary="No document object in context",
            errors=["canonical_structuring must run before chunking"],
        )

    cfg = ctx.config
    profile = document.profile
    warnings: List[str] = []

    # Choose chunking strategy using the decision tree from the docs
    strategy = _choose_chunk_strategy(profile, document)
    decision = ChunkingDecision(
        document_id=ctx.document_id,
        strategy=strategy,
        secondary_rules=_secondary_rules(document),
        fallback_strategy=_fallback_strategy(strategy),
        routing_signals={
            "page_count": profile.page_count,
            "is_long_document": profile.is_long_document,
            "has_tables": profile.has_tables,
            "table_density": profile.table_density,
            "image_density": profile.image_density,
        },
        decision_confidence=0.85,
        reason_codes=[f"strategy={strategy}"],
        created_at=T.now_iso(),
    )

    ctx.logger.decision(
        stage="chunking",
        decision_type="chunking_strategy",
        value=strategy,
        reason=f"pages={profile.page_count}, long={profile.is_long_document}, tables={profile.has_tables}",
    )

    # Build chunks
    chunks: List[Chunk] = []
    chunk_idx = 0

    # --- Text chunks: group by structural unit (article → group of blocks) ---
    if document.articles:
        for article in document.articles:
            # Collect all clause IDs that belong to this article so body blocks
            # owned by sub-clauses (Khoản / Điểm) are included in the article chunk.
            article_clause_ids = {
                c.clause_id for c in document.clauses
                if c.parent_article_id == article.article_id
            }

            # Collect body blocks: heading block + direct article body blocks
            # + clause heading blocks + clause body blocks (all under this article)
            body_blocks = [
                b for b in document.blocks
                if b.parent_structure_id == article.article_id
                or b.parent_structure_id in article_clause_ids
                or b.block_id in article.block_ids
            ]
            body_text = "\n\n".join(
                (b.clean_text or b.raw_text)
                for b in body_blocks
                if (b.clean_text or b.raw_text)
            )
            structure_path = _build_path(article, document)

            # Chunk content: include structure path as context header so keyword
            # searches on hierarchy terms ("điều", "chương", "article", etc.) always hit.
            path_header = " › ".join(structure_path)
            content = f"{path_header}\n\n## {article.label}\n\n{body_text}" if body_text \
                else f"{path_header}\n\n## {article.label}"

            # Multilingual: canonical refs and language metadata
            chunk_canonical_refs = canonical_refs_for_chunk(structure_path, content)
            chunk_lang = _get_chunk_language(document)
            hierarchy_path_str = " › ".join(structure_path)

            chunk = Chunk(
                chunk_id=T.make_chunk_id(ctx.document_id, chunk_idx),
                document_id=ctx.document_id,
                chunk_type="text",
                content_format="markdown",
                content=content,
                structure_path=structure_path,
                page_refs=article.page_refs,
                block_refs=[b.block_id for b in body_blocks] or article.block_ids,
                citations=article.citations,
                token_estimate=len(content) // 4,
                confidence=article.confidence.overall,
                degraded=article.confidence.degraded,
                jurisdiction=document.metadata.jurisdiction,
                version_label=document.metadata.version_label or "",
                document_type=document.metadata.document_type,
                language=chunk_lang,
                canonical_refs=chunk_canonical_refs,
                hierarchy_path=hierarchy_path_str,
            )
            chunks.append(chunk)
            chunk_idx += 1
    else:
        # No detected hierarchy: chunk by paragraph groups (fallback)
        CHUNK_BLOCK_SIZE = 10 if not profile.is_long_document else 20
        for i in range(0, max(1, len(document.blocks)), CHUNK_BLOCK_SIZE):
            group = document.blocks[i: i + CHUNK_BLOCK_SIZE]
            if not group:
                continue
            content = "\n\n".join(
                (b.clean_text or b.raw_text)
                for b in group
                if (b.clean_text or b.raw_text)
            )
            avg_conf = sum(b.confidence.overall for b in group) / len(group)
            chunk_canonical_refs = canonical_refs_for_chunk([], content)
            chunk_lang = _get_chunk_language(document)

            chunk = Chunk(
                chunk_id=T.make_chunk_id(ctx.document_id, chunk_idx),
                document_id=ctx.document_id,
                chunk_type="text",
                content_format="markdown",
                content=content,
                structure_path=[],
                page_refs=list({b.page_id for b in group}),
                block_refs=[b.block_id for b in group],
                token_estimate=len(content) // 4,
                confidence=avg_conf,
                degraded=avg_conf < cfg.chunk_authority_threshold,
                jurisdiction=document.metadata.jurisdiction,
                version_label=document.metadata.version_label or "",
                document_type=document.metadata.document_type,
                language=chunk_lang,
                canonical_refs=chunk_canonical_refs,
                hierarchy_path="",
            )
            chunks.append(chunk)
            chunk_idx += 1

    # --- Table chunks: one chunk per table ---
    for table in document.tables:
        content = table.projection_text or table.markdown or "[table]"
        chunk_canonical_refs = canonical_refs_for_chunk([], content)
        chunk_lang = _get_chunk_language(document)

        chunk = Chunk(
            chunk_id=T.make_chunk_id(ctx.document_id, chunk_idx),
            document_id=ctx.document_id,
            chunk_type="table",
            content_format="markdown",
            content=content,
            structure_path=[],
            page_refs=table.page_refs,
            table_refs=[table.table_id],
            token_estimate=len(content) // 4,
            confidence=table.confidence.overall,
            degraded=table.confidence.degraded,
            jurisdiction=document.metadata.jurisdiction,
            version_label=document.metadata.version_label or "",
            document_type=document.metadata.document_type,
            language=chunk_lang,
            canonical_refs=chunk_canonical_refs,
            hierarchy_path="",
        )
        chunks.append(chunk)
        chunk_idx += 1

    degraded_count = sum(1 for c in chunks if c.degraded)
    chunk_set = ChunkSet(
        document_id=ctx.document_id,
        chunks=chunks,
        chunking_decision=decision,
        total_chunks=len(chunks),
        degraded_chunks=degraded_count,
        strategy_used=strategy,
        created_at=T.now_iso(),
    )
    ctx.put("chunk_set", chunk_set)

    return StageOutput(
        stage_name="chunking",
        status=STATUS_WARNING if warnings else STATUS_PASS,
        summary=f"{len(chunks)} chunks ({degraded_count} degraded) using strategy={strategy}",
        warnings=warnings,
        output_summary={
            "total_chunks": len(chunks),
            "text_chunks": len(chunk_set.text_chunks()),
            "table_chunks": len(chunk_set.table_chunks()),
            "degraded_chunks": degraded_count,
            "strategy": strategy,
        },
    )


# ---------------------------------------------------------------------------
# Chunking helpers
# ---------------------------------------------------------------------------


def _get_chunk_language(document: CanonicalDocument) -> str:
    """
    Determine the primary language for chunks in a document.

    Uses the formal language_detection result if available (confidence >= 0.5),
    otherwise falls back to the first entry in profile.languages.
    """
    if document.profile.language_detection:
        ld = document.profile.language_detection
        if ld.confidence >= 0.5 and ld.language not in ("unknown",):
            return ld.language
    langs = document.profile.languages or document.metadata.languages
    return langs[0] if langs else "en"


def _choose_chunk_strategy(
    profile: DocumentProfile, document: CanonicalDocument
) -> str:
    """Implement the chunking decision tree from docs."""
    structure_score = 0.8 if document.has_structure() else 0.3
    if structure_score >= 0.7 and profile.table_density <= 0.2 and profile.image_density <= 0.2:
        return (
            ChunkingStrategy.LONG_LOCAL_STRUCTURAL if profile.is_long_document
            else ChunkingStrategy.STRUCTURAL
        )
    if structure_score >= 0.5 and profile.is_long_document:
        return ChunkingStrategy.LEGAL_AWARE
    if profile.table_density >= 0.4 and profile.layout_complexity_score <= 0.5:
        return ChunkingStrategy.TABLE_AWARE
    if profile.image_density >= 0.3 or (profile.scan_quality_score < 0.5):
        return ChunkingStrategy.CONSERVATIVE_FALLBACK
    if profile.layout_complexity_score >= 0.7:
        return ChunkingStrategy.MIXED_GROUP
    return ChunkingStrategy.SEMANTIC


def _secondary_rules(document: CanonicalDocument) -> List[str]:
    rules = []
    if document.tables:
        rules.append("enforce_table_header_preservation")
    if document.images:
        rules.append("create_evidence_sibling_chunks")
    return rules


def _fallback_strategy(strategy: str) -> str:
    fallback_map = {
        ChunkingStrategy.STRUCTURAL:            ChunkingStrategy.LEGAL_AWARE,
        ChunkingStrategy.LONG_LOCAL_STRUCTURAL: ChunkingStrategy.LEGAL_AWARE,
        ChunkingStrategy.LEGAL_AWARE:           ChunkingStrategy.SEMANTIC,
        ChunkingStrategy.TABLE_AWARE:           ChunkingStrategy.MIXED_GROUP,
        ChunkingStrategy.MIXED_GROUP:           ChunkingStrategy.CONSERVATIVE_FALLBACK,
        ChunkingStrategy.SEMANTIC:              ChunkingStrategy.CONSERVATIVE_FALLBACK,
        ChunkingStrategy.CONSERVATIVE_FALLBACK: ChunkingStrategy.CONSERVATIVE_FALLBACK,
    }
    return fallback_map.get(strategy, ChunkingStrategy.CONSERVATIVE_FALLBACK)


def _build_path(article: Article, document: CanonicalDocument) -> List[str]:
    path = []
    if article.parent_section_id:
        for sec in document.sections:
            if sec.section_id == article.parent_section_id:
                path.append(sec.label or sec.title or sec.section_id)
                break
    path.append(article.label or article.article_id)
    return path
