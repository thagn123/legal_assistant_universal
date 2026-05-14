"""
Chunk schema.

Matches docs/chunking/chunking-strategies.md and docs/chunking/chunking-decision-tree.md.

A Chunk is the retrieval unit. It must carry:
- structural path (so retrieval knows which article/clause it came from)
- source anchors (page, block, region refs)
- citations
- provenance and confidence
- degraded flag (chunks from low-confidence extraction must be marked)
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel
except ImportError:
    from src.utils.compat import BaseModel  # type: ignore


class ChunkingDecision(BaseModel):
    """
    Routing decision emitted before chunk generation begins.
    Logged and auditable. Never silently overridden at runtime.
    """

    document_id: str
    strategy: str                   # structural | semantic | legal_aware | table_aware | mixed_group | long_local_structural | conservative_fallback
    secondary_rules: List[str] = [] # e.g. ["enforce_table_header_preservation", "create_evidence_sibling_chunks"]
    fallback_strategy: str = ""
    routing_signals: Dict[str, Any] = {}
    long_document_threshold: int = 30
    decision_confidence: float = 1.0
    reason_codes: List[str] = []
    created_at: str = ""


class Chunk(BaseModel):
    """
    A retrieval unit derived from one or more structurally related blocks.

    The following must NEVER be split across two chunks:
    - article number from its title and opening text
    - definition term from its definition body
    - clause condition from its operative consequence (when short)
    - table header from the rows that depend on it
    - amendment instruction from its target citation
    """

    chunk_id: str
    document_id: str
    chunk_type: str                         # text | table | image | mixed | heading_context
    content_format: str = "markdown"        # markdown | html | plain
    content: str = ""

    # Structure context
    structure_path: List[str] = []          # e.g. ["Chapter I", "Article 5", "Clause 5.1"]
    parent_chunk_id: Optional[str] = None
    sibling_chunk_ids: List[str] = []

    # Source anchors
    page_refs: List[str] = []
    block_refs: List[str] = []
    table_refs: List[str] = []
    image_refs: List[str] = []
    citations: List[str] = []

    # Overlap metadata
    overlap_from: List[str] = []            # chunk_ids this chunk borrows context from

    # Quality signals
    token_estimate: int = 0
    confidence: float = 1.0
    degraded: bool = False
    degraded_reasons: List[str] = []

    # Jurisdiction / version context (always carried into every chunk)
    jurisdiction: str = ""
    version_label: str = ""
    document_type: str = ""

    # Multilingual retrieval metadata
    language: str = ""                       # primary language of chunk content: "vi" | "en" | "mixed"
    canonical_refs: List[str] = []           # canonical structure IDs: ["article_1", "clause_3_a"]
    hierarchy_path: str = ""                 # human-readable path: "Chương I › Điều 1 › Khoản 3"

    def is_authoritative(self, threshold: float = 0.65) -> bool:
        """A chunk is authoritative for answer generation only if not degraded and above threshold."""
        return not self.degraded and self.confidence >= threshold


class ChunkSet(BaseModel):
    """
    Full output of the chunking stage for one document.
    """

    document_id: str
    chunks: List[Chunk] = []
    chunking_decision: Optional[ChunkingDecision] = None
    total_chunks: int = 0
    degraded_chunks: int = 0
    strategy_used: str = ""
    created_at: str = ""

    def authoritative_chunks(self, threshold: float = 0.65) -> List[Chunk]:
        return [c for c in self.chunks if c.is_authoritative(threshold)]

    def table_chunks(self) -> List[Chunk]:
        return [c for c in self.chunks if c.chunk_type == "table"]

    def text_chunks(self) -> List[Chunk]:
        return [c for c in self.chunks if c.chunk_type == "text"]
