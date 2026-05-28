"""
Stage 4: Canonical structuring

Converts raw extraction output into a CanonicalDocument with full provenance.
Detects legal hierarchy (Vietnamese and English), builds structural objects,
assigns canonical reference IDs, and generates a Markdown rendering.

Design rules:
- Do NOT invent articles or clauses from ambiguous content.
- Tables and images are first-class objects, never flattened.
- Hierarchy is preserved; missing text remains missing (no filler).
- Every output carries provenance and confidence.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Matches intra-document citation patterns in Vietnamese legal text.
# Captures the article number(s) referenced.
# Examples matched:
#   "Theo Điều 15", "căn cứ Điều 7 và Điều 8", "quy định tại Điều 10, 11, 12"
_CITATION_RE = re.compile(
    r"(?:theo|căn\s+cứ|quy\s+định\s+tại|xem|theo\s+quy\s+định|tại)?\s*"
    r"(?:khoản\s+\d+\s+)?"
    r"[Đđ]iều\s+(\d+(?:\s*[,\s]\s*(?:và\s+)?\d+)*)",
    re.IGNORECASE | re.UNICODE,
)

from src.config import PipelineConfig
from src.pipeline.interfaces import StageContext, StageOutput
from src.schemas.document import (
    Article,
    Block,
    CanonicalDocument,
    Clause,
    Confidence,
    DocumentMetadata,
    DocumentProfile,
    Image,
    RenderedOutputs,
    Section,
    Table,
    TableCell,
    Traceability,
    ValidationSummary,
)
from src.schemas.evaluation import STATUS_FAIL, STATUS_PASS
from src.utils import trace as T
from src.retrieval.canonical_references import CanonicalRefBuilder


# ---------------------------------------------------------------------------
# Document family / type auto-detection
# ---------------------------------------------------------------------------

# Priority-ordered detection rules: (family, type, keyword_patterns)
# Scans first 8000 chars; first match wins.
# ORDER MATTERS: more structurally distinctive document types must come first
# so that a document referencing other types (e.g. a form citing a thông tư)
# is classified by its own identity, not by references within its body.
_DOC_DETECTION_RULES: List[Tuple[str, str, List[str]]] = [
    # Forms / templates / annexes — checked first; these docs often cite laws
    ("bieu_mau", "bieu_mau",    ["phụ lục", "phu luc"]),
    ("bieu_mau", "bieu_mau",    ["biểu mẫu", "bieu mau", "mẫu số", "mau so"]),
    # Contracts — checked before generic statute keywords
    ("hop_dong", "hop_dong",    ["bên a:", "bên b:", "ben a:", "ben b:"]),
    ("hop_dong", "hop_dong",    ["this agreement", "this contract", "party a:", "party b:"]),
    ("hop_dong", "hop_dong",    ["hợp đồng", "hop dong"]),
    # Vietnamese statutes — most unique indicators first
    ("luat_phap", "bo_luat",    ["bộ luật", "bo luat"]),
    ("luat_phap", "luat",       ["quốc hội ban hành", "căn cứ hiến pháp", "luật này quy định"]),
    ("luat_phap", "nghi_dinh",  ["nghị định", "nghi dinh", "chính phủ ban hành"]),
    ("luat_phap", "thong_tu",   ["bộ trưởng ban hành", "thông tư", "thong tu"]),
    ("luat_phap", "quyet_dinh", ["quyết định", "quyet dinh"]),
    ("luat_phap", "chi_thi",    ["chỉ thị", "chi thi"]),
    ("luat_phap", "nghi_quyet", ["nghị quyết", "nghi quyet"]),
    # English statutes
    ("luat_phap", "bo_luat",    ["labor code", "civil code", "penal code", "criminal code"]),
    ("luat_phap", "nghi_dinh",  ["decree no.", "government decree"]),
    ("luat_phap", "thong_tu",   ["circular no.", "ministry circular"]),
]


def _detect_document_family_and_type(text: str) -> Tuple[str, str]:
    """
    Heuristic classifier: scan first 8000 chars for Vietnamese/English legal keywords.
    Returns (document_family, document_type). Falls back to ("general", "general") when
    no keyword matches.

    document_family: broad category slug  (e.g. "luat_phap", "hop_dong", "bieu_mau")
    document_type:   specific sub-type    (e.g. "nghi_dinh", "thong_tu", "bo_luat")
    """
    sample = text[:8000].lower()
    for family, doc_type, keywords in _DOC_DETECTION_RULES:
        if any(kw in sample for kw in keywords):
            return family, doc_type
    return "general", "general"


# ---------------------------------------------------------------------------
# Stage 4: Canonical structuring
# ---------------------------------------------------------------------------


def stage_canonical_structuring(ctx: StageContext) -> StageOutput:
    """
    Convert raw extraction output into a CanonicalDocument with provenance.
    Detects headings, articles, clauses. Preserves tables and images as first-class objects.
    """
    raw_blocks: List[Dict] = ctx.get("raw_blocks", [])
    raw_tables: List[Dict] = ctx.get("raw_tables", [])
    raw_images: List[Dict] = ctx.get("raw_images", [])
    profile: DocumentProfile = ctx.get("profile", DocumentProfile())
    source_hash = ctx.get("source_hash", "")
    file_type = ctx.get("file_type", "unknown")
    cfg = ctx.config

    # Build traceability template
    traceability_base = Traceability(
        trace_id=ctx.trace_id,
        source_hash=source_hash,
        extractor="local_pipeline_v1",
        extractor_version=cfg.processing_version,
        processing_version=cfg.processing_version,
        created_at=T.now_iso(),
    )

    # Detect document language from profile (set during profiling)
    profile_langs = profile.languages or ["en"]
    primary_language = profile_langs[0] if profile_langs else "en"

    # Build Block objects
    blocks: List[Block] = []
    for idx, rb in enumerate(raw_blocks):
        page_index = rb.get("page_index", 1)
        page_id = T.make_page_id(ctx.document_id, page_index)
        region_id = T.make_region_id(page_id, idx, "text")
        block_id = T.make_block_id(ctx.document_id, page_index, 0, idx)
        raw_text = rb.get("raw_text", "")
        block_type = _detect_block_type(rb)
        ocr_conf = rb.get("ocr_confidence")
        overall_conf = ocr_conf if ocr_conf is not None else 1.0
        degraded = overall_conf < cfg.extraction_confidence_threshold

        block = Block(
            block_id=block_id,
            page_id=page_id,
            region_id=region_id,
            block_type=block_type,
            order_index=idx,
            raw_text=raw_text,
            clean_text=_clean_text(raw_text),
            language=primary_language,
            confidence=Confidence(
                overall=overall_conf,
                extraction=overall_conf,
                ocr=ocr_conf,
                degraded=degraded,
                reasons=["ocr_below_threshold"] if degraded and ocr_conf is not None else [],
            ),
            traceability=traceability_base,
        )
        blocks.append(block)

    # Build Table objects
    tables: List[Table] = []
    for tbl_idx, rt in enumerate(raw_tables):
        page_index = rt.get("page_index", 1)
        table_id = T.make_table_id(ctx.document_id, page_index, tbl_idx)
        rows_raw = rt.get("rows", [])
        page_id = T.make_page_id(ctx.document_id, page_index)

        header_row_index = rt.get("header_row_index")
        cells: List[TableCell] = []
        for r_idx, row in enumerate(rows_raw):
            is_header = (header_row_index is not None and r_idx == header_row_index)
            for c_idx, cell_text in enumerate(row):
                cells.append(TableCell(
                    row=r_idx, col=c_idx,
                    text=cell_text, raw_text=cell_text,
                    is_header=is_header,
                ))

        # Markdown projection: bold header row if detected
        md_lines = []
        for r_idx, row in enumerate(rows_raw):
            row_str = " | ".join(str(c) for c in row)
            md_lines.append(f"| {row_str} |")
            if header_row_index is not None and r_idx == header_row_index:
                sep = " | ".join("---" for _ in row)
                md_lines.append(f"| {sep} |")
        projection = "\n".join(md_lines)

        tables.append(Table(
            table_id=table_id,
            page_refs=[page_id],
            row_count=len(rows_raw),
            column_count=max((len(r) for r in rows_raw), default=0),
            cells=cells,
            projection_text=projection,
            markdown=projection,
            confidence=Confidence(overall=0.9, topology=0.9),
            traceability=traceability_base,
        ))

    # Build Image objects (from raw_images if any, else empty)
    images: List[Image] = []
    for img_idx, ri in enumerate(raw_images):
        page_index = ri.get("page_index", 1)
        image_id = T.make_image_id(ctx.document_id, page_index, img_idx)
        page_id = T.make_page_id(ctx.document_id, page_index)
        images.append(Image(
            image_id=image_id,
            page_id=page_id,
            image_class=ri.get("image_class", "unknown"),
            raw_ocr_text=ri.get("raw_ocr_text", ""),
            clean_ocr_text=ri.get("clean_ocr_text", ""),
            ocr_confidence=ri.get("ocr_confidence"),
            evidence_status=ri.get("evidence_status", "visual_only"),
            confidence=Confidence(overall=ri.get("ocr_confidence", 0.5)),
            traceability=traceability_base,
        ))

    # Detect structural hierarchy from blocks
    sections, articles, clauses = _detect_hierarchy(blocks, ctx.document_id)

    # Populate article.citations from body text (enables CITES edges in graph_builder)
    _populate_article_citations(articles, blocks, clauses)

    # Build canonical reference IDs for all structural units
    _attach_canonical_ids(sections, articles, clauses, ctx.document_id)

    # Build page refs
    page_ids_seen = sorted({b.page_id for b in blocks})
    pages = [{"page_id": pid, "page_index": i + 1} for i, pid in enumerate(page_ids_seen)]

    # Compute doc-level confidence
    if blocks:
        avg_conf = sum(b.confidence.overall for b in blocks) / len(blocks)
    else:
        avg_conf = 0.0

    # Auto-detect document family/type from raw text when no override is set
    if ctx.config.document_type_override:
        doc_family = ctx.config.document_type_override
        doc_type = ctx.config.document_type_override
    else:
        raw_text_sample = " ".join(
            rb.get("raw_text", "") for rb in raw_blocks[:40]
        )
        doc_family, doc_type = _detect_document_family_and_type(raw_text_sample)

    document = CanonicalDocument(
        document_id=ctx.document_id,
        schema_version=cfg.schema_version,
        source_filename=ctx.source_path.name,
        mime_type=ctx.get("mime_type", ""),
        file_type=file_type,
        metadata=DocumentMetadata(
            languages=profile_langs,
            document_family=doc_family,
            document_type=doc_type,
        ),
        profile=profile,
        pages=pages,
        blocks=blocks,
        tables=tables,
        images=images,
        sections=sections,
        articles=articles,
        clauses=clauses,
        rendered_outputs=RenderedOutputs(
            markdown=_render_markdown(blocks, tables),
            generation_status="partial" if blocks else "unavailable",
        ),
        confidence=Confidence(overall=avg_conf, extraction=avg_conf),
        traceability=traceability_base,
    )

    ctx.put("document", document)

    return StageOutput(
        stage_name="canonical_structuring",
        status=STATUS_PASS,
        summary=(
            f"Structured {len(blocks)} blocks, {len(tables)} tables, "
            f"{len(sections)} sections, {len(articles)} articles, {len(clauses)} clauses"
        ),
        output_summary={
            "block_count": len(blocks),
            "table_count": len(tables),
            "image_count": len(images),
            "section_count": len(sections),
            "article_count": len(articles),
            "clause_count": len(clauses),
            "structure_detected": bool(sections or articles or clauses),
            "avg_confidence": round(avg_conf, 3),
        },
    )


# ---------------------------------------------------------------------------
# Canonical ID helpers
# ---------------------------------------------------------------------------


def _extract_citations(text: str) -> List[str]:
    """
    Extract raw citation strings from article body text for graph CITES edges.
    Returns deduplicated "Điều N" strings. graph_builder passes these through
    extract_refs() which correctly parses Vietnamese text to canonical IDs.
    Storing pre-built "article_N" strings causes extract_refs to misparse them
    via regex backtracking (art → icl false match).
    """
    refs: List[str] = []
    seen: set = set()
    for m in _CITATION_RE.finditer(text):
        numbers_str = m.group(1)
        for part in re.split(r"[\s,]+(?:và\s+)?", numbers_str):
            num = part.strip()
            if num and num.isdigit():
                key = f"Điều {num}"
                if key not in seen:
                    refs.append(key)
                    seen.add(key)
    return refs


def _populate_article_citations(
    articles: List["Article"],
    blocks: List["Block"],
    clauses: Optional[List["Clause"]] = None,
) -> None:
    """
    Second pass after hierarchy detection: scan body text of each article
    and populate article.citations with canonical refs of intra-doc Điều X
    mentions. These refs are consumed by graph_builder to create CITES edges.

    Collects both direct article body blocks AND blocks nested under clauses
    (which have parent_structure_id = clause_id, not article_id directly).
    """
    if not articles:
        return
    art_map: Dict[str, "Article"] = {art.article_id: art for art in articles}

    # Build clause_id → article_id map so clause-nested blocks can be attributed
    clause_to_article: Dict[str, str] = {}
    if clauses:
        for clause in clauses:
            if clause.parent_article_id and clause.parent_article_id in art_map:
                clause_to_article[clause.clause_id] = clause.parent_article_id

    body_texts: Dict[str, List[str]] = {aid: [] for aid in art_map}
    for block in blocks:
        pid = getattr(block, "parent_structure_id", None)
        if not pid:
            continue
        if pid in art_map:
            art_id = pid
        elif pid in clause_to_article:
            art_id = clause_to_article[pid]
        else:
            continue
        t = block.clean_text or block.raw_text
        if t:
            body_texts[art_id].append(t)

    for art_id, texts in body_texts.items():
        if texts:
            refs = _extract_citations(" ".join(texts))
            if refs:
                art_map[art_id].citations = refs


def _attach_canonical_ids(
    sections: List[Section],
    articles: List[Article],
    clauses: List[Clause],
    document_id: str,
) -> None:
    """
    Attach canonical_id attributes to structure objects.

    Canonical IDs are stored on traceability.repair_methods as
    "canonical_id:<value>" so they are preserved in the schema and accessible later.
    """
    builder = CanonicalRefBuilder(document_id=document_id)

    # Map section_id → canonical_id for parent lookup
    section_canonical: Dict[str, str] = {}
    for section in sections:
        cid = builder.section_ref(section.label or "")
        section_canonical[section.section_id] = cid
        if section.traceability is None:
            section.traceability = Traceability(
                trace_id="", source_hash="", extractor="local_pipeline_v1",
                extractor_version="0.1.0",
            )
        _set_canonical_id(section.traceability, cid)

    # Map article_id → canonical_id for clause parent lookup
    article_canonical: Dict[str, str] = {}
    for article in articles:
        cid = builder.article_ref(article.label or "")
        article_canonical[article.article_id] = cid
        if article.traceability is None:
            article.traceability = Traceability(
                trace_id="", source_hash="", extractor="local_pipeline_v1",
                extractor_version="0.1.0",
            )
        _set_canonical_id(article.traceability, cid)

    for clause in clauses:
        parent_art_canonical = (
            article_canonical.get(clause.parent_article_id or "")
            if clause.parent_article_id else None
        )
        cid = builder.clause_ref(
            clause.label or "",
            parent_canonical=parent_art_canonical,
        )
        if clause.traceability is None:
            clause.traceability = Traceability(
                trace_id="", source_hash="", extractor="local_pipeline_v1",
                extractor_version="0.1.0",
            )
        _set_canonical_id(clause.traceability, cid)


def _set_canonical_id(traceability: Traceability, canonical_id: str) -> None:
    """Store canonical_id in traceability.repair_methods as 'canonical_id:<value>'."""
    traceability.repair_methods = [
        m for m in traceability.repair_methods
        if not m.startswith("canonical_id:")
    ]
    traceability.repair_methods.append(f"canonical_id:{canonical_id}")


def _get_canonical_id(traceability: Optional[Traceability]) -> Optional[str]:
    """Retrieve canonical_id from traceability.repair_methods."""
    if traceability is None:
        return None
    for m in traceability.repair_methods:
        if m.startswith("canonical_id:"):
            return m[len("canonical_id:"):]
    return None


# ---------------------------------------------------------------------------
# Block classification
# ---------------------------------------------------------------------------


def _is_citation_text(text: str) -> bool:
    """
    Detect whether a "heading-looking" line is actually a CITATION to another
    legal document rather than a real heading of this document.

    Examples that look like Điều/Khoản headings but are citations:
      - "Điều 47 Nghị định số 96/2026/NĐ-CP" (referencing another decree)
      - "Khoản 3 Điều 23 Luật Đầu tư"
      - "Điều 32 Nghị định 96/2026/ND-CP (Chấp thuận chủ trương..."
      - "(Điểm a khoản 1 Điều 32)"

    A real article heading from the document being parsed has the form
    "Điều X. <Title>" or "Điều X <Title>" without referencing another doc.

    Returns True if the text contains citation keywords (Nghị định / Luật /
    Thông tư / Quyết định / NĐ-CP / TT-BTC) — in which case the caller
    should classify the block as paragraph, NOT heading.
    """
    if not text:
        return False
    citation_keywords = [
        r"Nghị\s*định", r"Luật\s+", r"Thông\s*tư", r"Quyết\s*định",
        r"NĐ-CP", r"TT-BTC", r"QH\d+", r"/202\d/", r"/20\d\d/",
    ]
    for kw in citation_keywords:
        if re.search(kw, text, re.IGNORECASE):
            return True
    # Mismatched brackets often indicate the line is a fragmented citation
    # (e.g. only the closing ")" survived after OCR slicing).
    if text.count("(") != text.count(")"):
        return True
    return False


def _detect_block_type(rb: Dict) -> str:
    """
    Heuristic block type detection.
    Recognises Vietnamese legal structure (Chương, Mục, Điều, Khoản, Điểm)
    and English legal structure (Chapter, Section, Article, Clause, Point).
    """
    style = rb.get("style", "").lower()
    tag = rb.get("tag", "").lower()
    text = (rb.get("raw_text", "") or "").strip()

    # Style / HTML tag signals
    if any(h in style for h in ("heading", "title", "h1", "h2", "h3", "heading 1", "heading 2", "heading 3")):
        return "heading"
    if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
        return "heading"
    if tag == "li":
        return "list_item"

    # --- Vietnamese hierarchy headings ---
    # Important: skip CITATIONS that mention "Điều X Nghị định Y" / similar.
    # Those are references to other documents, not real headings of this doc.
    if re.match(r"^\s*chương\s+[\w]+", text, re.IGNORECASE | re.UNICODE):
        return "heading" if not _is_citation_text(text) else "paragraph"
    if re.match(r"^\s*mục\s+[\w]+", text, re.IGNORECASE | re.UNICODE):
        return "heading" if not _is_citation_text(text) else "paragraph"
    if re.match(r"^\s*điều\s+\d+", text, re.IGNORECASE | re.UNICODE):
        return "heading" if not _is_citation_text(text) else "paragraph"
    if re.match(r"^\s*phần\s+[\w]+", text, re.IGNORECASE | re.UNICODE):
        return "heading" if not _is_citation_text(text) else "paragraph"
    if re.match(r"^\s*(mẫu|mau|biểu\s+mẫu|bieu\s+mau|phụ\s+lục|phu\s+luc|phy\s+luc|phu|phy|phụ|form)\s+", text, re.IGNORECASE | re.UNICODE):
        return "heading"

    # --- Vietnamese clause / point markers ---
    # Also gate by _is_citation_text — "Khoản 3 Điều 23 Luật Đầu tư" is a
    # citation, not a clause heading of this document.
    if re.match(r"^\s*khoản\s+\d+", text, re.IGNORECASE | re.UNICODE):
        return "list_item" if not _is_citation_text(text) else "paragraph"
    if re.match(r"^\s*điểm\s+[a-z][\.\):\s]", text, re.IGNORECASE | re.UNICODE):
        return "list_item" if not _is_citation_text(text) else "paragraph"

    # --- English hierarchy headings ---
    if re.match(r"^\s*(article|section|chapter|part|schedule|annex|exhibit)\s+[\w]+", text, re.IGNORECASE):
        return "heading"
    if re.match(r"^\s*§\s*\d+", text):
        return "heading"

    # --- Numbered list items (both languages) ---
    if re.match(r"^\s*\d+[\.\)]\s+\S", text):
        return "list_item"
    if re.match(r"^\s*[\(\[]?[a-záàảãạăắằẳẵặâấầẩẫậ][\)\]\.]\s+\S", text, re.IGNORECASE | re.UNICODE):
        return "list_item"

    # Short lines ending with colon are often subheadings
    if len(text) < 150 and text.endswith(":") and "\n" not in text:
        return "heading"

    # Citation patterns
    if re.match(r"^\s*\(?\d+\)\s+[A-ZĐÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬ]", text, re.UNICODE):
        return "list_item"

    return "paragraph"


def _clean_text(text: str) -> str:
    """Mechanical text normalization. Never changes legal wording."""
    text = re.sub(r"\s+", " ", text)
    text = text.strip()
    return text


# ---------------------------------------------------------------------------
# Hierarchy detection
# ---------------------------------------------------------------------------


def _detect_hierarchy(
    blocks: List[Block], document_id: str
) -> Tuple[List[Section], List[Article], List[Clause]]:
    """
    Bilingual hierarchy detection from heading blocks.
    Supports Vietnamese legal structure and English legal structure.

    Vietnamese hierarchy:
        Phần / Chương  →  Section (section_kind = "phần" / "chương")
        Mục            →  Section (section_kind = "mục")
        Điều           →  Article
        Khoản / Điểm   →  Clause  (via list_item blocks under a Điều)

    English hierarchy:
        Chapter / Part / Schedule / Annex  →  Section
        Article / Section (numbered)        →  Article
        Clause / Paragraph / Point          →  Clause

    Docs rule: do NOT invent articles or clauses from ambiguous content.
    """
    sections: List[Section] = []
    articles: List[Article] = []
    clauses: List[Clause] = []

    sec_idx = 0
    art_idx = 0
    cls_idx = 0

    current_section_id: Optional[str] = None
    current_article_id: Optional[str] = None
    current_clause_id: Optional[str] = None   # tracks last Khoản so Điểm can nest under it

    # ----------------------------------------------------------------
    # Compiled patterns — Vietnamese
    # ----------------------------------------------------------------
    re_vi_part = re.compile(
        r"^\s*(phần)\s+([\wIVXivx]+)([\.\:\s]+(.*))?$",
        re.IGNORECASE | re.UNICODE,
    )
    re_vi_chapter = re.compile(
        r"^\s*(chương)\s+([\wIVXivx]+)([\.\:\s]+(.*))?$",
        re.IGNORECASE | re.UNICODE,
    )
    re_vi_muc = re.compile(
        r"^\s*(mục)\s+(\w+)([\.\:\s]+(.*))?$",
        re.IGNORECASE | re.UNICODE,
    )
    re_vi_dieu = re.compile(
        r"^\s*(điều)\s+(\d+[a-zđ]?)([\.\:\s]+(.*))?$",
        re.IGNORECASE | re.UNICODE,
    )
    re_vi_khoan = re.compile(
        r"^\s*(khoản)\s+(\d+)([\.\:\s]+(.*))?$",
        re.IGNORECASE | re.UNICODE,
    )
    re_vi_diem = re.compile(
        r"^\s*(điểm)\s+([a-záàảãạăắằẳẵặâấầẩẫậ])([\.\)\:\s]+(.*))?$",
        re.IGNORECASE | re.UNICODE,
    )
    re_vi_form = re.compile(
        r"^\s*(mẫu|mau|biểu\s+mẫu|bieu\s+mau|phụ\s+lục|phu\s+luc|phy\s+luc|phu|phy|phụ|form)\s+(?:số\s+|so\s+)?(?:([a-z0-9\.\-\/]+)\s+)?(.*)$",
        re.IGNORECASE | re.UNICODE,
    )

    # ----------------------------------------------------------------
    # Compiled patterns — English
    # ----------------------------------------------------------------
    re_en_section = re.compile(
        r"^\s*(chapter|part|title|schedule|annex|exhibit)\s+([\wIVXivx]+)([\.\:\s]+(.*))?$",
        re.IGNORECASE,
    )
    re_en_article = re.compile(
        r"^\s*(article|section|§)\s*(\d+[a-z]?)([\.\:\s]+(.*))?$",
        re.IGNORECASE,
    )
    re_en_clause = re.compile(
        r"^\s*(clause|paragraph|sub-clause|point)\s+(\d+[a-z]?|\([a-z]\))([\.\:\s]+(.*))?$",
        re.IGNORECASE,
    )

    for block in blocks:
        text = block.raw_text.strip()
        if not text:
            continue

        # ---- Vietnamese: Mẫu / Phụ lục / Form → Section ----
        m_form = re_vi_form.match(text)
        if m_form:
            section_id = T.make_section_id(document_id, sec_idx)
            sec_idx += 1
            heading_title = (m_form.group(3) or "").strip() if m_form.lastindex and m_form.lastindex >= 3 else ""
            sections.append(Section(
                section_id=section_id,
                section_kind="form",
                label=text[:120],
                number=m_form.group(2) or None,
                title=heading_title or None,
                parent_section_id=None,
                block_ids=[block.block_id],
                page_refs=[block.page_id],
                confidence=Confidence(overall=0.90, structure=0.90),
            ))
            current_section_id = section_id
            current_article_id = None
            block.parent_structure_id = section_id
            block.block_type = "heading"
            continue

        # ---- Vietnamese: Phần / Chương / Mục → Section ----
        for pattern, kind in [
            (re_vi_part, "phần"),
            (re_vi_chapter, "chương"),
            (re_vi_muc, "mục"),
        ]:
            m = pattern.match(text)
            if m:
                section_id = T.make_section_id(document_id, sec_idx)
                sec_idx += 1
                heading_title = (m.group(4) or "").strip() if m.lastindex and m.lastindex >= 4 else ""
                sections.append(Section(
                    section_id=section_id,
                    section_kind=kind,
                    label=text[:120],
                    number=m.group(2),
                    title=heading_title or None,
                    parent_section_id=None,
                    block_ids=[block.block_id],
                    page_refs=[block.page_id],
                    confidence=Confidence(overall=0.90, structure=0.90),
                ))
                current_section_id = section_id
                current_article_id = None
                block.parent_structure_id = section_id
                block.block_type = "heading"
                break
        else:
            # ---- Vietnamese: Điều → Article ----
            m = re_vi_dieu.match(text)
            if m:
                article_id = T.make_article_id(document_id, art_idx)
                art_idx += 1
                heading_title = (m.group(4) or "").strip() if m.lastindex and m.lastindex >= 4 else ""
                articles.append(Article(
                    article_id=article_id,
                    label=text[:120],
                    number=m.group(2),
                    title=heading_title or None,
                    parent_section_id=current_section_id,
                    block_ids=[block.block_id],
                    page_refs=[block.page_id],
                    confidence=Confidence(overall=0.90, structure=0.90),
                ))
                current_article_id = article_id
                current_clause_id = None          # reset clause context on new Điều
                block.parent_structure_id = article_id
                block.block_type = "heading"
                continue

            # ---- Vietnamese: Khoản / Điểm → Clause ----
            m_khoan = re_vi_khoan.match(text)
            m_diem = re_vi_diem.match(text)
            if m_khoan or m_diem:
                clause_id = T.make_clause_id(document_id, cls_idx)
                cls_idx += 1
                if m_khoan:
                    clauses.append(Clause(
                        clause_id=clause_id,
                        label=text[:120],
                        number=m_khoan.group(2),
                        clause_kind="paragraph",
                        parent_article_id=current_article_id,
                        parent_clause_id=None,
                        block_ids=[block.block_id],
                        page_refs=[block.page_id],
                        confidence=Confidence(overall=0.85, structure=0.85),
                    ))
                    current_clause_id = clause_id
                else:
                    clauses.append(Clause(
                        clause_id=clause_id,
                        label=text[:120],
                        number=m_diem.group(2),
                        clause_kind="point",
                        parent_article_id=current_article_id,
                        parent_clause_id=current_clause_id,
                        block_ids=[block.block_id],
                        page_refs=[block.page_id],
                        confidence=Confidence(overall=0.82, structure=0.82),
                    ))
                block.parent_structure_id = clause_id
                continue

            # ---- English: Chapter / Part / Schedule → Section ----
            m = re_en_section.match(text)
            if m:
                section_id = T.make_section_id(document_id, sec_idx)
                sec_idx += 1
                kind = m.group(1).lower()
                heading_title = (m.group(4) or "").strip() if m.lastindex and m.lastindex >= 4 else ""
                sections.append(Section(
                    section_id=section_id,
                    section_kind=kind,
                    label=text[:120],
                    number=m.group(2),
                    title=heading_title or None,
                    parent_section_id=None,
                    block_ids=[block.block_id],
                    page_refs=[block.page_id],
                    confidence=Confidence(overall=0.90, structure=0.90),
                ))
                current_section_id = section_id
                current_article_id = None
                block.parent_structure_id = section_id
                block.block_type = "heading"
                continue

            # ---- English: Article / Section (numbered) → Article ----
            m = re_en_article.match(text)
            if m:
                article_id = T.make_article_id(document_id, art_idx)
                art_idx += 1
                heading_title = (m.group(4) or "").strip() if m.lastindex and m.lastindex >= 4 else ""
                articles.append(Article(
                    article_id=article_id,
                    label=text[:120],
                    number=m.group(2),
                    title=heading_title or None,
                    parent_section_id=current_section_id,
                    block_ids=[block.block_id],
                    page_refs=[block.page_id],
                    confidence=Confidence(overall=0.88, structure=0.88),
                ))
                current_article_id = article_id
                block.parent_structure_id = article_id
                block.block_type = "heading"
                continue

            # ---- English: Clause / Paragraph → Clause ----
            m = re_en_clause.match(text)
            if m:
                clause_id = T.make_clause_id(document_id, cls_idx)
                cls_idx += 1
                clauses.append(Clause(
                    clause_id=clause_id,
                    label=text[:120],
                    number=m.group(2),
                    clause_kind=m.group(1).lower(),
                    parent_article_id=current_article_id,
                    block_ids=[block.block_id],
                    page_refs=[block.page_id],
                    confidence=Confidence(overall=0.82, structure=0.82),
                ))
                block.parent_structure_id = clause_id
                continue

            # ---- Non-structural block: inherit innermost active context ----
            # Paragraphs, list items, and other body content that do not match
            # any structural heading are assigned to the innermost active scope
            # so the chunker can gather full article/clause body text.
            if current_clause_id:
                block.parent_structure_id = current_clause_id
            elif current_article_id:
                block.parent_structure_id = current_article_id
            elif current_section_id:
                block.parent_structure_id = current_section_id

    return sections, articles, clauses


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_markdown(blocks: List[Block], tables: List[Table]) -> str:
    """
    Generate a basic Markdown representation from canonical objects.
    Handles Vietnamese and English headings uniformly.
    Vietnamese diacritics are preserved exactly — never simplified or stripped.
    """
    lines: List[str] = []
    for block in blocks:
        text = block.clean_text or block.raw_text
        if not text:
            continue
        if block.block_type == "heading":
            level = _heading_level(text)
            prefix = "#" * level
            lines.append(f"\n{prefix} {text}\n")
        elif block.block_type == "list_item":
            lines.append(f"- {text}")
        elif block.block_type == "footnote":
            lines.append(f"> {text}")
        else:
            lines.append(text)
    for table in tables:
        if table.markdown:
            lines.append(f"\n{table.markdown}\n")
    return "\n".join(lines)


def _heading_level(text: str) -> int:
    """
    Determine Markdown heading level from text content.
    Vietnamese:  Phần/Chương → h1, Mục → h2, Điều → h3, Khoản/Điểm → h4
    English:     Chapter/Part → h1, Article/Section → h2, Clause → h3
    Default:     h2
    """
    t = text.strip().lower()
    if re.match(r"^(chương|phần|chapter|part|mẫu|mau|biểu\s+mẫu|bieu\s+mau|phụ\s+lục|phu\s+luc|phy\s+luc|phu|phy|phụ|form)\s+", t, re.UNICODE):
        return 1
    if re.match(r"^(mục|section|article|§)\s+", t, re.UNICODE):
        return 2
    if re.match(r"^(điều|clause)\s+", t, re.UNICODE):
        return 3
    if re.match(r"^(khoản|điểm|paragraph|sub-clause)\s+", t, re.UNICODE):
        return 4
    return 2
