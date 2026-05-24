"""
Stage 6: Chunking

Structure-aware chunk generation implementing the decision tree from
docs/chunking/chunking-strategies.md.

Design rules:
- Legal structure (articles, clauses) is never split at the wrong boundary.
- Article number and title are NEVER separated across chunk boundaries.
- When an article exceeds chunk_max_tokens AND has clauses, it is split by
  clause with the article heading carried into each sub-chunk as context.
- Tables produce one chunk per table, linked to their parent article via
  sibling_chunk_ids / parent_chunk_id.
- Images with readable OCR text produce evidence chunks.
- Chunks include hierarchy path in content so keyword searches on
  structure terms always hit ("điều", "chương", "article", etc.).
- Language metadata is derived from the document's formal language detection.
- A validation pass after generation flags empty chunks as degraded.
"""

from __future__ import annotations

from typing import Dict, List

from src.config import ChunkingStrategy
from src.pipeline.interfaces import StageContext, StageOutput
from src.schemas.chunk import Chunk, ChunkSet, ChunkingDecision
from src.schemas.document import Article, CanonicalDocument, Clause, DocumentProfile
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

    Phase 5 additions:
    - Token-limit enforcement: articles > chunk_max_tokens are split by clause.
    - Table sibling linking: table chunks carry parent_chunk_id pointing to their article.
    - Image evidence chunks for images with OCR text.
    - Validation pass: empty chunks are flagged as degraded.
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

    chunk_lang = _get_chunk_language(document)
    chunks: List[Chunk] = []
    chunk_idx = 0

    # Build clause lookup: article_id → list of Clause objects (ordered)
    article_clauses: Dict[str, List[Clause]] = {}
    for clause in document.clauses:
        if clause.parent_article_id:
            article_clauses.setdefault(clause.parent_article_id, []).append(clause)

    # Build child-clause lookup from parent_clause_id links (structurer may leave
    # child_clause_ids unpopulated, so we derive it dynamically here).
    child_clause_map: Dict[str, List[str]] = {}
    for clause in document.clauses:
        if clause.parent_clause_id:
            child_clause_map.setdefault(clause.parent_clause_id, []).append(clause.clause_id)

    # Track which table_ids have been assigned a parent_chunk_id so the table
    # chunk loop can set it correctly.
    table_parent_map: Dict[str, str] = {}  # table_id → parent article chunk_id

    # ----------------------------------------------------------------
    # Article coverage guard
    # ----------------------------------------------------------------
    # If structurer detected articles but they cover only a small fraction
    # of the document's blocks (e.g. a single citation in a 173-block
    # appendix), the structural chunker would drop the unassigned blocks
    # entirely. Detect that case and fall back to paragraph-group chunking
    # so every block ends up in some chunk.
    if document.articles:
        # Count ALL blocks belonging to articles: heading blocks (in art.block_ids)
        # AND body blocks (blocks whose parent_structure_id points to an article or clause).
        # The original check only counted heading blocks (1 per article), which caused
        # nearly all documents to incorrectly fall back to paragraph-group chunking.
        article_ids = {art.article_id for art in document.articles}
        clause_ids_set = {c.clause_id for c in document.clauses}
        heading_block_ids: set = set()
        for art in document.articles:
            heading_block_ids.update(art.block_ids)
        for clause in document.clauses:
            heading_block_ids.update(clause.block_ids)
        article_block_count = sum(
            1 for b in document.blocks
            if b.block_id in heading_block_ids
            or getattr(b, "parent_structure_id", None) in article_ids
            or getattr(b, "parent_structure_id", None) in clause_ids_set
        )
        total_blocks = max(1, len(document.blocks))
        article_coverage = article_block_count / total_blocks
        # Threshold: if articles cover < 30% of blocks, treat as no-structure.
        if article_coverage < 0.30:
            ctx.logger.info(
                f"Article coverage {article_coverage:.0%} below threshold "
                f"({len(document.articles)} articles covering "
                f"{article_block_count}/{total_blocks} blocks); "
                "falling back to paragraph-group chunking.",
                stage="chunking",
            )
            warnings.append(
                f"Low article coverage ({article_coverage:.0%}); "
                "using paragraph-group fallback to keep all blocks in chunks."
            )
            # Drop structural artefacts so the `else` branch below activates.
            document.articles = []
            document.clauses = []
            strategy = ChunkingStrategy.SEMANTIC

    # ----------------------------------------------------------------
    # Form-section chunking: one chunk per mẫu/biểu mẫu section
    # Activates when the document has form sections but no articles
    # (e.g. TT55/2026/TT-BTC appendix with 49 official investment forms)
    # ----------------------------------------------------------------
    form_sections = [s for s in document.sections if s.section_kind == "form"]
    if form_sections and not document.articles:
        ctx.logger.info(
            f"Form-section chunking: {len(form_sections)} form sections detected; "
            "creating one chunk per form section.",
            stage="chunking",
        )

        # Group blocks by their parent_structure_id
        section_block_map: Dict[str, List] = {s.section_id: [] for s in form_sections}
        preamble_blocks: List = []
        for b in document.blocks:
            pid = getattr(b, "parent_structure_id", None)
            if pid in section_block_map:
                section_block_map[pid].append(b)
            else:
                preamble_blocks.append(b)

        # Preamble chunk (document header / introductory text before first form)
        if preamble_blocks:
            preamble_text = "\n\n".join(
                _block_text(b) for b in preamble_blocks if _block_text(b)
            )
            if preamble_text:
                seen: set = set()
                preamble_pages: List[str] = []
                for b in preamble_blocks:
                    if b.page_id and b.page_id not in seen:
                        seen.add(b.page_id)
                        preamble_pages.append(b.page_id)
                chunk = Chunk(
                    chunk_id=T.make_chunk_id(ctx.document_id, chunk_idx),
                    document_id=ctx.document_id,
                    chunk_type="text",
                    content_format="markdown",
                    content=preamble_text,
                    structure_path=[],
                    page_refs=preamble_pages,
                    block_refs=[b.block_id for b in preamble_blocks],
                    token_estimate=len(preamble_text) // 4,
                    confidence=1.0,
                    degraded=False,
                    jurisdiction=document.metadata.jurisdiction,
                    version_label=document.metadata.version_label or "",
                    document_type=document.metadata.document_type,
                    language=chunk_lang,
                    canonical_refs=canonical_refs_for_chunk([], preamble_text),
                    hierarchy_path="",
                )
                chunks.append(chunk)
                chunk_idx += 1

        # One chunk per form section
        for section in form_sections:
            section_blocks = section_block_map.get(section.section_id, [])
            body_text = "\n\n".join(
                _block_text(b) for b in section_blocks if _block_text(b)
            )
            form_num = section.number or ""
            form_title = section.title or section.label or ""
            if form_num and form_title:
                heading = f"Mẫu {form_num}"
                content = f"## {heading} — {form_title}\n\n{body_text}" if body_text else f"## {heading} — {form_title}"
                structure_path = [heading, form_title]
                hierarchy_path_str = f"{heading} — {form_title}"
            elif form_num:
                heading = f"Mẫu {form_num}"
                content = f"## {heading}\n\n{body_text}" if body_text else f"## {heading}"
                structure_path = [heading]
                hierarchy_path_str = heading
            else:
                content = f"## {form_title}\n\n{body_text}" if body_text else f"## {form_title}"
                structure_path = [form_title]
                hierarchy_path_str = form_title

            seen_p: set = set()
            ordered_pages: List[str] = []
            for b in section_blocks:
                if b.page_id and b.page_id not in seen_p:
                    seen_p.add(b.page_id)
                    ordered_pages.append(b.page_id)
            if section.page_refs:
                for pr in section.page_refs:
                    if pr not in seen_p:
                        ordered_pages.append(pr)

            avg_conf = (
                sum(b.confidence.overall for b in section_blocks) / len(section_blocks)
                if section_blocks else 1.0
            )
            chunk_canonical_refs = canonical_refs_for_chunk(structure_path, content)
            chunk = Chunk(
                chunk_id=T.make_chunk_id(ctx.document_id, chunk_idx),
                document_id=ctx.document_id,
                chunk_type="text",
                content_format="markdown",
                content=content,
                structure_path=structure_path,
                page_refs=ordered_pages,
                block_refs=[b.block_id for b in section_blocks],
                token_estimate=len(content) // 4,
                confidence=avg_conf,
                degraded=avg_conf < cfg.chunk_authority_threshold,
                jurisdiction=document.metadata.jurisdiction,
                version_label=document.metadata.version_label or "",
                document_type=document.metadata.document_type,
                language=chunk_lang,
                canonical_refs=chunk_canonical_refs,
                hierarchy_path=hierarchy_path_str,
            )
            chunks.append(chunk)
            chunk_idx += 1

    # ----------------------------------------------------------------
    # Text chunks: group by structural unit (article → clause → blocks)
    # Skipped when form-section chunking already ran above.
    # ----------------------------------------------------------------
    elif document.articles:
        for article in document.articles:
            clauses_for_article = article_clauses.get(article.article_id, [])
            clause_ids_for_article = {c.clause_id for c in clauses_for_article}

            # Collect all blocks that belong to this article (direct or via sub-clauses)
            body_blocks = [
                b for b in document.blocks
                if b.parent_structure_id == article.article_id
                or b.parent_structure_id in clause_ids_for_article
                or b.block_id in article.block_ids
            ]
            body_text = "\n\n".join(
                _block_text(b)
                for b in body_blocks
                if _block_text(b)
            )
            structure_path = _build_path(article, document)
            path_header = " › ".join(structure_path)
            content = (
                f"{path_header}\n\n## {article.label}\n\n{body_text}"
                if body_text
                else f"{path_header}\n\n## {article.label}"
            )
            token_est = len(content) // 4
            chunk_canonical_refs = canonical_refs_for_chunk(structure_path, content)
            hierarchy_path_str = " › ".join(structure_path)

            if token_est <= cfg.chunk_max_tokens or not clauses_for_article:
                # ---- Single-chunk article (normal case) ----
                article_chunk_id = T.make_chunk_id(ctx.document_id, chunk_idx)
                chunk = Chunk(
                    chunk_id=article_chunk_id,
                    document_id=ctx.document_id,
                    chunk_type="text",
                    content_format="markdown",
                    content=content,
                    structure_path=structure_path,
                    page_refs=article.page_refs,
                    block_refs=[b.block_id for b in body_blocks] or article.block_ids,
                    citations=article.citations,
                    token_estimate=token_est,
                    confidence=article.confidence.overall,
                    degraded=article.confidence.degraded,
                    jurisdiction=document.metadata.jurisdiction,
                    version_label=document.metadata.version_label or "",
                    document_type=document.metadata.document_type,
                    language=chunk_lang,
                    canonical_refs=chunk_canonical_refs,
                    hierarchy_path=hierarchy_path_str,
                )
                if token_est > cfg.chunk_max_tokens:
                    # Oversized but no clauses — flag it, don't fail
                    chunk.degraded_reasons.append("exceeds_token_limit_no_clauses")
                    warnings.append(
                        f"Article '{article.label}' exceeds token limit "
                        f"({token_est} tokens) but has no clauses to split on."
                    )
                # Record this chunk_id for table linking
                for tid in article.table_ids:
                    table_parent_map[tid] = article_chunk_id
                chunks.append(chunk)
                chunk_idx += 1

            else:
                # ---- Multi-chunk article: split by clause ----
                # Parent chunk: article heading + intro blocks (not owned by any clause)
                intro_blocks = [
                    b for b in body_blocks
                    if b.parent_structure_id == article.article_id
                    or b.block_id in article.block_ids
                ]
                intro_text = "\n\n".join(
                    _block_text(b)
                    for b in intro_blocks
                    if _block_text(b)
                )
                parent_content = (
                    f"{path_header}\n\n## {article.label}\n\n{intro_text}"
                    if intro_text
                    else f"{path_header}\n\n## {article.label}"
                )
                parent_chunk_id = T.make_chunk_id(ctx.document_id, chunk_idx)
                chunk_idx += 1

                # Build clause sub-chunks first to collect their IDs
                clause_chunks: List[Chunk] = []
                for clause in clauses_for_article:
                    clause_block_ids = set(clause.block_ids)
                    # Include direct child clause IDs from both schema field and
                    # the dynamically built map (structurer may not populate the field).
                    child_clause_ids = set(clause.child_clause_ids) | set(
                        child_clause_map.get(clause.clause_id, [])
                    )
                    clause_blocks = [
                        b for b in document.blocks
                        if b.block_id in clause_block_ids
                        or b.parent_structure_id == clause.clause_id
                        or b.parent_structure_id in child_clause_ids
                    ]
                    clause_text = "\n\n".join(
                        _block_text(b)
                        for b in clause_blocks
                        if _block_text(b)
                    )
                    if not clause_text:
                        continue
                    clause_structure_path = structure_path + [clause.label or clause.clause_id]
                    clause_path_header = " › ".join(clause_structure_path)
                    # Carry article heading as context prefix (hierarchy carryover)
                    clause_content = (
                        f"{clause_path_header}\n\n"
                        f"[{article.label}]\n\n"
                        f"{clause_text}"
                    )
                    clause_refs = canonical_refs_for_chunk(clause_structure_path, clause_content)
                    clause_chunk_id = T.make_chunk_id(ctx.document_id, chunk_idx)
                    clause_chunk = Chunk(
                        chunk_id=clause_chunk_id,
                        document_id=ctx.document_id,
                        chunk_type="text",
                        content_format="markdown",
                        content=clause_content,
                        structure_path=clause_structure_path,
                        parent_chunk_id=parent_chunk_id,
                        page_refs=clause.page_refs,
                        block_refs=[b.block_id for b in clause_blocks],
                        citations=clause.citations,
                        token_estimate=len(clause_content) // 4,
                        confidence=clause.confidence.overall,
                        degraded=clause.confidence.degraded,
                        jurisdiction=document.metadata.jurisdiction,
                        version_label=document.metadata.version_label or "",
                        document_type=document.metadata.document_type,
                        language=chunk_lang,
                        canonical_refs=clause_refs,
                        hierarchy_path=" › ".join(clause_structure_path),
                    )
                    clause_chunks.append(clause_chunk)
                    chunk_idx += 1

                clause_chunk_ids = [c.chunk_id for c in clause_chunks]

                parent_chunk = Chunk(
                    chunk_id=parent_chunk_id,
                    document_id=ctx.document_id,
                    chunk_type="text",
                    content_format="markdown",
                    content=parent_content,
                    structure_path=structure_path,
                    sibling_chunk_ids=clause_chunk_ids,
                    page_refs=article.page_refs,
                    block_refs=[b.block_id for b in intro_blocks] or article.block_ids,
                    citations=article.citations,
                    token_estimate=len(parent_content) // 4,
                    confidence=article.confidence.overall,
                    degraded=article.confidence.degraded,
                    jurisdiction=document.metadata.jurisdiction,
                    version_label=document.metadata.version_label or "",
                    document_type=document.metadata.document_type,
                    language=chunk_lang,
                    canonical_refs=chunk_canonical_refs,
                    hierarchy_path=hierarchy_path_str,
                )
                # Record for table linking
                for tid in article.table_ids:
                    table_parent_map[tid] = parent_chunk_id

                chunks.append(parent_chunk)
                chunks.extend(clause_chunks)

                ctx.logger.info(
                    f"Split article '{article.label}' ({token_est} tokens) into "
                    f"1 heading + {len(clause_chunks)} clause chunks",
                    stage="chunking",
                )

    else:
        # No detected hierarchy: chunk by accumulating blocks up to a
        # bounded token budget. We use a smaller cap for the fallback path
        # (FALLBACK_TARGET_TOKENS) so retrieval works well on OCR-derived
        # forms/appendices where blocks are short and chunk_max_tokens=1024
        # would produce only a handful of huge chunks. Blocks are processed
        # in (page_id, reading_order_index) order so page_refs end up
        # sequential and chunk boundaries respect page boundaries.
        FALLBACK_TARGET_TOKENS = min(500, cfg.chunk_max_tokens)

        ordered_blocks = sorted(
            document.blocks,
            key=lambda b: (
                b.page_id or "",
                getattr(b, "reading_order_index", 0),
            ),
        )

        # Track the nearest section label or heading text so fallback chunks
        # carry a meaningful hierarchy_path instead of an empty string.
        section_label_map = {
            s.section_id: (s.label or s.title or "").strip()
            for s in document.sections
        }
        _current_hier = ""

        current_group: List = []
        current_content = ""
        current_tokens = 0

        def push_group(group, content, tokens, hier=""):
            if not group:
                return
            avg_conf = sum(b.confidence.overall for b in group) / len(group)
            chunk_canonical_refs = canonical_refs_for_chunk([], content)

            # Preserve page order: collect unique page_ids while keeping the
            # order they first appear in the group.
            seen = set()
            ordered_pages = []
            for b in group:
                if b.page_id and b.page_id not in seen:
                    seen.add(b.page_id)
                    ordered_pages.append(b.page_id)

            nonlocal chunk_idx
            chunk = Chunk(
                chunk_id=T.make_chunk_id(ctx.document_id, chunk_idx),
                document_id=ctx.document_id,
                chunk_type="text",
                content_format="markdown",
                content=content,
                structure_path=[],
                page_refs=ordered_pages,
                block_refs=[b.block_id for b in group],
                token_estimate=tokens,
                confidence=avg_conf,
                degraded=avg_conf < cfg.chunk_authority_threshold,
                jurisdiction=document.metadata.jurisdiction,
                version_label=document.metadata.version_label or "",
                document_type=document.metadata.document_type,
                language=chunk_lang,
                canonical_refs=chunk_canonical_refs,
                hierarchy_path=hier,
            )
            chunks.append(chunk)
            chunk_idx += 1

        for b in ordered_blocks:
            # Update hierarchy context when crossing into a section or heading block
            pid = getattr(b, "parent_structure_id", None)
            if pid and pid in section_label_map and section_label_map[pid]:
                _current_hier = section_label_map[pid]
            elif getattr(b, "block_type", "") == "heading":
                heading_text = (b.clean_text or b.raw_text or "").strip()[:100]
                if heading_text:
                    _current_hier = heading_text

            b_text = _block_text(b)
            if not b_text:
                continue

            b_tokens = len(b_text) // 4
            if current_group and (current_tokens + b_tokens > FALLBACK_TARGET_TOKENS):
                push_group(current_group, current_content, current_tokens, _current_hier)
                current_group = []
                current_content = ""
                current_tokens = 0

            current_group.append(b)
            current_content = f"{current_content}\n\n{b_text}" if current_content else b_text
            current_tokens += b_tokens

        if current_group:
            push_group(current_group, current_content, current_tokens, _current_hier)

    # ----------------------------------------------------------------
    # Table chunks: one chunk per table, linked to parent article
    # ----------------------------------------------------------------
    for table in document.tables:
        content = table.projection_text or table.markdown or "[table]"
        chunk_canonical_refs = canonical_refs_for_chunk([], content)
        parent_id = table_parent_map.get(table.table_id)

        table_chunk_id = T.make_chunk_id(ctx.document_id, chunk_idx)
        chunk = Chunk(
            chunk_id=table_chunk_id,
            document_id=ctx.document_id,
            chunk_type="table",
            content_format="markdown",
            content=content,
            structure_path=[],
            parent_chunk_id=parent_id,
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
        # Backfill sibling reference on parent article chunk
        if parent_id:
            for pc in chunks:
                if pc.chunk_id == parent_id:
                    pc.sibling_chunk_ids = list(pc.sibling_chunk_ids) + [table_chunk_id]
                    break
        chunks.append(chunk)
        chunk_idx += 1

    # ----------------------------------------------------------------
    # Image evidence chunks: for images with readable OCR text
    # ----------------------------------------------------------------
    for image in document.images:
        ocr_text = image.clean_ocr_text or image.raw_ocr_text
        if not ocr_text:
            continue  # Skip images with no textual content
        content = f"[Image: {image.image_class or 'visual'}]\n\n{ocr_text}"
        chunk_canonical_refs = canonical_refs_for_chunk([], content)

        chunk = Chunk(
            chunk_id=T.make_chunk_id(ctx.document_id, chunk_idx),
            document_id=ctx.document_id,
            chunk_type="image",
            content_format="markdown",
            content=content,
            structure_path=[],
            page_refs=[image.page_id] if image.page_id else [],
            image_refs=[image.image_id],
            token_estimate=len(content) // 4,
            confidence=image.confidence.overall,
            degraded=image.confidence.degraded or (image.evidence_status == "unreadable"),
            jurisdiction=document.metadata.jurisdiction,
            version_label=document.metadata.version_label or "",
            document_type=document.metadata.document_type,
            language=chunk_lang,
            canonical_refs=chunk_canonical_refs,
            hierarchy_path="",
        )
        chunks.append(chunk)
        chunk_idx += 1

    # ----------------------------------------------------------------
    # Validation pass: flag and warn about empty chunks
    # ----------------------------------------------------------------
    for chunk in chunks:
        if not chunk.content or not chunk.content.strip():
            chunk.degraded = True
            chunk.degraded_reasons = list(chunk.degraded_reasons) + ["empty_content"]
            warnings.append(
                f"Empty chunk detected: {chunk.chunk_id} (type={chunk.chunk_type})"
            )

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


def _block_text(b) -> str:
    """Return retrieval-ready text for a block, skipping cleaner-excluded noise."""
    if b.confidence.degraded and "noise_excluded" in b.confidence.reasons:
        return ""
    return b.clean_text or b.raw_text


def _build_path(article: Article, document: CanonicalDocument) -> List[str]:
    path = []
    if article.parent_section_id:
        for sec in document.sections:
            if sec.section_id == article.parent_section_id:
                path.append(sec.label or sec.title or sec.section_id)
                break
    path.append(article.label or article.article_id)
    return path
