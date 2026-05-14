"""
Report generation: JSON and Markdown.

Converts a PipelineEvalReport into human-readable and machine-readable formats.
The JSON report is the authoritative output for CI/CD and benchmarking.
The Markdown report is for human review.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from src.schemas.evaluation import (
    DocumentEvalResult,
    PipelineEvalReport,
    STATUS_FAIL,
    STATUS_PASS,
    STATUS_WARNING,
)


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------


def write_json_report(report: PipelineEvalReport, output_dir: Path) -> Path:
    """Write the full evaluation report as JSON."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"eval_report_{report.run_id[:12]}.json"
    data = _report_to_dict(report)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)
    return path


def _report_to_dict(report: PipelineEvalReport) -> Dict[str, Any]:
    """Convert report to plain dict for JSON serialization."""
    try:
        return report.model_dump()
    except AttributeError:
        # Pydantic v1 fallback
        return report.dict()


# ---------------------------------------------------------------------------
# Markdown report
# ---------------------------------------------------------------------------


STATUS_ICON = {
    STATUS_PASS: "✅",
    STATUS_WARNING: "⚠️",
    STATUS_FAIL: "❌",
    "skipped": "⏭️",
}


def write_markdown_report(report: PipelineEvalReport, output_dir: Path) -> Path:
    """Write a human-readable Markdown report."""
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"eval_report_{report.run_id[:12]}.md"
    md = _build_markdown(report)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(md)
    return path


def _build_markdown(report: PipelineEvalReport) -> str:
    lines: List[str] = []

    overall_icon = STATUS_ICON.get(report.overall_status, "❓")
    lines.append(f"# Legal GraphRAG Pipeline Evaluation Report")
    lines.append(f"")
    lines.append(f"**Run ID:** `{report.run_id}`  ")
    lines.append(f"**Processing Version:** `{report.processing_version}`  ")
    lines.append(f"**Started:** {report.started_at}  ")
    lines.append(f"**Finished:** {report.finished_at}  ")
    lines.append(f"**Duration:** {report.total_duration_seconds:.2f}s  ")
    lines.append(f"**Overall Status:** {overall_icon} `{report.overall_status.upper()}`")
    lines.append(f"")

    # Summary table
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"| --- | --- |")
    lines.append(f"| Documents Processed | {report.documents_processed} |")
    lines.append(f"| Passed | ✅ {report.documents_passed} |")
    lines.append(f"| Warnings | ⚠️ {report.documents_warned} |")
    lines.append(f"| Failed | ❌ {report.documents_failed} |")
    lines.append("")

    if report.critical_failures:
        lines.append("## ❌ Critical Failures")
        lines.append("")
        for f in report.critical_failures:
            lines.append(f"- {f}")
        lines.append("")

    if report.key_warnings:
        lines.append("## ⚠️ Key Warnings")
        lines.append("")
        for w in report.key_warnings:
            lines.append(f"- {w}")
        lines.append("")

    if report.recommendations:
        lines.append("## 💡 Recommendations")
        lines.append("")
        for r in report.recommendations:
            lines.append(f"- {r}")
        lines.append("")

    # Per-document results
    lines.append("---")
    lines.append("")
    for doc_result in report.document_results:
        lines.extend(_document_section(doc_result))

    return "\n".join(lines)


def _document_section(result: DocumentEvalResult) -> List[str]:
    lines: List[str] = []
    icon = STATUS_ICON.get(result.overall_status, "❓")
    lines.append(f"## {icon} Document: `{result.source_filename}`")
    lines.append("")
    lines.append(f"**Document ID:** `{result.document_id}`  ")
    lines.append(f"**File Type:** `{result.file_type}`  ")
    lines.append(f"**Extraction Strategy:** `{result.extraction_strategy}`  ")
    lines.append(f"**Overall Status:** `{result.overall_status.upper()}`")
    lines.append("")

    # Stage results table
    lines.append("### Stage Results")
    lines.append("")
    lines.append("| Stage | Status | Duration | Summary |")
    lines.append("| --- | --- | --- | --- |")
    for s in result.stage_results:
        icon = STATUS_ICON.get(s.status, "❓")
        dur = f"{s.duration_seconds:.2f}s"
        summary = (s.summary or "")[:80]
        lines.append(f"| {s.stage} | {icon} {s.status} | {dur} | {summary} |")
    lines.append("")

    # Extraction metrics
    em = result.extraction_metrics
    if em.block_count > 0:
        lines.append("### Extraction Metrics")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"| --- | --- |")
        lines.append(f"| Pages (source) | {em.source_page_count} |")
        lines.append(f"| Pages (extracted) | {em.extracted_page_count} |")
        lines.append(f"| Blocks | {em.block_count} |")
        lines.append(f"| Coverage Score | {em.block_coverage:.2f} |")
        lines.append(f"| Degraded Blocks | {em.degraded_block_count} |")
        lines.append(f"| Tables | {em.table_count} |")
        lines.append(f"| Images | {em.image_count} |")
        lines.append(f"| Sections | {em.section_count} |")
        lines.append(f"| Articles | {em.article_count} |")
        lines.append(f"| Clauses | {em.clause_count} |")
        lines.append(f"| Structure Detected | {'Yes' if em.structure_detected else 'No'} |")
        lines.append("")

    # Chunk metrics
    cm = result.chunk_metrics
    if cm.total_chunks > 0:
        lines.append("### Chunk Metrics")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"| --- | --- |")
        lines.append(f"| Total Chunks | {cm.total_chunks} |")
        lines.append(f"| Text Chunks | {cm.text_chunks} |")
        lines.append(f"| Table Chunks | {cm.table_chunks} |")
        lines.append(f"| Degraded Chunks | {cm.degraded_chunks} |")
        lines.append(f"| Avg Token Estimate | {cm.avg_token_estimate:.0f} |")
        lines.append(f"| Strategy | {cm.strategy_used} |")
        lines.append("")

    # Graph metrics
    gm = result.graph_metrics
    if gm.total_nodes > 0:
        lines.append("### Graph Metrics")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"| --- | --- |")
        lines.append(f"| Total Nodes | {gm.total_nodes} |")
        lines.append(f"| Total Edges | {gm.total_edges} |")
        lines.append(f"| Structural Edges | {gm.structural_edges} |")
        lines.append(f"| Low Confidence Edges | {gm.low_confidence_edges} |")
        if gm.nodes_by_type:
            lines.append(f"| Nodes by Type | {json.dumps(gm.nodes_by_type)} |")
        lines.append("")

    # Retrieval smoke
    if result.retrieval_smoke:
        rs = result.retrieval_smoke
        lines.append("### Retrieval Smoke Test")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"| --- | --- |")
        lines.append(f"| Queries Tested | {rs.queries_tested} |")
        lines.append(f"| Queries with Results | {rs.queries_with_results} |")
        lines.append(f"| Avg Result Count | {rs.avg_result_count:.1f} |")
        if rs.queries_failed:
            lines.append(f"| Failed Queries | {', '.join(rs.queries_failed[:5])} |")
        lines.append("")

    # Multilingual metrics
    mm = result.multilingual_metrics
    if mm is not None and (mm.primary_language or mm.canonical_refs_generated > 0):
        lines.append("### Multilingual Metrics")
        lines.append("")
        lines.append(f"| Metric | Value |")
        lines.append(f"| --- | --- |")
        lines.append(f"| Primary Language | `{mm.primary_language}` |")
        lines.append(f"| Language Confidence | {mm.language_confidence:.2f} |")
        if mm.jurisdiction:
            lines.append(f"| Jurisdiction | `{mm.jurisdiction}` |")
        lines.append(f"| Canonical Refs Generated | {mm.canonical_refs_generated} |")
        lines.append(f"| Chunks with Canonical Refs | {mm.chunks_with_canonical_refs} |")
        lines.append(f"| Chunks with Language Field | {mm.chunks_with_language_field} |")
        lines.append(f"| ALIAS_OF Edges | {mm.alias_edges_added} |")
        if mm.cross_lang_queries_tested > 0:
            lines.append(f"| Cross-lang Queries Tested | {mm.cross_lang_queries_tested} |")
            lines.append(f"| Cross-lang Hit Rate | {mm.cross_lang_hit_rate:.0%} |")
        lines.append("")

    # Warnings
    if result.all_warnings:
        lines.append("### Warnings")
        lines.append("")
        for w in result.all_warnings[:20]:
            lines.append(f"- ⚠️ {w}")
        if len(result.all_warnings) > 20:
            lines.append(f"- ... and {len(result.all_warnings) - 20} more.")
        lines.append("")

    # Critical failures
    if result.critical_failures:
        lines.append("### Critical Failures")
        lines.append("")
        for f in result.critical_failures:
            lines.append(f"- ❌ {f}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return lines
