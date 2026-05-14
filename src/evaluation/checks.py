"""
Per-stage validation checks.

Each check returns (passed: bool, message: str).
Checks are grouped by stage and called from the evaluation runner.
These rules directly implement the requirements in:
- docs/validation/hallucination-prevention.md
- docs/validation/parser-benchmark.md
- docs/schemas/document-schema.md
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from src.schemas.chunk import ChunkSet
from src.schemas.document import CanonicalDocument
from src.schemas.evaluation import ExtractionMetrics

Check = Tuple[bool, str]


# ---------------------------------------------------------------------------
# Extraction checks
# ---------------------------------------------------------------------------


def check_blocks_present(document: CanonicalDocument) -> Check:
    if document.block_count() == 0:
        return False, "No blocks extracted. Document may be empty, encrypted, or unsupported."
    return True, f"{document.block_count()} blocks extracted."


def check_coverage(document: CanonicalDocument, min_coverage: float = 0.3) -> Check:
    score = document.validation.coverage_score
    if score < min_coverage:
        return False, f"Coverage score {score:.2f} is below minimum {min_coverage:.2f}."
    return True, f"Coverage score: {score:.2f}"


def check_provenance_on_blocks(document: CanonicalDocument) -> Check:
    """Every block must have a page_id and region_id (docs rule: provenance on every unit)."""
    missing = [b.block_id for b in document.blocks if not b.page_id or not b.region_id]
    if missing:
        return False, f"{len(missing)} block(s) missing page_id or region_id: {missing[:5]}"
    return True, "All blocks have provenance."


def check_no_invented_text(document: CanonicalDocument) -> Check:
    """
    Hallucination prevention check: detect suspiciously short blocks that may be
    empty fill-ins (docs: missing text must remain missing, never replaced with filler).
    """
    suspicious = [
        b.block_id for b in document.blocks
        if b.raw_text.strip() in ("", "...", "[missing]", "N/A", "UNKNOWN")
        and b.confidence.overall > 0.8
    ]
    if suspicious:
        return (
            False,
            f"{len(suspicious)} block(s) contain placeholder text but are marked high-confidence. "
            "Possible hallucination risk."
        )
    return True, "No placeholder text detected in high-confidence blocks."


def check_tables_intact(document: CanonicalDocument) -> Check:
    """Tables must have at least one row and correct topology."""
    broken = [
        t.table_id for t in document.tables
        if t.row_count == 0 or t.column_count == 0
    ]
    if broken:
        return False, f"{len(broken)} table(s) have broken topology: {broken[:5]}"
    return True, f"All {document.table_count()} table(s) have valid topology."


def check_low_confidence_rate(document: CanonicalDocument, threshold: float = 0.65, max_rate: float = 0.3) -> Check:
    """Warn if too many blocks are below confidence threshold."""
    total = document.block_count()
    if total == 0:
        return True, "No blocks to assess."
    low = len(document.low_confidence_blocks(threshold))
    rate = low / total
    if rate > max_rate:
        return False, f"{low}/{total} blocks ({rate:.0%}) below confidence {threshold}. Consider OCR repair."
    return True, f"Low-confidence block rate: {rate:.0%} (within acceptable range)."


# ---------------------------------------------------------------------------
# Chunk checks
# ---------------------------------------------------------------------------


def check_chunks_present(chunk_set: ChunkSet) -> Check:
    if chunk_set.total_chunks == 0:
        return False, "No chunks produced. Pipeline cannot support retrieval."
    return True, f"{chunk_set.total_chunks} chunks produced."


def check_no_empty_chunks(chunk_set: ChunkSet) -> Check:
    empty = [c.chunk_id for c in chunk_set.chunks if not c.content.strip()]
    if empty:
        return False, f"{len(empty)} chunk(s) have empty content: {empty[:5]}"
    return True, "All chunks have non-empty content."


def check_degraded_chunk_rate(chunk_set: ChunkSet, max_rate: float = 0.5) -> Check:
    total = chunk_set.total_chunks
    if total == 0:
        return True, "No chunks."
    rate = chunk_set.degraded_chunks / total
    if rate > max_rate:
        return False, f"{rate:.0%} of chunks are degraded — too high for reliable retrieval."
    return True, f"Degraded chunk rate: {rate:.0%}"


def check_chunks_have_page_refs(chunk_set: ChunkSet) -> Check:
    missing_refs = [c.chunk_id for c in chunk_set.chunks if not c.page_refs and not c.table_refs]
    if missing_refs:
        return False, f"{len(missing_refs)} chunk(s) have no page or table refs (missing provenance)."
    return True, "All chunks have provenance refs."


# ---------------------------------------------------------------------------
# Graph checks
# ---------------------------------------------------------------------------


def check_graph_has_nodes(graph_node_count: int) -> Check:
    if graph_node_count == 0:
        return False, "Graph has no nodes."
    return True, f"Graph has {graph_node_count} nodes."


def check_structural_edges_present(structural_edge_count: int) -> Check:
    if structural_edge_count == 0:
        return False, "No structural edges in graph. Hierarchy is not represented."
    return True, f"{structural_edge_count} structural edges."


def check_no_orphan_chunks_in_graph(graph_node_count: int, chunk_count: int) -> Check:
    """
    Basic sanity: graph should have at least as many nodes as chunks
    (every chunk gets a Chunk node).
    """
    if chunk_count > 0 and graph_node_count < chunk_count:
        return (
            False,
            f"Graph has {graph_node_count} nodes but {chunk_count} chunks — "
            "some chunks may not have graph nodes."
        )
    return True, "Chunk-to-graph node coverage looks consistent."


# ---------------------------------------------------------------------------
# Overall hallucination risk summary
# ---------------------------------------------------------------------------


def hallucination_risk_warnings(document: Optional[CanonicalDocument]) -> List[str]:
    """
    Return a list of hallucination risk warnings based on document state.
    Implements rules from docs/validation/hallucination-prevention.md.
    """
    warnings: List[str] = []
    if document is None:
        warnings.append("Document not extracted — all retrieval answers will fail evidence check.")
        return warnings

    low_conf = document.low_confidence_blocks(0.65)
    if len(low_conf) > 0:
        warnings.append(
            f"{len(low_conf)} low-confidence block(s) present. "
            "Answers citing these blocks should be flagged as partially supported."
        )

    if document.degraded_block_count() > 0:
        warnings.append(
            f"{document.degraded_block_count()} degraded block(s). "
            "These blocks must not be used as authoritative evidence without review."
        )

    if not document.has_structure() and document.block_count() > 20:
        warnings.append(
            "No structural hierarchy detected in a large document. "
            "Clause-level retrieval precision will be reduced."
        )

    for table in document.tables:
        if table.confidence.overall < 0.7:
            warnings.append(
                f"Table {table.table_id} has low confidence ({table.confidence.overall:.2f}). "
                "Table-derived answers carry hallucination risk."
            )

    return warnings
