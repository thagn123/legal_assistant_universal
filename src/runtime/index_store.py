"""
Document index store — loads stored ChunkSets and GraphSubgraphs from
SQLite and assembles EvidenceBundles for /queries and /actions endpoints.

Design:
- Indexes are built on-demand per request (no background indexing thread).
- All chunk/graph reads are tenant-scoped: only documents owned by user_id
  are loaded.
- If no document_ids are specified, all ready documents for that user are used.
- Falls back to empty_bundle if nothing is indexed yet.
"""

from __future__ import annotations

import logging
from typing import List, Optional

from src.graphrag.evidence_bundle import (
    EvidenceBundle,
    assemble_evidence_bundle,
    empty_bundle,
)
from src.graphrag.traversal import GraphTraversal, TraversalPolicy
from src.retrieval.retrieval_engine import RetrievalEngine
from src.runtime.processor import deserialize_graph
from src.runtime.storage import StorageLayer
from src.schemas.chunk import Chunk, ChunkSet
from src.schemas.graph import GraphSubgraph

logger = logging.getLogger(__name__)


class DocumentIndexStore:
    """
    Loads stored ChunkSets and Graphs from the StorageLayer, builds a
    combined retrieval index, and returns EvidenceBundles for a query.

    Thread-safe: no mutable state; every call is independent.
    """

    def get_bundles(
        self,
        storage: StorageLayer,
        user_id: str,
        document_ids: List[str],
        query: str,
        query_id: str,
        max_retrieval_results: int = 10,
    ) -> List[EvidenceBundle]:
        """
        Build EvidenceBundles for the given query over the user's indexed documents.

        Args:
            storage:              StorageLayer instance.
            user_id:              Caller's user ID (tenant scope enforced).
            document_ids:         Restrict search to these docs; empty = all ready docs.
            query:                Free-text query string.
            query_id:             Stable identifier for this query (for bundle tracing).
            max_retrieval_results: Max chunks returned by the retrieval engine.

        Returns:
            List with one EvidenceBundle (SUPPORTED / PARTIALLY_SUPPORTED / UNSUPPORTED).
        """
        # ── 1. Resolve which documents to load ────────────────────────────
        if document_ids:
            # Verify tenant ownership for each specified doc
            docs = [
                storage.get_document(user_id, did)
                for did in document_ids
            ]
            docs = [d for d in docs if d is not None]
        else:
            docs = storage.list_documents(user_id)

        ready_doc_ids = [d.doc_id for d in docs if d.status == "ready"]

        if not ready_doc_ids:
            return [empty_bundle(query_id, "No indexed documents available. Upload and wait for processing to complete.")]

        # ── 2. Load ChunkSets ──────────────────────────────────────────────
        all_chunks: List[Chunk] = []
        for doc_id in ready_doc_ids:
            cs_json = storage.load_chunk_set_json(doc_id)
            if not cs_json:
                continue
            try:
                cs = ChunkSet.model_validate_json(cs_json)
                all_chunks.extend(cs.chunks)
            except Exception as exc:
                logger.warning("index_store: failed to load chunks for doc_id=%s: %s", doc_id, exc)

        if not all_chunks:
            return [empty_bundle(query_id, "Documents are indexed but no chunks were found. Re-upload to re-process.")]

        # ── 3. Run retrieval ───────────────────────────────────────────────
        combined_chunk_set = ChunkSet(
            document_id="combined",
            chunks=all_chunks,
            total_chunks=len(all_chunks),
        )
        engine = RetrievalEngine(combined_chunk_set)
        retrieval_results = engine.search(query, max_results=max_retrieval_results)

        if not retrieval_results:
            return [empty_bundle(query_id, "No matching evidence found for this query.")]

        seed_chunks = [r.chunk for r in retrieval_results]
        logger.info(
            "index_store: query_id=%s retrieved %d seed chunks from %d docs",
            query_id, len(seed_chunks), len(ready_doc_ids),
        )

        # ── 4. Graph traversal ─────────────────────────────────────────────
        expansion: Optional[object] = None
        all_graph_nodes = []
        all_graph_edges = []

        for doc_id in ready_doc_ids:
            g_json = storage.load_graph_json(doc_id)
            if not g_json:
                continue
            try:
                g = deserialize_graph(g_json)
                all_graph_nodes.extend(g.nodes)
                all_graph_edges.extend(g.edges)
            except Exception as exc:
                logger.warning("index_store: failed to load graph for doc_id=%s: %s", doc_id, exc)

        if all_graph_nodes:
            combined_graph = GraphSubgraph(
                document_id="combined",
                nodes=all_graph_nodes,
                edges=all_graph_edges,
            )
            traversal = GraphTraversal(combined_graph)
            seed_ids = [c.chunk_id for c in seed_chunks]
            expansion = traversal.expand(seed_ids, policy=TraversalPolicy())
            logger.info(
                "index_store: graph traversal returned %d expanded nodes",
                len(expansion.results) if expansion else 0,
            )

        # ── 5. Assemble EvidenceBundle ─────────────────────────────────────
        bundle = assemble_evidence_bundle(
            query_id=query_id,
            seed_chunks=seed_chunks,
            expansion=expansion,
            chunk_set=combined_chunk_set,
        )
        return [bundle]
