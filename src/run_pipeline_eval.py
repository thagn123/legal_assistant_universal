"""
Legal Multimodal GraphRAG — End-to-End Pipeline Evaluation Runner
=================================================================

Usage:
    python -m src.run_pipeline_eval --input ./samples --output ./reports
    python -m src.run_pipeline_eval --input ./samples --no-graph --log-level DEBUG

This script:
1. Loads configuration from CLI args
2. Discovers all supported documents in the input path
3. Runs each document through the full 8-stage pipeline
4. Collects and validates stage results
5. Generates a JSON evaluation report (machine-readable)
6. Generates a Markdown evaluation report (human-readable)
7. Prints a summary to stdout
8. Exits with code 0 (all pass), 1 (warnings), or 2 (any failure)

Pipeline stages:
  1. input_loading          — validate file, detect type, compute source hash
  2. document_profiling     — determine extraction strategy
  3. extraction             — local-first text/table/image extraction
  4. canonical_structuring  — build CanonicalDocument with provenance
  5. cleaning_validation    — remove garbage, flag low-confidence content
  6. chunking               — structure-aware chunk generation
  7. graph_building         — create GraphSubgraph (optional)
  8. retrieval_smoke_test   — basic keyword retrieval validation (optional)

Design rules (from docs):
  - Local-first extraction by default; AI repair only if --enable-ai-repair
  - Tables and images are first-class objects, never flattened
  - Hierarchy preserved; missing text remains missing (no filler)
  - Every output carries provenance and confidence
  - Deterministic where possible; structured logs always
"""

from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path
from typing import List, Optional

from src.cli import parse_config
from src.config import PipelineConfig
from src.evaluation.checks import (
    check_blocks_present,
    check_chunks_present,
    check_coverage,
    check_degraded_chunk_rate,
    check_graph_has_nodes,
    check_low_confidence_rate,
    check_no_empty_chunks,
    check_no_invented_text,
    check_structural_edges_present,
    check_tables_intact,
    hallucination_risk_warnings,
)
from src.evaluation.metrics import (
    compute_chunk_quality_summary,
    compute_extraction_completeness,
    compute_graph_summary,
    compute_missing_content_warnings,
    compute_ocr_confidence_summary,
    compute_structure_preservation,
    compute_table_preservation,
)
from src.evaluation.reports import write_json_report, write_markdown_report
from src.pipeline.orchestrator import PipelineOrchestrator
from src.schemas.evaluation import (
    DocumentEvalResult,
    PipelineEvalReport,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_WARNING,
)
from src.utils import trace as T

# Supported file extensions
# .doc requires docx2txt or antiword to be installed (see requirements.txt)
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".doc",        # legacy Word — needs docx2txt or antiword
    ".html", ".htm",
    ".png", ".jpg", ".jpeg", ".tiff", ".tif", ".bmp", ".webp",
}


# ---------------------------------------------------------------------------
# Document discovery
# ---------------------------------------------------------------------------


def discover_documents(input_path: Path) -> List[Path]:
    """
    Find all supported documents in the input path.
    Accepts a single file or a directory.
    """
    if input_path.is_file():
        if input_path.suffix.lower() in SUPPORTED_EXTENSIONS:
            return [input_path]
        print(f"[WARNING] File '{input_path}' has unsupported extension. Will attempt anyway.")
        return [input_path]

    if input_path.is_dir():
        docs = []
        for ext in SUPPORTED_EXTENSIONS:
            docs.extend(input_path.rglob(f"*{ext}"))
            docs.extend(input_path.rglob(f"*{ext.upper()}"))
        docs = sorted(set(docs))
        return docs

    return []


# ---------------------------------------------------------------------------
# Post-processing: run checks and enrich the DocumentEvalResult
# ---------------------------------------------------------------------------


def run_evaluation_checks(
    result: DocumentEvalResult,
    orchestrator: PipelineOrchestrator,
) -> DocumentEvalResult:
    """
    Run all evaluation checks on the pipeline output and record results.
    Checks implement the benchmark rules from docs/validation/parser-benchmark.md.
    """
    # We need to reconstruct artifacts from stage outputs for checking
    # (in a fuller system the orchestrator would expose them; here we derive from metrics)
    em = result.extraction_metrics
    cm = result.chunk_metrics
    gm = result.graph_metrics

    all_warnings = list(result.all_warnings)
    all_failures = list(result.critical_failures)

    # Extraction checks
    if em.block_count == 0:
        all_failures.append("No blocks extracted — document may be empty or unsupported.")
    if em.block_coverage < 0.3 and em.source_page_count > 0:
        all_warnings.append(f"Low coverage score: {em.block_coverage:.2f}")
    if em.table_count == 0 and em.source_page_count > 0 and result.extraction_strategy in ("hybrid_region_precision",):
        all_warnings.append("Document expected tables but none were extracted.")

    # Chunk checks
    if cm.total_chunks == 0 and em.block_count > 0:
        all_failures.append("No chunks produced despite extracted content.")
    if cm.total_chunks > 0:
        rate = cm.degraded_chunks / cm.total_chunks
        if rate > 0.5:
            all_warnings.append(f"High degraded chunk rate: {rate:.0%}")

    # Graph checks
    if gm.total_nodes == 0 and result.graph_metrics is not None:
        all_warnings.append("Graph was not built or produced no nodes.")
    if gm.structural_edges == 0 and gm.total_nodes > 1:
        all_warnings.append("Graph has nodes but no structural edges — hierarchy may be lost.")

    # Hallucination risk
    # We can't access the full document object here easily without passing it through,
    # so we use metric signals as proxies.
    if em.low_confidence_block_count > em.block_count * 0.4:
        all_warnings.append(
            f"High proportion of low-confidence blocks ({em.low_confidence_block_count}/{em.block_count}). "
            "Answers citing these should be flagged as partially supported."
        )

    result.all_warnings = all_warnings
    result.critical_failures = all_failures
    result.overall_status = result.compute_overall_status()
    return result


# ---------------------------------------------------------------------------
# Main pipeline runner
# ---------------------------------------------------------------------------


def run_pipeline(config: PipelineConfig) -> PipelineEvalReport:
    """
    Full pipeline evaluation run.
    Returns a PipelineEvalReport with all document results.
    """
    run_id = str(uuid.uuid4())
    started_at = T.now_iso()
    t_start = time.perf_counter()

    config.ensure_output_dir()

    print(f"\n{'='*60}")
    print(f"  Legal GraphRAG Pipeline Evaluator")
    print(f"  Run ID   : {run_id[:12]}...")
    print(f"  Input    : {config.input_path}")
    print(f"  Output   : {config.output_path}")
    print(f"  OCR      : {'enabled' if config.enable_ocr else 'disabled'}")
    print(f"  Graph    : {'enabled' if config.enable_graph_building else 'disabled'}")
    print(f"  AI Repair: {'enabled' if config.enable_ai_repair else 'disabled'}")
    print(f"{'='*60}\n")

    # Discover documents
    docs = discover_documents(config.input_path)
    if not docs:
        print(f"[ERROR] No supported documents found in: {config.input_path}")
        print(f"  Supported extensions: {sorted(SUPPORTED_EXTENSIONS)}")
        print(f"  Hint: Drop your PDFs, DOCX, HTML, or image files into: {config.input_path}")
        # Return empty report
        return PipelineEvalReport(
            run_id=run_id,
            processing_version=config.processing_version,
            started_at=started_at,
            finished_at=T.now_iso(),
            total_duration_seconds=time.perf_counter() - t_start,
            config_summary=_config_summary(config),
            documents_processed=0,
            overall_status=STATUS_WARNING,
            key_warnings=[f"No documents found in {config.input_path}"],
            recommendations=[
                "Add sample documents to the input directory.",
                f"Supported formats: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
            ],
        )

    print(f"Found {len(docs)} document(s) to process:\n")
    for i, doc in enumerate(docs, 1):
        print(f"  [{i}] {doc.name}")
    print()

    orchestrator = PipelineOrchestrator(config)
    doc_results: List[DocumentEvalResult] = []

    for i, doc_path in enumerate(docs, 1):
        print(f"[{i}/{len(docs)}] Processing: {doc_path.name}")
        result = orchestrator.run(doc_path)
        result = run_evaluation_checks(result, orchestrator)
        doc_results.append(result)

        icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(result.overall_status, "?")
        print(f"  {icon} {result.overall_status.upper()} — "
              f"{result.extraction_metrics.block_count} blocks, "
              f"{result.chunk_metrics.total_chunks} chunks, "
              f"{result.graph_metrics.total_nodes} graph nodes")
        if result.critical_failures:
            for f in result.critical_failures[:3]:
                print(f"  ❌ {f}")
        if result.all_warnings:
            for w in result.all_warnings[:2]:
                print(f"  ⚠️ {w}")
        print()

    # Aggregate
    passed = sum(1 for d in doc_results if d.overall_status == STATUS_PASS)
    warned = sum(1 for d in doc_results if d.overall_status == STATUS_WARNING)
    failed = sum(1 for d in doc_results if d.overall_status == STATUS_FAIL)

    all_failures = [f for d in doc_results for f in d.critical_failures]
    all_warnings = list({w for d in doc_results for w in d.all_warnings})[:20]

    recommendations = _build_recommendations(doc_results)

    report = PipelineEvalReport(
        run_id=run_id,
        processing_version=config.processing_version,
        schema_version=config.schema_version,
        started_at=started_at,
        finished_at=T.now_iso(),
        total_duration_seconds=time.perf_counter() - t_start,
        config_summary=_config_summary(config),
        documents_processed=len(docs),
        documents_passed=passed,
        documents_warned=warned,
        documents_failed=failed,
        document_results=doc_results,
        critical_failures=all_failures,
        key_warnings=all_warnings,
        recommendations=recommendations,
    )
    report.overall_status = report.compute_overall_status()

    return report


def _config_summary(config: PipelineConfig) -> dict:
    return {
        "input_path": str(config.input_path),
        "output_path": str(config.output_path),
        "enable_ocr": config.enable_ocr,
        "enable_ai_repair": config.enable_ai_repair,
        "enable_graph_building": config.enable_graph_building,
        "enable_retrieval_smoke_test": config.enable_retrieval_smoke_test,
        "strict_accuracy_mode": config.strict_accuracy_mode,
        "processing_version": config.processing_version,
    }


def _build_recommendations(doc_results: List[DocumentEvalResult]) -> List[str]:
    recs = []
    total_blocks = sum(d.extraction_metrics.block_count for d in doc_results)
    total_degraded = sum(d.extraction_metrics.degraded_block_count for d in doc_results)
    total_chunks = sum(d.chunk_metrics.total_chunks for d in doc_results)
    total_degraded_chunks = sum(d.chunk_metrics.degraded_chunks for d in doc_results)

    if total_blocks == 0:
        recs.append("Install extraction libraries: pip install pdfminer.six python-docx beautifulsoup4")
        recs.append("For OCR support: pip install pytesseract Pillow")
    else:
        if total_degraded > total_blocks * 0.3:
            recs.append("High degraded block rate. Consider enabling AI repair with --enable-ai-repair.")
        if total_chunks == 0:
            recs.append("No chunks produced. Check extraction output and document structure.")
        if total_degraded_chunks > total_chunks * 0.5:
            recs.append("High degraded chunk rate. Extraction quality needs improvement.")

    has_failed = any(d.overall_status == STATUS_FAIL for d in doc_results)
    if has_failed:
        recs.append("Some documents failed. Check logs in the output/logs/ directory.")

    return recs


# ---------------------------------------------------------------------------
# Report writing and exit
# ---------------------------------------------------------------------------


def write_reports(report: PipelineEvalReport, config: PipelineConfig) -> None:
    json_path = write_json_report(report, config.output_path)
    md_path = write_markdown_report(report, config.output_path)
    print(f"\n{'='*60}")
    print(f"  Evaluation Reports")
    print(f"{'='*60}")
    print(f"  JSON: {json_path}")
    print(f"  MD  : {md_path}")
    print(f"{'='*60}\n")


def print_final_summary(report: PipelineEvalReport) -> None:
    icon = {"pass": "✅", "warning": "⚠️", "fail": "❌"}.get(report.overall_status, "?")
    print(f"\n{icon} OVERALL: {report.overall_status.upper()}")
    print(f"  Processed : {report.documents_processed} documents")
    print(f"  Passed    : {report.documents_passed}")
    print(f"  Warnings  : {report.documents_warned}")
    print(f"  Failed    : {report.documents_failed}")
    print(f"  Duration  : {report.total_duration_seconds:.2f}s")
    if report.recommendations:
        print(f"\n  Recommendations:")
        for r in report.recommendations:
            print(f"    → {r}")
    print()


def exit_code(report: PipelineEvalReport) -> int:
    """Return exit code: 0=pass, 1=warnings, 2=failures."""
    if report.overall_status == STATUS_FAIL:
        return 2
    if report.overall_status == STATUS_WARNING:
        return 1
    return 0


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    config = parse_config()
    report = run_pipeline(config)
    write_reports(report, config)
    print_final_summary(report)
    sys.exit(exit_code(report))


if __name__ == "__main__":
    main()
