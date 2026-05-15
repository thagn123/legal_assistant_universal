"""
Evidence bundle assembly for GraphRAG reasoning.

Takes retrieval results and traversal expansion, assembles coherent evidence
bundles that carry source chunks, graph paths, and support status for downstream
answer generation.

Design rules:
  - Evidence bundles are built from chunks, not from raw text.
  - Support status is derived from chunk confidence, not inferred.
  - Every bundle carries its source path so citations can be reconstructed.
  - Bundles never invent content; unsupported questions get empty bundles.

Usage:
    from src.graphrag.evidence_bundle import EvidenceBundle, assemble_evidence_bundle
    from src.graphrag.traversal import GraphTraversal, TraversalPolicy

    traversal = GraphTraversal(graph)
    expansion = traversal.expand(seed_node_ids, policy)
    bundle = assemble_evidence_bundle(
        query_id="q1",
        seed_chunks=retrieved_chunks,
        expansion=expansion,
        chunk_set=chunk_set,
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.graphrag.traversal import ExpandedEvidenceSet, TraversalResult
from src.schemas.chunk import Chunk, ChunkSet


# ---------------------------------------------------------------------------
# Support status constants
# ---------------------------------------------------------------------------

SUPPORTED = "supported"
PARTIALLY_SUPPORTED = "partially_supported"
UNSUPPORTED = "unsupported"


# ---------------------------------------------------------------------------
# Evidence bundle schema
# ---------------------------------------------------------------------------


@dataclass
class EvidenceBundle:
    """
    A coherent set of evidence chunks assembled for a single query.

    Fields:
        query_id:           Identifier for the originating query.
        seed_chunk_ids:     Chunk IDs from the primary retrieval pass.
        expanded_node_ids:  Node IDs reached by graph traversal.
        evidence_chunks:    Ordered list of chunks (seeds first, then expanded).
        support_status:     "supported" | "partially_supported" | "unsupported"
        confidence:         Aggregate confidence across evidence chunks.
        graph_paths:        List of node-ID paths justifying each expanded chunk.
        degraded_chunks:    Subset of evidence_chunks that are degraded.
        citations:          Deduplicated citation strings from all evidence chunks.
        warnings:           Assembly-time warnings (missing chunks, low confidence, etc.)
    """

    query_id: str
    seed_chunk_ids: List[str]
    expanded_node_ids: List[str]
    evidence_chunks: List[Chunk]
    support_status: str
    confidence: float
    graph_paths: List[List[str]] = field(default_factory=list)
    degraded_chunks: List[Chunk] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def is_authoritative(self, threshold: float = 0.65) -> bool:
        """True if the bundle has non-empty, non-degraded evidence above threshold."""
        return (
            self.support_status == SUPPORTED
            and self.confidence >= threshold
            and len(self.evidence_chunks) > 0
            and len(self.degraded_chunks) < len(self.evidence_chunks)
        )

    def summary(self) -> str:
        return (
            f"EvidenceBundle(status={self.support_status}, "
            f"chunks={len(self.evidence_chunks)}, "
            f"confidence={self.confidence:.2f}, "
            f"degraded={len(self.degraded_chunks)})"
        )


# ---------------------------------------------------------------------------
# Assembly function
# ---------------------------------------------------------------------------


def assemble_evidence_bundle(
    query_id: str,
    seed_chunks: List[Chunk],
    expansion: ExpandedEvidenceSet,
    chunk_set: Optional[ChunkSet],
    authority_threshold: float = 0.65,
) -> EvidenceBundle:
    """
    Assemble an EvidenceBundle from retrieval seeds and graph traversal expansion.

    Assembly strategy:
    1. Start with seed chunks (from retrieval) — always included.
    2. For each expanded node that is a Chunk type, look up the chunk from chunk_set.
    3. De-duplicate chunks (seed chunks take priority).
    4. Compute aggregate confidence as weighted average (seed weight = 2x expanded).
    5. Assign support_status based on whether authoritative chunks exist.

    Args:
        query_id:           Query identifier for provenance.
        seed_chunks:        Chunks from primary retrieval (highest priority).
        expansion:          Graph traversal result.
        chunk_set:          The ChunkSet to look up expanded chunk nodes.
        authority_threshold: Confidence threshold for SUPPORTED status.

    Returns:
        EvidenceBundle ready for reasoning.
    """
    warnings: List[str] = []

    # Build chunk lookup from chunk_set
    chunk_by_id: Dict[str, Chunk] = {}
    if chunk_set:
        chunk_by_id = {c.chunk_id: c for c in chunk_set.chunks}

    # ── Step 1: Start with seed chunks ──────────────────────────────────
    seen_chunk_ids: set = set()
    evidence_chunks: List[Chunk] = []
    for chunk in seed_chunks:
        if chunk.chunk_id not in seen_chunk_ids:
            evidence_chunks.append(chunk)
            seen_chunk_ids.add(chunk.chunk_id)

    # ── Step 2: Add chunks from expanded Chunk nodes ─────────────────────
    expanded_node_ids: List[str] = []
    graph_paths: List[List[str]] = []

    for result in expansion.results:
        expanded_node_ids.append(result.node.node_id)
        if result.path_edges:
            graph_paths.append(result.path_node_ids)

        if result.node.node_type != "Chunk":
            continue

        # The node label is the chunk_id for Chunk nodes
        chunk_id = result.node.label
        if chunk_id in seen_chunk_ids:
            continue

        chunk = chunk_by_id.get(chunk_id)
        if chunk is None:
            # Try looking up by node_id suffix
            for cid, c in chunk_by_id.items():
                if result.node.node_id.endswith(cid.replace("_", "")[-8:]):
                    chunk = c
                    break

        if chunk:
            evidence_chunks.append(chunk)
            seen_chunk_ids.add(chunk_id)
        else:
            warnings.append(f"Expanded Chunk node {result.node.node_id!r} not found in chunk_set")

    # ── Step 3: Identify degraded chunks ────────────────────────────────
    degraded = [c for c in evidence_chunks if c.degraded]

    # ── Step 4: Compute aggregate confidence ────────────────────────────
    if not evidence_chunks:
        aggregate_confidence = 0.0
    else:
        seed_ids = {c.chunk_id for c in seed_chunks}
        weighted_sum = 0.0
        total_weight = 0.0
        for chunk in evidence_chunks:
            weight = 2.0 if chunk.chunk_id in seed_ids else 1.0
            weighted_sum += chunk.confidence * weight
            total_weight += weight
        aggregate_confidence = round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0

    # ── Step 5: Determine support status ────────────────────────────────
    authoritative = [c for c in evidence_chunks if c.is_authoritative(authority_threshold)]
    if not evidence_chunks:
        support_status = UNSUPPORTED
    elif not authoritative:
        support_status = PARTIALLY_SUPPORTED
        warnings.append("All evidence chunks are below authority threshold or degraded.")
    elif len(degraded) > len(evidence_chunks) // 2:
        support_status = PARTIALLY_SUPPORTED
    else:
        support_status = SUPPORTED

    if not seed_chunks:
        support_status = UNSUPPORTED
        warnings.append("No seed chunks provided — query has no retrieval basis.")

    # ── Step 6: Collect citations ────────────────────────────────────────
    citations: List[str] = []
    seen_citations: set = set()
    for chunk in evidence_chunks:
        for cit in chunk.citations:
            if cit and cit not in seen_citations:
                citations.append(cit)
                seen_citations.add(cit)

    return EvidenceBundle(
        query_id=query_id,
        seed_chunk_ids=[c.chunk_id for c in seed_chunks],
        expanded_node_ids=expanded_node_ids,
        evidence_chunks=evidence_chunks,
        support_status=support_status,
        confidence=aggregate_confidence,
        graph_paths=graph_paths,
        degraded_chunks=degraded,
        citations=citations,
        warnings=warnings,
    )


def empty_bundle(query_id: str, reason: str) -> EvidenceBundle:
    """Return an empty UNSUPPORTED bundle for queries with no retrieval basis."""
    return EvidenceBundle(
        query_id=query_id,
        seed_chunk_ids=[],
        expanded_node_ids=[],
        evidence_chunks=[],
        support_status=UNSUPPORTED,
        confidence=0.0,
        warnings=[reason],
    )
