"""
Stage 5: Cleaning and validation

Remove obvious garbage, detect missing/duplicate content, flag low-confidence regions.
Rule: emit warnings, never silently fix legally meaningful text.
"""

from __future__ import annotations

import re
from typing import Dict, List

from src.pipeline.interfaces import StageContext, StageOutput
from src.schemas.document import CanonicalDocument, ValidationSummary
from src.schemas.evaluation import STATUS_FAIL, STATUS_PASS, STATUS_WARNING
from src.utils import trace as T


def stage_cleaning_validation(ctx: StageContext) -> StageOutput:
    """
    Remove obvious garbage, detect missing/duplicate content, flag low-confidence regions.
    Rule: emit warnings, never silently fix legally meaningful text.
    """
    document: CanonicalDocument = ctx.get("document")
    if document is None:
        return StageOutput(
            stage_name="cleaning_validation",
            status=STATUS_FAIL,
            summary="No document object in context",
            errors=["canonical_structuring must run before cleaning_validation"],
        )

    cfg = ctx.config
    warnings: List[str] = []
    issues: List[str] = []

    if cfg.parser_noise_cleanup:
        # Detect duplicated blocks
        seen_texts: Dict[str, str] = {}
        for block in document.blocks:
            normalized = re.sub(r"\s+", " ", block.raw_text.strip().lower())
            if normalized in seen_texts and len(normalized) > 40:
                warnings.append(
                    f"Duplicate block detected: block_id={block.block_id} "
                    f"duplicates {seen_texts[normalized]}"
                )
                block.confidence.degraded = True
                block.confidence.reasons.append("duplicate_content")
            else:
                seen_texts[normalized] = block.block_id

    # Flag low-confidence blocks
    low_conf_blocks = document.low_confidence_blocks(cfg.extraction_confidence_threshold)
    if low_conf_blocks:
        warnings.append(
            f"{len(low_conf_blocks)} block(s) below confidence threshold "
            f"({cfg.extraction_confidence_threshold}): "
            f"{[b.block_id for b in low_conf_blocks[:5]]}"
        )

    # Check coverage
    if document.block_count() == 0:
        issues.append("No blocks extracted. Document may be empty, encrypted, or unsupported.")

    # Validate tables are non-empty
    for table in document.tables:
        if table.row_count == 0:
            warnings.append(f"Table {table.table_id} has 0 rows — may be extraction failure.")

    # Update validation summary
    document.validation = ValidationSummary(
        coverage_score=min(1.0, document.block_count() / max(1, document.profile.page_count * 3)),
        unresolved_issues=issues,
        warnings=warnings,
        validated_at=T.now_iso(),
    )

    status = STATUS_FAIL if issues else (STATUS_WARNING if warnings else STATUS_PASS)
    return StageOutput(
        stage_name="cleaning_validation",
        status=status,
        summary=f"{len(warnings)} warnings, {len(issues)} issues. Coverage: {document.validation.coverage_score:.2f}",
        warnings=warnings,
        errors=issues,
        output_summary={
            "coverage_score": round(document.validation.coverage_score, 3),
            "degraded_blocks": document.degraded_block_count(),
            "low_confidence_blocks": len(low_conf_blocks),
        },
    )
