"""
Stage 5: Cleaning and validation

Remove obvious garbage, detect missing/duplicate content, flag low-confidence regions.
Rule: raw_text is never mutated (forensic record). clean_text is the retrieval-ready version.
Blocks marked noise_excluded are skipped by the chunker's body-text assembly.
"""

from __future__ import annotations

import re
from typing import Dict, List

from src.pipeline.interfaces import StageContext, StageOutput
from src.schemas.document import Block, CanonicalDocument, ValidationSummary
from src.schemas.evaluation import STATUS_FAIL, STATUS_PASS, STATUS_WARNING
from src.utils import trace as T


# ---------------------------------------------------------------------------
# Noise detection patterns
# ---------------------------------------------------------------------------

# Standalone page numbers: "5", "- 5 -", "– 12 –", "Page 5", "Page 5 of 20", "Trang 5"
_RE_PAGE_NUMBER = re.compile(
    r"^[\-–—\s]*\d{1,4}[\-–—\s]*$"
    r"|^[Pp]age\s+\d+(\s+of\s+\d+)?$"
    r"|^[Tt]rang\s+\d+(\s*/\s*\d+)?$",
    re.UNICODE,
)

# Control characters that are never legitimate in legal text
_RE_CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Lines shorter than this character count are candidates for header/footer dedup
_REPEAT_MAX_LEN = 120
# A short line seen this many times across the document is treated as a header/footer
_REPEAT_THRESHOLD = 3


# ---------------------------------------------------------------------------
# Stage entry point
# ---------------------------------------------------------------------------


def stage_cleaning_validation(ctx: StageContext) -> StageOutput:
    """
    Remove obvious garbage, detect missing/duplicate content, flag low-confidence regions.
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
    noise_count = 0

    if cfg.parser_noise_cleanup:
        # -- Pass 1: count frequency of short lines to detect repeated headers/footers --
        freq: Dict[str, int] = {}
        for block in document.blocks:
            norm = _normalize(block.raw_text)
            if len(norm) <= _REPEAT_MAX_LEN:
                freq[norm] = freq.get(norm, 0) + 1

        # -- Pass 2: mark noise and duplicates --
        seen_texts: Dict[str, str] = {}
        for block in document.blocks:
            raw = block.raw_text.strip()
            norm = _normalize(raw)

            # Strip control characters from clean_text (safe — these are never legal content)
            if _RE_CONTROL_CHARS.search(raw):
                cleaned = _RE_CONTROL_CHARS.sub("", block.clean_text or raw).strip()
                block.clean_text = re.sub(r"\s+", " ", cleaned)

            # Page number detection
            if _RE_PAGE_NUMBER.match(raw):
                _mark_noise(block, "noise_page_number")
                noise_count += 1
                continue

            # Repeated short line → header/footer artifact
            if len(norm) <= _REPEAT_MAX_LEN and freq.get(norm, 0) >= _REPEAT_THRESHOLD:
                _mark_noise(block, "noise_repeated_line")
                noise_count += 1
                continue

            # Duplicate content block (same text appeared earlier)
            if norm in seen_texts and len(norm) > 40:
                warnings.append(
                    f"Duplicate block: block_id={block.block_id} "
                    f"duplicates {seen_texts[norm]}"
                )
                block.confidence.degraded = True
                block.confidence.reasons.append("duplicate_content")
            else:
                seen_texts[norm] = block.block_id

    if noise_count:
        warnings.append(f"{noise_count} noise block(s) excluded (page numbers / repeated headers).")

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
        summary=(
            f"{len(warnings)} warnings, {len(issues)} issues, "
            f"{noise_count} noise blocks removed. "
            f"Coverage: {document.validation.coverage_score:.2f}"
        ),
        warnings=warnings,
        errors=issues,
        output_summary={
            "coverage_score": round(document.validation.coverage_score, 3),
            "degraded_blocks": document.degraded_block_count(),
            "low_confidence_blocks": len(low_conf_blocks),
            "noise_blocks_excluded": noise_count,
        },
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _mark_noise(block: Block, reason: str) -> None:
    """Mark a block as noise: degraded + reason. raw_text is never touched."""
    block.confidence.degraded = True
    if reason not in block.confidence.reasons:
        block.confidence.reasons.append(reason)
    if "noise_excluded" not in block.confidence.reasons:
        block.confidence.reasons.append("noise_excluded")
