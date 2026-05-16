"""
Real document pipeline processor for the job runner.

Replaces the stub _default_processor in job_runner.py.
Runs all 8 pipeline stages (extract → chunk → graph → index) on the
uploaded document file, then persists the resulting ChunkSet and
GraphSubgraph to storage so retrieval can use them.

Usage (in create_app):
    from src.runtime.processor import build_document_processor
    processor = build_document_processor(storage)
    runner = JobRunner(storage, processor=processor)
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from src.config import PipelineConfig
from src.mongodb.client import ping as mongo_ping
from src.mongodb.mongo_storage import VectorStorage
from src.pipeline.embedding_stage import embed_chunks_into_mongo
from src.pipeline.orchestrator import PipelineOrchestrator
from src.runtime.storage import StorageLayer
from src.schemas.chunk import ChunkSet
from src.schemas.graph import GraphNode, GraphEdge, GraphSubgraph

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Serialization helpers (Graph uses List[Any] so needs manual round-trip)
# ---------------------------------------------------------------------------


def _serialize_chunk_set(chunk_set: ChunkSet) -> str:
    return chunk_set.model_dump_json()


def _serialize_graph(graph: GraphSubgraph) -> str:
    data = {
        "document_id": graph.document_id,
        "nodes": [
            n.model_dump() if hasattr(n, "model_dump") else dict(n)
            for n in graph.nodes
        ],
        "edges": [
            e.model_dump() if hasattr(e, "model_dump") else dict(e)
            for e in graph.edges
        ],
    }
    return json.dumps(data, ensure_ascii=False)


def deserialize_graph(json_str: str) -> GraphSubgraph:
    """Public helper used by IndexStore to reconstruct a GraphSubgraph."""
    data = json.loads(json_str)
    nodes = [GraphNode(**n) for n in data.get("nodes", [])]
    edges = [GraphEdge(**e) for e in data.get("edges", [])]
    return GraphSubgraph(
        document_id=data.get("document_id", ""),
        nodes=nodes,
        edges=edges,
    )


# ---------------------------------------------------------------------------
# Processor factory
# ---------------------------------------------------------------------------


def build_document_processor(
    storage: StorageLayer,
    config: Optional[PipelineConfig] = None,
):
    """
    Return a ProcessorFn that runs the real 8-stage pipeline.

    The returned function matches the ProcessorFn signature expected by JobRunner:
        processor(user_id: str, doc_id: str, checkpoint: dict) -> dict
    """
    if config is None:
        config = PipelineConfig()

    def processor(user_id: str, doc_id: str, checkpoint: dict) -> dict:
        # 1. Locate file
        file_path_str = storage.get_file_path(doc_id)
        if not file_path_str:
            raise ValueError(
                f"No file registered for doc_id={doc_id}. "
                "Did the upload endpoint call storage.save_file_path()?"
            )

        source_path = Path(file_path_str)
        if not source_path.exists():
            raise FileNotFoundError(
                f"Uploaded file missing from disk: {file_path_str}"
            )

        logger.info(
            "processor: starting pipeline doc_id=%s file=%s",
            doc_id,
            source_path.name,
        )

        # 2. Run full pipeline (stages 1-8)
        orch = PipelineOrchestrator(config)
        result = orch.run(source_path)

        # 3. Persist ChunkSet (SQLite) + embed into MongoDB
        chunks_produced = 0
        chunks_embedded = 0
        if orch.last_chunk_set is not None:
            cs_json = _serialize_chunk_set(orch.last_chunk_set)
            storage.save_chunk_set(doc_id, cs_json)
            chunks_produced = len(orch.last_chunk_set.chunks)
            logger.info("processor: saved %d chunks for doc_id=%s", chunks_produced, doc_id)

            # Embed chunks into MongoDB for vector search (non-fatal if MongoDB unavailable)
            if mongo_ping():
                try:
                    vec_storage = VectorStorage()
                    chunks_embedded = embed_chunks_into_mongo(
                        orch.last_chunk_set, doc_id, user_id, vec_storage
                    )
                except Exception as exc:
                    logger.warning("processor: MongoDB embedding failed for doc_id=%s: %s", doc_id, exc)
            else:
                logger.info("processor: MongoDB unavailable — skipping vector embedding for doc_id=%s", doc_id)

        # 4. Persist GraphSubgraph
        graph_nodes = 0
        graph_edges = 0
        if orch.last_graph is not None:
            g_json = _serialize_graph(orch.last_graph)
            storage.save_graph(doc_id, g_json)
            graph_nodes = orch.last_graph.node_count()
            graph_edges = orch.last_graph.edge_count()
            logger.info(
                "processor: saved graph nodes=%d edges=%d for doc_id=%s",
                graph_nodes, graph_edges, doc_id,
            )

        return {
            "stage": "index",
            "doc_id": doc_id,
            "pipeline_document_id": result.document_id,
            "overall_status": result.overall_status,
            "chunks_produced": chunks_produced,
            "chunks_embedded": chunks_embedded,
            "graph_nodes": graph_nodes,
            "graph_edges": graph_edges,
        }

    return processor
