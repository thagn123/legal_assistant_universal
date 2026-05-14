"""
Graph schema.

Matches docs/graphrag/graph-schema.md exactly.

Allowed node types and edge types are defined as constants to prevent
undocumented additions. Every node and edge requires provenance.
"""

from __future__ import annotations

import copy as _copy
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel
except ImportError:

    class BaseModel:  # type: ignore[no-redef]
        """Minimal Pydantic-compatible base when pydantic is not installed."""

        def __init__(self, **kwargs: Any) -> None:
            for cls in reversed(type(self).__mro__):
                for attr, val in vars(cls).items():
                    if attr.startswith("_") or callable(val):
                        continue
                    if isinstance(val, (classmethod, staticmethod, property)):
                        continue
                    object.__setattr__(self, attr, _copy.deepcopy(val))
            for k, v in kwargs.items():
                object.__setattr__(self, k, v)

        def model_dump(self) -> dict:
            return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

        def dict(self) -> dict:
            return self.model_dump()


# ---------------------------------------------------------------------------
# Allowed types (from graph-schema.md)
# ---------------------------------------------------------------------------

NODE_TYPES = frozenset([
    "Document", "DocumentVersion", "Section", "Article", "Clause",
    "Table", "TableRow", "ImageEvidence", "Chunk", "DefinedTerm",
    "Entity", "LegalConcept", "Citation", "Obligation", "Condition",
    "Exception", "Penalty",
])

EDGE_TYPES = frozenset([
    "CONTAINS",          # parent -> child (hierarchy)
    "PRECEDES",          # earlier -> later (source order)
    "HAS_TABLE",         # structure -> table
    "HAS_IMAGE",         # structure -> image
    "DERIVED_TO_CHUNK",  # source unit -> chunk
    "MENTIONS",          # source unit -> entity or concept
    "DEFINES",           # clause/article -> defined term
    "REFERS_TO",         # source unit -> source unit (cross-reference)
    "CITES",             # source unit -> citation
    "RESOLVES_TO",       # citation -> target node
    "APPLIES_TO",        # rule -> entity or jurisdiction
    "IMPOSES",           # clause/row -> obligation
    "QUALIFIED_BY",      # obligation/rule -> condition
    "EXCEPTED_BY",       # rule/obligation -> exception
    "ENFORCED_BY",       # rule/obligation -> penalty
    "SUPPORTS",          # evidence -> claim
    "CONTRADICTS",       # node -> node (requires explicit evidence)
    "AMENDS",            # source unit -> target source unit
    "ALIAS_OF",          # multilingual: node A is the cross-language alias of node B
])

# Edge families for confidence default rules
STRUCTURAL_EDGES = frozenset(["CONTAINS", "PRECEDES", "HAS_TABLE", "HAS_IMAGE", "DERIVED_TO_CHUNK"])
CITATION_EDGES = frozenset(["CITES", "RESOLVES_TO", "REFERS_TO"])
SEMANTIC_EDGES = frozenset([
    "MENTIONS", "DEFINES", "APPLIES_TO", "IMPOSES", "QUALIFIED_BY",
    "EXCEPTED_BY", "ENFORCED_BY", "SUPPORTS", "CONTRADICTS", "AMENDS",
])
ALIAS_EDGES = frozenset(["ALIAS_OF"])


class GraphNodeProvenance(BaseModel):
    document_id: str = ""
    source_anchor: str = ""
    extraction_method: str = ""
    processing_version: str = ""
    created_at: str = ""


class GraphNode(BaseModel):
    """A node in the legal knowledge graph."""

    node_id: str = ""
    node_type: str = ""
    label: str = ""
    document_scope: str = ""
    source_trace: Optional[Any] = None
    confidence: float = 1.0
    degraded: bool = False
    attributes: Dict[str, Any] = {}

    def validate_type(self) -> bool:
        return self.node_type in NODE_TYPES


class GraphEdge(BaseModel):
    """A directed edge in the legal knowledge graph."""

    edge_id: str = ""
    edge_type: str = ""
    from_node_id: str = ""
    to_node_id: str = ""
    confidence: float = 1.0
    provenance: str = ""
    method: str = ""
    active_version_range: Optional[str] = None

    def validate_type(self) -> bool:
        return self.edge_type in EDGE_TYPES

    def is_structural(self) -> bool:
        return self.edge_type in STRUCTURAL_EDGES

    def is_citation(self) -> bool:
        return self.edge_type in CITATION_EDGES

    def is_semantic(self) -> bool:
        return self.edge_type in SEMANTIC_EDGES


class GraphBuildJob(BaseModel):
    """Metadata record for a graph build run."""

    job_id: str = ""
    document_id: str = ""
    processing_version: str = ""
    input_artifact_ids: List[str] = []
    created_nodes: List[str] = []
    created_edges: List[str] = []
    dedup_actions: List[str] = []
    unresolved_items: List[str] = []
    validation_status: str = "pending"
    nodes_by_type: Dict[str, int] = {}
    edges_by_type: Dict[str, int] = {}


class GraphSubgraph(BaseModel):
    """The graph output for one document."""

    document_id: str = ""
    nodes: List[Any] = []
    edges: List[Any] = []
    build_job: Optional[Any] = None

    def node_count(self) -> int:
        return len(self.nodes)

    def edge_count(self) -> int:
        return len(self.edges)

    def structural_edge_count(self) -> int:
        return sum(1 for e in self.edges if e.is_structural())

    def nodes_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for n in self.nodes:
            counts[n.node_type] = counts.get(n.node_type, 0) + 1
        return counts

    def edges_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.edges:
            counts[e.edge_type] = counts.get(e.edge_type, 0) + 1
        return counts

    def low_confidence_edges(self, threshold: float = 0.60) -> List[Any]:
        return [e for e in self.edges if e.confidence < threshold]
