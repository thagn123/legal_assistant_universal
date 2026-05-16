"""
Pipeline orchestrator.

Sequences pipeline stages for a single document and collects stage results.
The orchestrator is responsible for:
- building StageContext from config and document path
- running each stage in order via timed_run
- stopping early on fatal failures (but still reporting partial results)
- aggregating stage outputs into a DocumentEvalResult
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional

from src.config import PipelineConfig
from src.pipeline.interfaces import StageContext, StageOutput, timed_run
from src.pipeline.profiler import stage_input_loading, stage_document_profiling
from src.pipeline.extractor import stage_extraction
from src.pipeline.structurer import stage_canonical_structuring
from src.pipeline.cleaner import stage_cleaning_validation
from src.pipeline.chunker import stage_chunking
from src.pipeline.graph_builder import stage_graph_building
from src.pipeline.retrieval_stage import stage_retrieval_smoke_test
from src.schemas.document import CanonicalDocument
from src.schemas.evaluation import (
    ChunkMetrics,
    DocumentEvalResult,
    ExtractionMetrics,
    GraphMetrics,
    MultilingualMetrics,
    RetrievalSmokeResult,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_SKIPPED,
    STATUS_WARNING,
    StageResult,
)
from src.utils import trace as T
from src.utils.logging import get_logger
from src.evaluation.multilingual_metrics import compute_multilingual_metrics


class PipelineOrchestrator:
    """
    Runs all pipeline stages for a single source document.

    Usage:
        orchestrator = PipelineOrchestrator(config)
        result = orchestrator.run(document_path)
    """

    def __init__(self, config: PipelineConfig) -> None:
        self.config = config
        self.document_graphs: List = []  # GraphSubgraph per doc — used for cross-doc ALIAS_OF
        # Artifacts from the most recent run() call — used by the job processor
        self.last_chunk_set = None   # ChunkSet | None
        self.last_graph = None       # GraphSubgraph | None

    def run(self, source_path: Path, trace_id: Optional[str] = None) -> DocumentEvalResult:
        """
        Run the full pipeline for one document.
        Returns a DocumentEvalResult with per-stage results and aggregated metrics.
        """
        if trace_id is None:
            trace_id = T.new_trace_id()

        # We need source_hash before document_id — compute lazily after input loading
        source_hash_placeholder = "pending"
        document_id_placeholder = f"doc_{uuid.uuid4().hex[:16]}"

        logger = get_logger(
            module="orchestrator",
            trace_id=trace_id,
            document_id=document_id_placeholder,
            output_dir=self.config.output_path / "logs",
            level=self.config.log_level,
        )

        ctx = StageContext(
            trace_id=trace_id,
            document_id=document_id_placeholder,
            source_path=source_path,
            config=self.config,
            logger=logger,
        )

        logger.stage_start("pipeline", extra={"source": str(source_path)})

        stage_results: List[StageResult] = []
        fatal_failure = False

        # ----------------------------------------------------------------
        # Stage 1: Input loading
        # ----------------------------------------------------------------
        out = timed_run("input_loading", stage_input_loading, ctx)
        stage_results.append(out.to_stage_result())
        if out.status == STATUS_FAIL:
            fatal_failure = True

        # Refine document_id from source hash after loading
        if not fatal_failure:
            source_hash = ctx.get("source_hash", "")
            document_id = T.new_document_id(source_path.name, source_hash)
            ctx.document_id = document_id
            logger.document_id = document_id
        else:
            document_id = document_id_placeholder

        # ----------------------------------------------------------------
        # Stage 2: Document profiling
        # ----------------------------------------------------------------
        if not fatal_failure:
            out = timed_run("document_profiling", stage_document_profiling, ctx)
            stage_results.append(out.to_stage_result())
            if out.status == STATUS_FAIL:
                fatal_failure = True

        # ----------------------------------------------------------------
        # Stage 3: Extraction
        # ----------------------------------------------------------------
        if not fatal_failure:
            out = timed_run("extraction", stage_extraction, ctx)
            stage_results.append(out.to_stage_result())
            if out.status == STATUS_FAIL:
                fatal_failure = True

        # ----------------------------------------------------------------
        # Stage 4: Canonical structuring
        # ----------------------------------------------------------------
        if not fatal_failure:
            out = timed_run("canonical_structuring", stage_canonical_structuring, ctx)
            stage_results.append(out.to_stage_result())
            if out.status == STATUS_FAIL:
                fatal_failure = True

        # ----------------------------------------------------------------
        # Stage 5: Cleaning and validation
        # ----------------------------------------------------------------
        if not fatal_failure:
            out = timed_run("cleaning_validation", stage_cleaning_validation, ctx)
            stage_results.append(out.to_stage_result())
            # Warnings don't stop the pipeline

        # ----------------------------------------------------------------
        # Stage 6: Chunking
        # ----------------------------------------------------------------
        if not fatal_failure:
            out = timed_run("chunking", stage_chunking, ctx)
            stage_results.append(out.to_stage_result())

        # ----------------------------------------------------------------
        # Stage 7: Graph building
        # ----------------------------------------------------------------
        if not fatal_failure:
            out = timed_run("graph_building", stage_graph_building, ctx)
            stage_results.append(out.to_stage_result())
            # Accumulate graph for cross-document ALIAS_OF enrichment (run_pipeline_eval.py)
            _graph = ctx.get("graph")
            if _graph is not None:
                self.document_graphs.append(_graph)
            # Expose for job processor
            self.last_graph = _graph
            self.last_chunk_set = ctx.get("chunk_set")

        # ----------------------------------------------------------------
        # Stage 8: Retrieval smoke test
        # ----------------------------------------------------------------
        if not fatal_failure:
            out = timed_run("retrieval_smoke_test", stage_retrieval_smoke_test, ctx)
            stage_results.append(out.to_stage_result())

        # ----------------------------------------------------------------
        # Aggregate metrics
        # ----------------------------------------------------------------
        document: Optional[CanonicalDocument] = ctx.get("document")
        extraction_metrics = _build_extraction_metrics(ctx, document)
        chunk_metrics = _build_chunk_metrics(ctx)
        graph_metrics = _build_graph_metrics(ctx)
        retrieval_smoke = _build_retrieval_smoke(ctx, stage_results)
        multilingual_metrics = _build_multilingual_metrics(ctx, document)

        result = DocumentEvalResult(
            document_id=document_id,
            source_filename=source_path.name,
            file_type=ctx.get("file_type", "unknown"),
            extraction_strategy=ctx.get("profile") and ctx.get("profile").extraction_strategy or "",
            stage_results=stage_results,
            extraction_metrics=extraction_metrics,
            chunk_metrics=chunk_metrics,
            graph_metrics=graph_metrics,
            retrieval_smoke=retrieval_smoke,
            multilingual_metrics=multilingual_metrics,
        )
        result.overall_status = result.compute_overall_status()
        result.all_warnings = [
            w for s in stage_results for w in s.warnings
        ]
        result.critical_failures = [
            e for s in stage_results for e in s.errors if s.status == STATUS_FAIL
        ]

        logger.stage_end("pipeline", status=result.overall_status)

        if self.config.log_to_file:
            logger.flush_to_file()

        return result


# ---------------------------------------------------------------------------
# Metric builders
# ---------------------------------------------------------------------------


def _build_extraction_metrics(ctx: StageContext, document: Optional[CanonicalDocument]) -> ExtractionMetrics:
    if document is None:
        return ExtractionMetrics()
    profile = document.profile
    return ExtractionMetrics(
        source_page_count=profile.page_count,
        extracted_page_count=len(document.pages),
        block_count=document.block_count(),
        block_coverage=document.validation.coverage_score,
        degraded_block_count=document.degraded_block_count(),
        low_confidence_block_count=len(document.low_confidence_blocks()),
        table_count=document.table_count(),
        image_count=document.image_count(),
        section_count=len(document.sections),
        article_count=len(document.articles),
        clause_count=len(document.clauses),
        structure_detected=document.has_structure(),
        missing_content_warnings=document.validation.unresolved_issues,
    )


def _build_chunk_metrics(ctx: StageContext) -> ChunkMetrics:
    from src.schemas.chunk import ChunkSet
    chunk_set: Optional[ChunkSet] = ctx.get("chunk_set")
    if chunk_set is None:
        return ChunkMetrics()
    chunks = chunk_set.chunks
    avg_tokens = sum(c.token_estimate for c in chunks) / max(1, len(chunks))
    return ChunkMetrics(
        total_chunks=len(chunks),
        text_chunks=len(chunk_set.text_chunks()),
        table_chunks=len(chunk_set.table_chunks()),
        image_chunks=sum(1 for c in chunks if c.chunk_type == "image"),
        degraded_chunks=chunk_set.degraded_chunks,
        avg_token_estimate=round(avg_tokens, 1),
        strategy_used=chunk_set.strategy_used,
    )


def _build_graph_metrics(ctx: StageContext) -> GraphMetrics:
    from src.schemas.graph import GraphSubgraph
    graph: Optional[GraphSubgraph] = ctx.get("graph")
    if graph is None:
        return GraphMetrics()
    return GraphMetrics(
        total_nodes=graph.node_count(),
        total_edges=graph.edge_count(),
        nodes_by_type=graph.nodes_by_type(),
        edges_by_type=graph.edges_by_type(),
        structural_edges=graph.structural_edge_count(),
        low_confidence_edges=len(graph.low_confidence_edges()),
    )


def _build_retrieval_smoke(
    ctx: StageContext, stage_results: List[StageResult]
) -> Optional[RetrievalSmokeResult]:
    smoke_stage = next(
        (s for s in stage_results if s.stage == "retrieval_smoke_test"), None
    )
    if smoke_stage is None or smoke_stage.status == "skipped":
        return None
    out = smoke_stage.output_summary
    return RetrievalSmokeResult(
        queries_tested=out.get("queries_tested", 0),
        queries_with_results=out.get("queries_with_results", 0),
        avg_result_count=out.get("avg_result_count", 0.0),
        queries_failed=out.get("queries_failed", []),
    )


def _build_multilingual_metrics(
    ctx: StageContext,
    document,
) -> Optional[MultilingualMetrics]:
    """Compute multilingual metrics from all pipeline artifacts."""
    try:
        from src.schemas.chunk import ChunkSet
        from src.schemas.graph import GraphSubgraph

        chunk_set: Optional[ChunkSet] = ctx.get("chunk_set")
        graph: Optional[GraphSubgraph] = ctx.get("graph")
        cross_lang_results = ctx.get("cross_lang_retrieval_results", None)

        return compute_multilingual_metrics(
            document=document,
            chunk_set=chunk_set,
            graph=graph,
            cross_lang_results=cross_lang_results,
        )
    except Exception:
        return None
