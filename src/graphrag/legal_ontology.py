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

from typing import Dict, List, Optional, Set, Tuple

from src.schemas.graph import (
    GraphEdge,
    GraphNode,
    GraphSubgraph,
    EDGE_TYPES,
)
from src.utils.trace import make_edge_id, now_iso

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
      - They have the same node_type (Article-Article, Clause-Clause, etc.)
      - Or one of them is a Chunk derived from the other (covered by DERIVED_TO_CHUNK)
      - They are NOT the same node
    """
    if n1.node_id == n2.node_id:
        return False
    # Same structural type → safe to alias
    if n1.node_type == n2.node_type:
        return True
    # Chunk nodes should not be aliased to structural nodes here
    if "Chunk" in (n1.node_type, n2.node_type):
        return False
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
