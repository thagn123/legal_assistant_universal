"""
Legal ontology enrichment — ALIAS_OF edges and multilingual concept links.

This module adds cross-language ALIAS_OF edges to a GraphSubgraph so that
graph traversal can find Vietnamese and English representations of the same
legal concept as connected nodes.

Use cases:
  - "Article 1" node and "Điều 1" node from the same document → ALIAS_OF edge
  - "clause" concept node aliases to "khoản" node in a multilingual graph
  - Cross-document aliasing: same article in two document versions

Design rules:
  - ALIAS_OF edges are added to the graph, never to the node labels.
  - Alias detection is done via canonical_refs attribute on graph nodes.
  - No AI inference — canonical IDs drive aliasing.
  - Aliases are symmetric (if A aliases B, B aliases A).
  - Never create ALIAS_OF between nodes with incompatible types.

Usage:
    from src.graphrag.legal_ontology import OntologyEnricher
    from src.schemas.graph import GraphSubgraph

    enricher = OntologyEnricher()
    enriched_graph = enricher.enrich(graph)
    # → GraphSubgraph with ALIAS_OF edges added
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from src.schemas.graph import (
    GraphEdge,
    GraphNode,
    GraphSubgraph,
    EDGE_TYPES,
)
from src.utils.trace import make_edge_id

# ALIAS_OF is added to EDGE_TYPES in graph.py — guarded here for safety
_ALIAS_OF = "ALIAS_OF"


# ---------------------------------------------------------------------------
# Legal concept hierarchy (canonical level → node type)
# ---------------------------------------------------------------------------

_CANONICAL_TO_NODE_TYPE: Dict[str, str] = {
    "chapter": "Section",
    "part":    "Section",
    "section": "Section",
    "article": "Article",
    "clause":  "Clause",
    "point":   "Clause",
    "annex":   "Section",
}


# ---------------------------------------------------------------------------
# Alias detection helpers
# ---------------------------------------------------------------------------


def _get_canonical_refs(node: GraphNode) -> List[str]:
    """Extract canonical_refs from a node's attributes list."""
    return node.attributes.get("canonical_refs", []) or []


def _nodes_by_canonical_ref(
    nodes: List[GraphNode],
) -> Dict[str, List[GraphNode]]:
    """
    Build an index: canonical_ref → list of GraphNodes that carry it.

    Nodes may carry multiple canonical refs; they appear in every bucket.
    """
    index: Dict[str, List[GraphNode]] = {}
    for node in nodes:
        for ref in _get_canonical_refs(node):
            if ref not in index:
                index[ref] = []
            index[ref].append(node)
    return index


def _compatible_for_alias(n1: GraphNode, n2: GraphNode) -> bool:
    """
    Return True if two nodes may be aliased.

    Nodes can be aliased if:
      - They have the same structural node_type (Article-Article, Section-Section, etc.)
      - They are NOT the same node
      - Neither is a Chunk (chunks are linked via DERIVED_TO_CHUNK, not ALIAS_OF)

    NOTE: Chunk exclusion must be checked BEFORE the same-type check, otherwise
    two Chunk nodes would pass the same-type check and be incorrectly aliased.
    """
    if n1.node_id == n2.node_id:
        return False
    # Chunk nodes must not be aliased — their canonical_refs include all
    # structure path + content mention refs, creating O(n²) spurious edges.
    if "Chunk" in (n1.node_type, n2.node_type):
        return False
    # Same structural type → safe to alias
    if n1.node_type == n2.node_type:
        return True
    return False


# ---------------------------------------------------------------------------
# OntologyEnricher
# ---------------------------------------------------------------------------


class OntologyEnricher:
    """
    Adds ALIAS_OF edges to a GraphSubgraph to link multilingual equivalents.

    Aliasing strategy:
      1. Build an index of canonical_refs → nodes.
      2. For each canonical_ref that is shared by ≥2 nodes from different
         document_scope or different language contexts, add a symmetric
         ALIAS_OF edge pair.
      3. Never duplicate edges that already exist.
      4. Record a summary of edges added.

    Usage:
        enricher = OntologyEnricher()
        enriched = enricher.enrich(graph)
        print(f"Added {enricher.last_run_edges_added} ALIAS_OF edges")
    """

    def __init__(self) -> None:
        self.last_run_edges_added: int = 0
        self.last_run_log: List[str] = []

    def enrich(self, graph: GraphSubgraph) -> GraphSubgraph:
        """
        Add ALIAS_OF edges to the graph for nodes sharing a canonical_ref.

        Returns the same GraphSubgraph object with edges list extended.
        (Does not mutate node attributes.)

        Args:
            graph: The GraphSubgraph to enrich.

        Returns:
            The enriched GraphSubgraph.
        """
        self.last_run_edges_added = 0
        self.last_run_log = []

        if not graph.nodes:
            return graph

        # Check that ALIAS_OF is a recognised edge type
        if _ALIAS_OF not in EDGE_TYPES:
            self.last_run_log.append(
                f"WARNING: {_ALIAS_OF!r} not in EDGE_TYPES — skipping ontology enrichment. "
                "Add ALIAS_OF to graph.py EDGE_TYPES."
            )
            return graph

        # Build canonical ref index
        ref_index = _nodes_by_canonical_ref(graph.nodes)

        # Collect existing edge pairs to avoid duplicates
        existing_pairs: Set[Tuple[str, str]] = {
            (e.from_node_id, e.to_node_id)
            for e in graph.edges
            if e.edge_type == _ALIAS_OF
        }

        new_edges: List[GraphEdge] = []

        for canonical_ref, nodes in ref_index.items():
            if len(nodes) < 2:
                continue
            # Add a symmetric ALIAS_OF edge between every compatible pair
            for i in range(len(nodes)):
                for j in range(i + 1, len(nodes)):
                    n1, n2 = nodes[i], nodes[j]
                    if not _compatible_for_alias(n1, n2):
                        continue

                    pair_fwd = (n1.node_id, n2.node_id)
                    pair_rev = (n2.node_id, n1.node_id)

                    if pair_fwd not in existing_pairs:
                        edge = GraphEdge(
                            edge_id=make_edge_id(n1.node_id, _ALIAS_OF, n2.node_id),
                            edge_type=_ALIAS_OF,
                            from_node_id=n1.node_id,
                            to_node_id=n2.node_id,
                            confidence=0.95,
                            provenance=f"canonical_ref:{canonical_ref}",
                            method="canonical_ref_match",
                        )
                        new_edges.append(edge)
                        existing_pairs.add(pair_fwd)
                        self.last_run_edges_added += 1

                    if pair_rev not in existing_pairs:
                        edge = GraphEdge(
                            edge_id=make_edge_id(n2.node_id, _ALIAS_OF, n1.node_id),
                            edge_type=_ALIAS_OF,
                            from_node_id=n2.node_id,
                            to_node_id=n1.node_id,
                            confidence=0.95,
                            provenance=f"canonical_ref:{canonical_ref}",
                            method="canonical_ref_match",
                        )
                        new_edges.append(edge)
                        existing_pairs.add(pair_rev)

        if new_edges:
            graph.edges = list(graph.edges) + new_edges
            self.last_run_log.append(
                f"Added {self.last_run_edges_added} ALIAS_OF edges "
                f"across {len(ref_index)} canonical refs"
            )

        return graph


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------


def add_alias_edges(graph: GraphSubgraph) -> GraphSubgraph:
    """
    Convenience function: run OntologyEnricher.enrich() on a graph.

    Returns the enriched graph.
    """
    return OntologyEnricher().enrich(graph)


def add_cross_document_alias_edges(graphs: List[GraphSubgraph]) -> Dict[str, int]:
    """
    Add ALIAS_OF edges between nodes from DIFFERENT documents that share a canonical_ref.

    This is the cross-document enrichment pass. It runs after all documents have
    been individually processed and their graphs built. It finds Section/Article/Clause
    nodes across documents that share the same canonical_ref (e.g., "article_1" from an
    English doc and "article_1" from a Vietnamese doc) and links them with symmetric
    ALIAS_OF edges, one edge stored in each document's GraphSubgraph.

    Args:
        graphs: List of GraphSubgraph objects (one per document).

    Returns:
        Dict mapping document_id → count of ALIAS_OF edges added to that graph.
        Returns empty dict if fewer than 2 graphs are provided.
    """
    if len(graphs) < 2:
        return {}

    if _ALIAS_OF not in EDGE_TYPES:
        return {}

    # Build cross-graph index: canonical_ref → list of (node, graph_index)
    ref_index: Dict[str, List[Tuple[GraphNode, int]]] = {}
    for g_idx, graph in enumerate(graphs):
        for node in graph.nodes:
            if node.node_type == "Chunk":
                continue
            for ref in _get_canonical_refs(node):
                ref_index.setdefault(ref, []).append((node, g_idx))

    # Pre-build existing ALIAS_OF pair sets per graph to avoid duplicates
    existing: List[Set[Tuple[str, str]]] = [
        {(e.from_node_id, e.to_node_id) for e in g.edges if e.edge_type == _ALIAS_OF}
        for g in graphs
    ]

    counts: Dict[str, int] = {g.document_id: 0 for g in graphs}

    for canonical_ref, entries in ref_index.items():
        if len(entries) < 2:
            continue
        for i in range(len(entries)):
            for j in range(i + 1, len(entries)):
                n1, g1_idx = entries[i]
                n2, g2_idx = entries[j]

                if g1_idx == g2_idx:
                    continue  # same document — handled by intra-doc OntologyEnricher
                if not _compatible_for_alias(n1, n2):
                    continue

                pair_fwd = (n1.node_id, n2.node_id)
                pair_rev = (n2.node_id, n1.node_id)

                # Forward edge lives in g1
                if pair_fwd not in existing[g1_idx]:
                    edge = GraphEdge(
                        edge_id=make_edge_id(n1.node_id, _ALIAS_OF, n2.node_id),
                        edge_type=_ALIAS_OF,
                        from_node_id=n1.node_id,
                        to_node_id=n2.node_id,
                        confidence=0.95,
                        provenance=f"cross_doc:{canonical_ref}",
                        method="cross_document_canonical_ref",
                    )
                    graphs[g1_idx].edges = list(graphs[g1_idx].edges) + [edge]
                    existing[g1_idx].add(pair_fwd)
                    counts[graphs[g1_idx].document_id] += 1

                # Reverse edge lives in g2
                if pair_rev not in existing[g2_idx]:
                    edge = GraphEdge(
                        edge_id=make_edge_id(n2.node_id, _ALIAS_OF, n1.node_id),
                        edge_type=_ALIAS_OF,
                        from_node_id=n2.node_id,
                        to_node_id=n1.node_id,
                        confidence=0.95,
                        provenance=f"cross_doc:{canonical_ref}",
                        method="cross_document_canonical_ref",
                    )
                    graphs[g2_idx].edges = list(graphs[g2_idx].edges) + [edge]
                    existing[g2_idx].add(pair_rev)
                    counts[graphs[g2_idx].document_id] += 1

    return counts
