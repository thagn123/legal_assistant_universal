"""
Evidence-grounded reasoning interface.

Takes a user query and an EvidenceBundle assembled from retrieval + graph
traversal, and produces a ReasoningResult that cites only what the evidence
actually contains.

Design rules (from docs/graphrag/ and Phase 8 requirements):
  - Answers are assembled from chunk content ONLY. No invented text.
  - Every material claim in an answer must map to an evidence chunk.
  - Unsupported queries get a clear refusal — no authoritative answer.
  - Partially-supported answers carry an explicit caveat.
  - Source excerpts are distinguishable from generated explanation text.
  - No LLM calls; this module is deterministic.

Support-status → answer behaviour:
  supported           → Direct evidence answer with citations.
  partially_supported → Evidence answer with caveat about low confidence
                        or degraded sources.
  unsupported         → Refusal: explain that no evidence was found.

Usage:
    from src.graphrag.reasoning import ReasoningEngine, ReasoningResult
    from src.graphrag.evidence_bundle import assemble_evidence_bundle

    engine = ReasoningEngine()
    result = engine.reason(query="What does Article 1 say?", bundle=bundle)
    if result.is_refusal:
        print("No answer:", result.answer)
    else:
        print(result.answer)
        for excerpt, citation in zip(result.evidence_excerpts, result.citations):
            print(f"  [{citation}] {excerpt[:120]}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from src.graphrag.evidence_bundle import (
    SUPPORTED,
    PARTIALLY_SUPPORTED,
    UNSUPPORTED,
    EvidenceBundle,
)
from src.graphrag.query_intent import classify_intent
from src.schemas.chunk import Chunk


# ---------------------------------------------------------------------------
# Refusal and caveat templates
# ---------------------------------------------------------------------------

_REFUSAL_NO_EVIDENCE = (
    "No evidence was found in the uploaded documents to answer this query. "
    "Please upload the relevant document or rephrase your question."
)

_REFUSAL_NO_SEEDS = (
    "The query could not be matched to any section of the uploaded documents. "
    "This may mean the requested article or clause does not exist in the current document set."
)

_CAVEAT_LOW_CONFIDENCE = (
    "[Note: The following answer is based on evidence with low confidence or "
    "degraded source quality. Treat with caution and verify against the original document.]"
)

_CAVEAT_PARTIAL = (
    "[Note: Only partial evidence was found. The answer may be incomplete. "
    "Additional documents may be needed.]"
)

# Maximum characters of chunk content to include as an excerpt
_EXCERPT_MAX_CHARS = 800


# ---------------------------------------------------------------------------
# ReasoningResult schema
# ---------------------------------------------------------------------------


@dataclass
class ReasoningResult:
    """
    Output of the reasoning engine for a single query.

    Fields:
        query_id:          Identifier matching the originating EvidenceBundle.
        query:             The raw query string.
        intent:            Classified query intent.
        support_status:    From the EvidenceBundle (supported / partially_supported / unsupported).
        confidence:        Aggregate confidence from the EvidenceBundle.
        answer:            The assembled answer string (may be a refusal).
        evidence_excerpts: Verbatim excerpts from evidence chunks (ordered by chunk rank).
        citations:         Deduplicated citation strings from all evidence chunks.
        is_refusal:        True when the answer is a refusal due to missing evidence.
        warnings:          Reasoning-time warnings (bundle warnings + engine warnings).
    """

    query_id: str
    query: str
    intent: str
    support_status: str
    confidence: float
    answer: str
    evidence_excerpts: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    is_refusal: bool = False
    warnings: List[str] = field(default_factory=list)

    def summary(self) -> str:
        return (
            f"ReasoningResult(intent={self.intent}, status={self.support_status}, "
            f"confidence={self.confidence:.2f}, refusal={self.is_refusal}, "
            f"excerpts={len(self.evidence_excerpts)}, citations={len(self.citations)})"
        )


# ---------------------------------------------------------------------------
# ReasoningEngine
# ---------------------------------------------------------------------------


class ReasoningEngine:
    """
    Evidence-grounded reasoning engine.

    Constructs answers from EvidenceBundle content only. No LLM calls.
    Enforces support-state validation before producing any answer.

    Args:
        authority_threshold: Minimum chunk confidence to treat as authoritative (default 0.65).
        excerpt_max_chars:   Maximum characters per evidence excerpt (default 800).
    """

    def __init__(
        self,
        authority_threshold: float = 0.65,
        excerpt_max_chars: int = _EXCERPT_MAX_CHARS,
    ) -> None:
        self.authority_threshold = authority_threshold
        self.excerpt_max_chars = excerpt_max_chars

    # ── Public API ────────────────────────────────────────────────────────

    def reason(
        self,
        query: str,
        bundle: EvidenceBundle,
        query_id: Optional[str] = None,
    ) -> ReasoningResult:
        """
        Produce a ReasoningResult from a query and its EvidenceBundle.

        Args:
            query:    The user's raw query string.
            bundle:   EvidenceBundle assembled from retrieval + traversal.
            query_id: Optional override for query_id (defaults to bundle.query_id).

        Returns:
            ReasoningResult with answer, citations, and support status.
        """
        qid = query_id or bundle.query_id
        intent = classify_intent(query)
        warnings: List[str] = list(bundle.warnings)

        # ── Unsupported: refusal ─────────────────────────────────────────
        if bundle.support_status == UNSUPPORTED or not bundle.evidence_chunks:
            refusal_text = (
                _REFUSAL_NO_SEEDS
                if "No seed chunks provided" in " ".join(bundle.warnings)
                else _REFUSAL_NO_EVIDENCE
            )
            return ReasoningResult(
                query_id=qid,
                query=query,
                intent=intent,
                support_status=UNSUPPORTED,
                confidence=bundle.confidence,
                answer=refusal_text,
                is_refusal=True,
                warnings=warnings,
            )

        # ── Collect authoritative chunks for answer assembly ─────────────
        authoritative = [
            c for c in bundle.evidence_chunks
            if c.is_authoritative(self.authority_threshold)
        ]
        degraded_only = len(authoritative) == 0

        # ── Build evidence excerpts ──────────────────────────────────────
        # Use authoritative chunks first; fall back to all chunks if none authoritative.
        source_chunks = authoritative if authoritative else bundle.evidence_chunks
        excerpts: List[str] = []
        for chunk in source_chunks:
            excerpt = self._make_excerpt(chunk)
            if excerpt:
                excerpts.append(excerpt)

        # ── Assemble answer ──────────────────────────────────────────────
        if bundle.support_status == SUPPORTED and not degraded_only:
            answer = self._assemble_supported_answer(query, intent, source_chunks, excerpts)
        else:
            # PARTIALLY_SUPPORTED or degraded-only supported
            caveat = _CAVEAT_LOW_CONFIDENCE if degraded_only else _CAVEAT_PARTIAL
            answer = caveat + "\n\n" + self._assemble_supported_answer(
                query, intent, source_chunks, excerpts
            )
            warnings.append(
                "Answer confidence is reduced due to degraded or low-confidence evidence."
                if degraded_only
                else "Answer may be incomplete — only partial evidence was found."
            )

        return ReasoningResult(
            query_id=qid,
            query=query,
            intent=intent,
            support_status=bundle.support_status,
            confidence=bundle.confidence,
            answer=answer,
            evidence_excerpts=excerpts,
            citations=list(bundle.citations),
            is_refusal=False,
            warnings=warnings,
        )

    # ── Private helpers ───────────────────────────────────────────────────

    def _make_excerpt(self, chunk: Chunk) -> str:
        """
        Extract a verbatim excerpt from a chunk.

        Returns the first `excerpt_max_chars` characters of the chunk content,
        trimmed to a sentence boundary where possible.
        """
        content = chunk.content.strip()
        if not content:
            return ""
        if len(content) <= self.excerpt_max_chars:
            return content
        # Try to trim at last sentence boundary within limit
        truncated = content[: self.excerpt_max_chars]
        last_period = max(
            truncated.rfind(". "),
            truncated.rfind(".\n"),
            truncated.rfind("! "),
            truncated.rfind("? "),
        )
        if last_period > self.excerpt_max_chars // 2:
            return truncated[: last_period + 1]
        return truncated + "…"

    def _assemble_supported_answer(
        self,
        query: str,
        intent: str,
        chunks: List[Chunk],
        excerpts: List[str],
    ) -> str:
        """
        Assemble an answer string from evidence excerpts.

        The answer format:
        - Preamble: one sentence naming the source structure path.
        - Body: verbatim excerpts, each labelled with its source path.
        - No invented text beyond the preamble label.
        """
        if not excerpts:
            return "Evidence was found but contained no usable text content."

        lines: List[str] = []

        if len(chunks) == 1:
            path = self._chunk_path_label(chunks[0])
            lines.append(f"Based on {path}:")
            lines.append("")
            lines.append(excerpts[0])
        else:
            lines.append(f"Based on {len(chunks)} evidence source(s):")
            for i, (chunk, excerpt) in enumerate(zip(chunks, excerpts), 1):
                path = self._chunk_path_label(chunk)
                lines.append(f"\n[Source {i}: {path}]")
                lines.append(excerpt)

        return "\n".join(lines)

    def _chunk_path_label(self, chunk: Chunk) -> str:
        """Return a human-readable source label for the chunk."""
        if chunk.hierarchy_path:
            return chunk.hierarchy_path
        if chunk.structure_path:
            return " › ".join(chunk.structure_path)
        return chunk.chunk_id


# ---------------------------------------------------------------------------
# Module-level convenience function
# ---------------------------------------------------------------------------


def reason_over_bundle(
    query: str,
    bundle: EvidenceBundle,
    authority_threshold: float = 0.65,
) -> ReasoningResult:
    """
    Convenience wrapper: construct a ReasoningEngine and call reason().

    Args:
        query:               The user's query string.
        bundle:              The EvidenceBundle from retrieval + traversal.
        authority_threshold: Confidence threshold for authoritative chunks.

    Returns:
        ReasoningResult.
    """
    engine = ReasoningEngine(authority_threshold=authority_threshold)
    return engine.reason(query=query, bundle=bundle)
