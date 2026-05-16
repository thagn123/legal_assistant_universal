"""
GraphRAG traversal engine.

Given seed node IDs (from retrieval), expands along legal graph edges to
gather related context within defined depth, confidence, and fan-out limits.

Design rules (from docs/graphrag/traversal-and-expansion.md):
  - Always start from retrieved evidence seeds, not the full graph.
  - Prefer structural and citation edges over semantic edges.
  - Carry path provenance for every expanded node.
  - Stop when confidence or relevance decays below threshold.
  - Cap fan-out on high-degree nodes to prevent graph explosion.
  - Never return expanded nodes without the path that justified them.

Usage:
    from src.graphrag.traversal import GraphTraversal, TraversalPolicy

    policy = TraversalPolicy()
    traversal = GraphTraversal(graph)
    result = traversal.expand(seed_node_ids=["node_abc"], policy=policy)
    for r in result.results:
        print(r.node.label, "depth=", r.depth, "score=", r.score)
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set

from src.schemas.graph import (
    CITATION_EDGES,
    SEMANTIC_EDGES,
    STRUCTURAL_EDGES,
    GraphEdge,
    GraphNode,
    GraphSubgraph,
)


# ---------------------------------------------------------------------------
# Traversal policy
# ---------------------------------------------------------------------------


@dataclass
class TraversalPolicy:
    """
    Controls which edges to follow, how deep to go, and when to stop.

    Defaults are calibrated for factual clause lookup (the most common case).
    Drafting and risk-analysis queries should use wider policies.
    """

    # Edge types to traverse (defaults: structural + citation; NOT semantic)
    allowed_edge_types: FrozenSet[str] = field(
        default_factory=lambda: STRUCTURAL_EDGES | CITATION_EDGES
    )

    # Maximum BFS depth from any seed node
    max_depth: int = 3

    # Minimum edge confidence required to traverse
    min_edge_confidence: float = 0.60

    # Maximum outgoing edges to follow from a single node (fan-out cap)
    max_fan_out: int = 10

    # Maximum total nodes to return (context budget)
    max_nodes: int = 30

    # Minimum node score to include in results (prunes low-quality expansions)
    min_node_score: float = 0.20

    # Edge types to never follow (overrides allowed_edge_types)
    blocked_edge_types: FrozenSet[str] = field(
        default_factory=lambda: frozenset({"CONTRADICTS", "SUPPORTS"})
    )


# ---------------------------------------------------------------------------
# Traversal result objects
# ---------------------------------------------------------------------------


@dataclass
class TraversalResult:
    """A single node reached during graph expansion."""
    node: GraphNode
    path_edges: List[GraphEdge]     # ordered list of edges from seed to this node
    score: float                    # composite score
    depth: int                      # BFS depth from nearest seed

    @property
    def path_node_ids(self) -> List[str]:
        """Node IDs along the path (from → to chain)."""
        if not self.path_edges:
            return [self.node.node_id]
        ids = [self.path_edges[0].from_node_id]
        for e in self.path_edges:
            ids.append(e.to_node_id)
        return ids


@dataclass
class ExpandedEvidenceSet:
    """Full result of a traversal from one or more seed nodes."""
    seed_node_ids: List[str]
    results: List[TraversalResult]   # sorted by score descending
    stop_reason: str                 # "budget_exhausted" | "depth_limit" | "complete"
    suppressed_count: int = 0        # nodes filtered by score/confidence threshold

    def node_ids(self) -> List[str]:
        return [r.node.node_id for r in self.results]

    def nodes_by_type(self, node_type: str) -> List[GraphNode]:
        return [r.node for r in self.results if r.node.node_type == node_type]


# ---------------------------------------------------------------------------
# Edge weight table (higher = more useful to traverse)
# ---------------------------------------------------------------------------

_EDGE_WEIGHTS: Dict[str, float] = {
    # Structural hierarchy — always follow, high value
    "CONTAINS":          0.90,
    "PRECEDES":          0.60,
    "HAS_TABLE":         0.85,
    "HAS_IMAGE":         0.70,
    "DERIVED_TO_CHUNK":  0.80,
    # Citations — high value for legal interpretation
    "CITES":             0.85,
    "RESOLVES_TO":       0.80,
    "REFERS_TO":         0.75,
    # Semantic edges (only if explicitly allowed)
    "DEFINES":           0.70,
    "APPLIES_TO":        0.60,
    "IMPOSES":           0.65,
    "QUALIFIED_BY":      0.65,
    "EXCEPTED_BY":       0.65,
    "ENFORCED_BY":       0.60,
    "MENTIONS":          0.50,
    "AMENDS":            0.85,
    # Legal amendment, override, and conflict edges
    "OVERRIDES":         0.92,
    "INVALIDATES":       0.90,
    "CONFLICTS_WITH":    0.88,
    "REQUIRES":          0.82,
    "DEPENDS_ON":        0.78,
    # Alias (cross-language)
    "ALIAS_OF":          0.70,
    # Default
    "SUPPORTS":          0.40,
    "CONTRADICTS":       0.40,
}

_DEPTH_PENALTY = 0.10   # score reduction per BFS depth level


# ---------------------------------------------------------------------------
# GraphTraversal
# ---------------------------------------------------------------------------


class GraphTraversal:
    """
    BFS-based graph traversal engine for legal knowledge graphs.

    Builds adjacency and node indexes at construction time for O(1) lookups
    during expansion. Thread-safe for read-only graph access.

    Args:
        graph: The GraphSubgraph to traverse.
    """

    def __init__(self, graph: GraphSubgraph) -> None:
        self._graph = graph
        # node_id → GraphNode
        self._nodes: Dict[str, GraphNode] = {n.node_id: n for n in graph.nodes}
        # from_node_id → list of outgoing edges
        self._adj: Dict[str, List[GraphEdge]] = {}
        for edge in graph.edges:
            self._adj.setdefault(edge.from_node_id, []).append(edge)

    # ── Public API ────────────────────────────────────────────────────────

    def expand(
        self,
        seed_node_ids: List[str],
        policy: Optional[TraversalPolicy] = None,
    ) -> ExpandedEvidenceSet:
        """
        BFS expansion from seed nodes under the given policy.

        Args:
            seed_node_ids: Node IDs of the retrieval seeds (starting points).
            policy:        Traversal policy. Defaults to TraversalPolicy() if None.

        Returns:
            ExpandedEvidenceSet with results sorted by score descending.
        """
        if policy is None:
            policy = TraversalPolicy()

        # Validate seeds exist in graph
        valid_seeds = [sid for sid in seed_node_ids if sid in self._nodes]
        if not valid_seeds:
            return ExpandedEvidenceSet(
                seed_node_ids=seed_node_ids,
                results=[],
                stop_reason="no_valid_seeds",
            )

        # BFS queue entries: (node_id, depth, path_edges, parent_score)
        queue: deque = deque()
        visited: Set[str] = set(valid_seeds)
        all_results: List[TraversalResult] = []
        suppressed = 0

        # Enqueue seeds with depth=0 and score=1.0
        for sid in valid_seeds:
            queue.append((sid, 0, [], 1.0))

        stop_reason = "complete"

        while queue:
            node_id, depth, path_edges, parent_score = queue.popleft()
            node = self._nodes.get(node_id)
            if node is None:
                continue

            # Score for this node
            score = self._score(node, depth, path_edges, parent_score)

            if score < policy.min_node_score:
                suppressed += 1
                continue

            all_results.append(TraversalResult(
                node=node,
                path_edges=path_edges,
                score=score,
                depth=depth,
            ))

            # Check budget
            if len(all_results) >= policy.max_nodes:
                stop_reason = "budget_exhausted"
                break

            # Don't expand beyond max_depth
            if depth >= policy.max_depth:
                if stop_reason == "complete":
                    stop_reason = "depth_limit"
                continue

            # Expand neighbors via outgoing edges
            neighbors = self._adj.get(node_id, [])
            fan_out = 0
            for edge in neighbors:
                if fan_out >= policy.max_fan_out:
                    break
                if edge.edge_type in policy.blocked_edge_types:
                    continue
                if edge.edge_type not in policy.allowed_edge_types:
                    continue
                if edge.confidence < policy.min_edge_confidence:
                    continue
                neighbor_id = edge.to_node_id
                if neighbor_id in visited:
                    continue
                visited.add(neighbor_id)
                queue.append((
                    neighbor_id,
                    depth + 1,
                    path_edges + [edge],
                    score,
                ))
                fan_out += 1

        # Sort by score descending
        all_results.sort(key=lambda r: r.score, reverse=True)

        return ExpandedEvidenceSet(
            seed_node_ids=valid_seeds,
            results=all_results,
            stop_reason=stop_reason,
            suppressed_count=suppressed,
        )

    def neighbors(
        self,
        node_id: str,
        edge_types: Optional[FrozenSet[str]] = None,
        min_confidence: float = 0.60,
    ) -> List[tuple[GraphNode, GraphEdge]]:
        """
        Return the immediate neighbors of a node, filtered by edge type and confidence.

        Args:
            node_id:        Source node ID.
            edge_types:     If given, only follow these edge types.
            min_confidence: Minimum edge confidence.

        Returns:
            List of (neighbor_node, edge) pairs.
        """
        result: List[tuple[GraphNode, GraphEdge]] = []
        for edge in self._adj.get(node_id, []):
            if edge.confidence < min_confidence:
                continue
            if edge_types and edge.edge_type not in edge_types:
                continue
            neighbor = self._nodes.get(edge.to_node_id)
            if neighbor:
                result.append((neighbor, edge))
        return result

    # ── Scoring ───────────────────────────────────────────────────────────

    def _score(
        self,
        node: GraphNode,
        depth: int,
        path_edges: List[GraphEdge],
        parent_score: float,
    ) -> float:
        """
        Composite score for a traversal result node.

        Factors:
        - Parent score propagated from seed
        - Edge-type weight of the incoming edge
        - Depth penalty (each hop loses some relevance)
        - Node confidence penalty for degraded nodes
        """
        if depth == 0:
            # Seed nodes score at their own confidence
            return round(max(node.confidence, 0.5), 4)

        incoming_edge = path_edges[-1] if path_edges else None
        edge_weight = _EDGE_WEIGHTS.get(incoming_edge.edge_type, 0.5) if incoming_edge else 0.5
        incoming_conf = incoming_edge.confidence if incoming_edge else 1.0

        score = parent_score * edge_weight * incoming_conf
        score -= depth * _DEPTH_PENALTY
        if node.degraded:
            score *= 0.7

        return round(max(score, 0.0), 4)
