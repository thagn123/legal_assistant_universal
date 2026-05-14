"""
Metric computation for the evaluation report.

These functions take pipeline artifacts and return structured metric dicts.
They do not mutate any artifact; they only read and compute.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from src.schemas.chunk import ChunkSet
from src.schemas.document import CanonicalDocument
from src.schemas.graph import GraphSubgraph


def compute_extraction_completeness(document: CanonicalDocument) -> Dict[str, Any]:
    """
    How much of the source document was extracted and preserved?
    Returns a dict with fraction scores and counts.
    """
    total_blocks = document.block_count()
    degraded = document.degraded_block_count()
    low_conf = len(document.low_confidence_blocks(threshold=0.65))

    coverage = document.validation.coverage_score
    authoritative_fraction = (total_blocks - degraded) / max(1, total_blocks)

    return {
        "total_blocks": total_blocks,
        "degraded_blocks": degraded,
        "low_confidence_blocks": low_conf,
        "coverage_score": round(coverage, 3),
        "authoritative_fraction": round(authoritative_fraction, 3),
        "has_structure": document.has_structure(),
        "section_count": len(document.sections),
        "article_count": len(document.articles),
        "clause_count": len(document.clauses),
    }


def compute_structure_preservation(document: CanonicalDocument) -> Dict[str, Any]:
    """
    Was the document hierarchy preserved during extraction?
    """
    has_sections = len(document.sections) > 0
    has_articles = len(document.articles) > 0
    has_clauses = len(document.clauses) > 0

    # Check parent references are populated
    articles_with_parent = sum(1 for a in document.articles if a.parent_section_id)
    clauses_with_parent = sum(1 for c in document.clauses if c.parent_article_id or c.parent_clause_id)

    return {
        "sections_detected": len(document.sections),
        "articles_detected": len(document.articles),
        "clauses_detected": len(document.clauses),
        "articles_with_section_parent": articles_with_parent,
        "clauses_with_article_parent": clauses_with_parent,
        "hierarchy_depth": _hierarchy_depth(document),
        "structure_quality": _structure_quality(document),
    }


def _hierarchy_depth(document: CanonicalDocument) -> int:
    if document.clauses:
        return 3
    if document.articles:
        return 2
    if document.sections:
        return 1
    return 0


def _structure_quality(document: CanonicalDocument) -> str:
    if not document.has_structure():
        return "flat"
    if document.articles and document.sections:
        return "hierarchical"
    if document.articles:
        return "article_level"
    return "section_level"


def compute_table_preservation(document: CanonicalDocument) -> Dict[str, Any]:
    """
    Were tables extracted with intact topology?
    """
    tables = document.tables
    if not tables:
        return {"table_count": 0, "note": "No tables in document."}

    intact = sum(1 for t in tables if t.row_count > 0 and t.column_count > 0)
    avg_conf = sum(t.confidence.overall for t in tables) / len(tables)
    multi_page = sum(1 for t in tables if t.continuation is not None)

    return {
        "table_count": len(tables),
        "intact_tables": intact,
        "broken_tables": len(tables) - intact,
        "avg_topology_confidence": round(avg_conf, 3),
        "multi_page_tables": multi_page,
        "has_html_rendering": sum(1 for t in tables if t.html),
        "has_markdown_rendering": sum(1 for t in tables if t.markdown),
    }


def compute_ocr_confidence_summary(document: CanonicalDocument) -> Dict[str, Any]:
    """
    Summarize OCR confidence across blocks and images.
    """
    ocr_blocks = [b for b in document.blocks if b.confidence.ocr is not None]
    ocr_images = [img for img in document.images if img.ocr_confidence is not None]

    if not ocr_blocks and not ocr_images:
        return {"ocr_applied": False}

    all_ocr_scores = [b.confidence.ocr for b in ocr_blocks] + [img.ocr_confidence for img in ocr_images]
    all_ocr_scores = [s for s in all_ocr_scores if s is not None]

    return {
        "ocr_applied": True,
        "ocr_block_count": len(ocr_blocks),
        "ocr_image_count": len(ocr_images),
        "avg_ocr_confidence": round(sum(all_ocr_scores) / len(all_ocr_scores), 3),
        "min_ocr_confidence": round(min(all_ocr_scores), 3),
        "max_ocr_confidence": round(max(all_ocr_scores), 3),
        "low_confidence_count": sum(1 for s in all_ocr_scores if s < 0.75),
    }


def compute_chunk_quality_summary(chunk_set: Optional[ChunkSet]) -> Dict[str, Any]:
    """
    Assess chunk set quality for retrieval readiness.
    """
    if chunk_set is None or not chunk_set.chunks:
        return {"total_chunks": 0, "retrieval_ready": False}

    chunks = chunk_set.chunks
    authoritative = chunk_set.authoritative_chunks()
    token_estimates = [c.token_estimate for c in chunks]
    avg_tokens = sum(token_estimates) / len(token_estimates)

    return {
        "total_chunks": len(chunks),
        "text_chunks": len(chunk_set.text_chunks()),
        "table_chunks": len(chunk_set.table_chunks()),
        "degraded_chunks": chunk_set.degraded_chunks,
        "authoritative_chunks": len(authoritative),
        "avg_token_estimate": round(avg_tokens, 1),
        "max_token_estimate": max(token_estimates),
        "min_token_estimate": min(token_estimates),
        "strategy_used": chunk_set.strategy_used,
        "retrieval_ready": len(authoritative) > 0,
    }


def compute_graph_summary(graph: Optional[GraphSubgraph]) -> Dict[str, Any]:
    """
    Summarize graph construction quality.
    """
    if graph is None:
        return {"graph_built": False}

    return {
        "graph_built": True,
        "total_nodes": graph.node_count(),
        "total_edges": graph.edge_count(),
        "structural_edges": graph.structural_edge_count(),
        "nodes_by_type": graph.nodes_by_type(),
        "edges_by_type": graph.edges_by_type(),
        "low_confidence_edges": len(graph.low_confidence_edges()),
        "coverage_adequate": graph.node_count() > 0 and graph.edge_count() > 0,
    }


def compute_missing_content_warnings(document: CanonicalDocument) -> List[str]:
    """
    Detect missing content patterns and return warnings.
    Does not invent or guess missing text.
    """
    warnings = []

    if document.block_count() == 0:
        warnings.append("CRITICAL: No content extracted. Document may be unreadable.")
        return warnings

    pages_with_blocks = {b.page_id for b in document.blocks}
    all_page_ids = {p.get("page_id", "") for p in document.pages}
    empty_pages = all_page_ids - pages_with_blocks
    if empty_pages:
        warnings.append(f"{len(empty_pages)} page(s) have no extracted blocks: {sorted(empty_pages)[:5]}")

    if document.profile.has_tables and document.table_count() == 0:
        warnings.append("Document was profiled as table-heavy but no tables were extracted.")

    if document.profile.has_images and document.image_count() == 0:
        warnings.append("Document has image regions but no image evidence objects were created.")

    return warnings
