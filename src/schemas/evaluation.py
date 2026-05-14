"""
Evaluation report schema.

Defines the machine-readable evaluation report produced by the pipeline runner.
Every stage emits a StageResult. The PipelineEvalReport aggregates them all.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel
except ImportError:
    from src.utils.compat import BaseModel  # type: ignore


# ---------------------------------------------------------------------------
# Stage status values
# ---------------------------------------------------------------------------

STATUS_PASS = "pass"
STATUS_WARNING = "warning"
STATUS_FAIL = "fail"
STATUS_SKIPPED = "skipped"

STAGE_NAMES = [
    "input_loading",
    "document_profiling",
    "extraction",
    "canonical_structuring",
    "cleaning_validation",
    "chunking",
    "graph_building",
    "retrieval_smoke_test",
    "evaluation_report",
]


class StageResult(BaseModel):
    """
    Result for a single pipeline stage.
    status must be: pass | warning | fail | skipped
    """

    stage: str
    status: str = STATUS_PASS
    duration_seconds: float = 0.0

    # Human-readable summary
    summary: str = ""

    # Structured metrics specific to this stage
    metrics: Dict[str, Any] = {}

    # Non-fatal issues
    warnings: List[str] = []

    # Fatal or blocking issues
    errors: List[str] = []

    # Any objects produced by this stage (e.g. block count, chunk count)
    output_summary: Dict[str, Any] = {}

    def is_blocking(self) -> bool:
        return self.status == STATUS_FAIL


class ExtractionMetrics(BaseModel):
    """Metrics for the extraction and structuring stages."""

    source_page_count: int = 0
    extracted_page_count: int = 0
    block_count: int = 0
    block_coverage: float = 0.0         # fraction of pages with ≥1 block
    degraded_block_count: int = 0
    low_confidence_block_count: int = 0
    table_count: int = 0
    image_count: int = 0
    ocr_applied_page_count: int = 0
    avg_ocr_confidence: Optional[float] = None
    min_ocr_confidence: Optional[float] = None
    section_count: int = 0
    article_count: int = 0
    clause_count: int = 0
    structure_detected: bool = False
    missing_content_warnings: List[str] = []
    hallucination_risk_warnings: List[str] = []


class ChunkMetrics(BaseModel):
    """Metrics for the chunking stage."""

    total_chunks: int = 0
    text_chunks: int = 0
    table_chunks: int = 0
    image_chunks: int = 0
    degraded_chunks: int = 0
    avg_token_estimate: float = 0.0
    strategy_used: str = ""
    forbidden_splits_detected: List[str] = []   # splits that violated docs rules


class GraphMetrics(BaseModel):
    """Metrics for the graph building stage."""

    total_nodes: int = 0
    total_edges: int = 0
    nodes_by_type: Dict[str, int] = {}
    edges_by_type: Dict[str, int] = {}
    structural_edges: int = 0
    unresolved_citations: int = 0
    low_confidence_edges: int = 0
    orphan_nodes: int = 0


class MultilingualMetrics(BaseModel):
    """
    Multilingual retrieval quality metrics for one document.

    Tracks how well the pipeline handles cross-language queries.
    """

    primary_language: str = ""                  # "vi" | "en" | "mixed" | "unknown"
    language_confidence: float = 0.0            # 0.0–1.0
    jurisdiction: Optional[str] = None          # "VN" | "US" | "GB" | etc.
    canonical_refs_generated: int = 0           # total canonical IDs on chunks
    chunks_with_canonical_refs: int = 0         # chunks that have ≥1 canonical ref
    chunks_with_language_field: int = 0         # chunks with language field set
    alias_edges_added: int = 0                  # ALIAS_OF edges added to graph
    cross_lang_queries_tested: int = 0          # cross-language smoke queries
    cross_lang_queries_hit: int = 0             # cross-language queries that returned results
    cross_lang_hit_rate: float = 0.0            # = cross_lang_queries_hit / cross_lang_queries_tested


class RetrievalSmokeResult(BaseModel):
    """Results from the retrieval smoke test."""

    queries_tested: int = 0
    queries_with_results: int = 0
    avg_result_count: float = 0.0
    queries_failed: List[str] = []
    multilingual: Optional[MultilingualMetrics] = None   # multilingual metrics


class DocumentEvalResult(BaseModel):
    """
    Full evaluation result for one document processed through the pipeline.
    """

    document_id: str
    source_filename: str
    file_type: str = ""
    extraction_strategy: str = ""
    stage_results: List[StageResult] = []
    extraction_metrics: ExtractionMetrics = ExtractionMetrics()
    chunk_metrics: ChunkMetrics = ChunkMetrics()
    graph_metrics: GraphMetrics = GraphMetrics()
    retrieval_smoke: Optional[RetrievalSmokeResult] = None
    multilingual_metrics: Optional[MultilingualMetrics] = None
    overall_status: str = STATUS_PASS
    critical_failures: List[str] = []
    all_warnings: List[str] = []

    def compute_overall_status(self) -> str:
        """Derive overall status from stage results."""
        if any(s.status == STATUS_FAIL for s in self.stage_results):
            return STATUS_FAIL
        if any(s.status == STATUS_WARNING for s in self.stage_results):
            return STATUS_WARNING
        return STATUS_PASS


class PipelineEvalReport(BaseModel):
    """
    Top-level evaluation report for a full pipeline run.

    Written as both JSON (machine-readable) and Markdown (human-readable).
    """

    run_id: str
    processing_version: str = "0.1.0"
    schema_version: str = "1.0"
    started_at: str = ""
    finished_at: str = ""
    total_duration_seconds: float = 0.0

    config_summary: Dict[str, Any] = {}
    documents_processed: int = 0
    documents_passed: int = 0
    documents_warned: int = 0
    documents_failed: int = 0

    document_results: List[DocumentEvalResult] = []

    # Cross-document summary
    overall_status: str = STATUS_PASS
    critical_failures: List[str] = []
    key_warnings: List[str] = []
    recommendations: List[str] = []

    def compute_overall_status(self) -> str:
        if any(d.overall_status == STATUS_FAIL for d in self.document_results):
            return STATUS_FAIL
        if any(d.overall_status == STATUS_WARNING for d in self.document_results):
            return STATUS_WARNING
        return STATUS_PASS
