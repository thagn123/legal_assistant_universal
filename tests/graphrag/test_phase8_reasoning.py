"""
Phase 8 validation: Evidence-Grounded Reasoning Interface.

Tests the four fixture scenarios required by the Phase 8 pass criteria:
  1. Direct clause lookup     → supported, non-refusal, citations present
  2. Missing clause query     → unsupported, refusal, no citations
  3. Conflicting evidence     → partially_supported, caveat in answer, no refusal
  4. Low-confidence OCR       → partially_supported, caveat in answer, no refusal

Pass criteria (from docs/07-implementation/development-pipeline.md):
  - Unsupported questions do not produce authoritative answers.
  - Every material claim maps to evidence.
  - Source quotes are distinguishable from generated explanation text.

All tests are deterministic — no LLM calls.
"""

from __future__ import annotations

import pytest

from src.graphrag.evidence_bundle import (
    SUPPORTED,
    PARTIALLY_SUPPORTED,
    UNSUPPORTED,
    EvidenceBundle,
    empty_bundle,
)
from src.graphrag.query_intent import (
    classify_intent,
    INTENT_LOOKUP,
    INTENT_EXPLANATION,
    INTENT_COMPARISON,
    INTENT_COMPLIANCE,
    INTENT_UNKNOWN,
)
from src.graphrag.reasoning import ReasoningEngine, reason_over_bundle
from src.schemas.chunk import Chunk


# ---------------------------------------------------------------------------
# Chunk fixtures
# ---------------------------------------------------------------------------


def _chunk(
    chunk_id: str,
    content: str,
    confidence: float = 0.95,
    degraded: bool = False,
    citations: list[str] | None = None,
    canonical_refs: list[str] | None = None,
    structure_path: list[str] | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="doc_test",
        chunk_type="text",
        content=content,
        confidence=confidence,
        degraded=degraded,
        degraded_reasons=["low_ocr_confidence"] if degraded else [],
        citations=citations or [],
        canonical_refs=canonical_refs or [],
        structure_path=structure_path or ["Article 1"],
        hierarchy_path=" › ".join(structure_path) if structure_path else "Article 1",
    )


def _bundle(
    query_id: str,
    support_status: str,
    confidence: float,
    chunks: list[Chunk],
    warnings: list[str] | None = None,
) -> EvidenceBundle:
    citations: list[str] = []
    seen: set[str] = set()
    for c in chunks:
        for cit in c.citations:
            if cit and cit not in seen:
                citations.append(cit)
                seen.add(cit)
    return EvidenceBundle(
        query_id=query_id,
        seed_chunk_ids=[c.chunk_id for c in chunks],
        expanded_node_ids=[],
        evidence_chunks=chunks,
        support_status=support_status,
        confidence=confidence,
        citations=citations,
        warnings=warnings or [],
    )


# ---------------------------------------------------------------------------
# Fixture 1: Direct clause lookup — supported
# ---------------------------------------------------------------------------


class TestDirectClauseLookup:
    """Query matches an existing, high-confidence chunk."""

    def setup_method(self):
        self.chunk = _chunk(
            "chunk_art1",
            content=(
                "Article 1. Scope of Application\n\n"
                "This Law applies to all employment contracts signed after 1 January 2021, "
                "including part-time, fixed-term, and indefinite-term contracts."
            ),
            confidence=0.95,
            citations=["Labor Code 2019, Article 13"],
            structure_path=["Chapter I", "Article 1"],
        )
        self.bundle = _bundle("q_lookup", SUPPORTED, 0.95, [self.chunk])
        self.engine = ReasoningEngine()

    def test_is_not_refusal(self):
        result = self.engine.reason("What does Article 1 say?", self.bundle)
        assert not result.is_refusal

    def test_support_status_is_supported(self):
        result = self.engine.reason("What does Article 1 say?", self.bundle)
        assert result.support_status == SUPPORTED

    def test_answer_contains_chunk_content(self):
        result = self.engine.reason("What does Article 1 say?", self.bundle)
        # Answer must include verbatim content, not invented text
        assert "employment contracts" in result.answer

    def test_citations_present(self):
        result = self.engine.reason("What does Article 1 say?", self.bundle)
        assert len(result.citations) > 0
        assert "Labor Code 2019, Article 13" in result.citations

    def test_evidence_excerpts_present(self):
        result = self.engine.reason("What does Article 1 say?", self.bundle)
        assert len(result.evidence_excerpts) > 0

    def test_intent_classified_as_lookup(self):
        result = self.engine.reason("What does Article 1 say?", self.bundle)
        assert result.intent == INTENT_LOOKUP

    def test_no_caveat_in_supported_answer(self):
        result = self.engine.reason("What does Article 1 say?", self.bundle)
        assert "[Note:" not in result.answer


# ---------------------------------------------------------------------------
# Fixture 2: Missing clause query — unsupported
# ---------------------------------------------------------------------------


class TestMissingClauseQuery:
    """Query has no matching evidence — bundle is empty/unsupported."""

    def setup_method(self):
        self.bundle = empty_bundle("q_missing", "No seed chunks provided — query has no retrieval basis.")
        self.engine = ReasoningEngine()

    def test_is_refusal(self):
        result = self.engine.reason("What does Article 99 say about export duties?", self.bundle)
        assert result.is_refusal

    def test_support_status_is_unsupported(self):
        result = self.engine.reason("What does Article 99 say?", self.bundle)
        assert result.support_status == UNSUPPORTED

    def test_answer_is_non_authoritative(self):
        result = self.engine.reason("What does Article 99 say?", self.bundle)
        # Must not assert anything as a legal fact
        assert result.answer  # refusal message exists
        authoritative_phrases = [
            "Article 99 states",
            "Article 99 requires",
            "According to Article 99",
            "The law provides that",
        ]
        for phrase in authoritative_phrases:
            assert phrase not in result.answer, f"Found authoritative phrase: {phrase!r}"

    def test_no_citations(self):
        result = self.engine.reason("What does Article 99 say?", self.bundle)
        assert result.citations == []

    def test_no_evidence_excerpts(self):
        result = self.engine.reason("What does Article 99 say?", self.bundle)
        assert result.evidence_excerpts == []

    def test_confidence_is_zero(self):
        result = self.engine.reason("What does Article 99 say?", self.bundle)
        assert result.confidence == 0.0


# ---------------------------------------------------------------------------
# Fixture 3: Conflicting evidence — partially_supported
# ---------------------------------------------------------------------------


class TestConflictingEvidence:
    """Bundle has evidence but some chunks are degraded, triggering partial support."""

    def setup_method(self):
        self.good_chunk = _chunk(
            "chunk_art5_good",
            content="Article 5. Payment. Payment shall be made within 30 days of invoice.",
            confidence=0.90,
            citations=["Contract v1.0, Article 5"],
            structure_path=["Article 5"],
        )
        self.degraded_chunk = _chunk(
            "chunk_art5_degraded",
            content="Article 5. Payment. Payment shall be made within 60 days of invoice.",
            confidence=0.55,
            degraded=True,
            citations=["Contract v2.0, Article 5"],
            structure_path=["Article 5"],
        )
        # PARTIALLY_SUPPORTED: majority degraded or below threshold
        self.bundle = _bundle(
            "q_conflict",
            PARTIALLY_SUPPORTED,
            0.72,
            [self.good_chunk, self.degraded_chunk],
        )
        self.engine = ReasoningEngine()

    def test_is_not_refusal(self):
        result = self.engine.reason("What are the payment terms in Article 5?", self.bundle)
        assert not result.is_refusal

    def test_support_status_is_partial(self):
        result = self.engine.reason("What are the payment terms in Article 5?", self.bundle)
        assert result.support_status == PARTIALLY_SUPPORTED

    def test_answer_contains_caveat(self):
        result = self.engine.reason("What are the payment terms in Article 5?", self.bundle)
        assert "[Note:" in result.answer

    def test_answer_contains_evidence_content(self):
        result = self.engine.reason("What are the payment terms in Article 5?", self.bundle)
        assert "Payment" in result.answer or "30 days" in result.answer

    def test_evidence_excerpts_from_authoritative_chunks(self):
        result = self.engine.reason("What are the payment terms in Article 5?", self.bundle)
        # Good chunk is authoritative, degraded is not — excerpts should be from good chunk
        assert any("30 days" in ex for ex in result.evidence_excerpts)

    def test_warnings_present(self):
        result = self.engine.reason("What are the payment terms in Article 5?", self.bundle)
        assert len(result.warnings) > 0

    def test_intent_classified_as_lookup(self):
        result = self.engine.reason("What are the payment terms in Article 5?", self.bundle)
        assert result.intent == INTENT_LOOKUP


# ---------------------------------------------------------------------------
# Fixture 4: Low-confidence OCR — partially_supported
# ---------------------------------------------------------------------------


class TestLowConfidenceOCR:
    """All chunks are degraded (low-quality OCR scan), triggering partial support."""

    def setup_method(self):
        self.ocr_chunk = _chunk(
            "chunk_ocr",
            content="Art1cle 3. L1ability. The party sha1l be 1iable for... [OCR artifact]",
            confidence=0.40,
            degraded=True,
            citations=[],
            structure_path=["Article 3"],
        )
        # Bundle is PARTIALLY_SUPPORTED because evidence exists but all degraded
        self.bundle = _bundle(
            "q_ocr",
            PARTIALLY_SUPPORTED,
            0.40,
            [self.ocr_chunk],
            warnings=["All evidence chunks are below authority threshold or degraded."],
        )
        self.engine = ReasoningEngine()

    def test_is_not_refusal(self):
        result = self.engine.reason("What does Article 3 say about liability?", self.bundle)
        assert not result.is_refusal

    def test_support_status_is_partial(self):
        result = self.engine.reason("What does Article 3 say?", self.bundle)
        assert result.support_status == PARTIALLY_SUPPORTED

    def test_answer_contains_low_confidence_caveat(self):
        result = self.engine.reason("What does Article 3 say?", self.bundle)
        assert "[Note:" in result.answer
        assert "low confidence" in result.answer.lower() or "degraded" in result.answer.lower()

    def test_source_quote_distinguishable(self):
        # The verbatim OCR text should appear in evidence_excerpts, not faked in answer
        result = self.engine.reason("What does Article 3 say?", self.bundle)
        # OCR artifact text appears in excerpts (verbatim), not made up
        assert len(result.evidence_excerpts) > 0
        assert "Art1cle" in result.evidence_excerpts[0] or "1iable" in result.evidence_excerpts[0]

    def test_confidence_low(self):
        result = self.engine.reason("What does Article 3 say?", self.bundle)
        assert result.confidence < 0.65


# ---------------------------------------------------------------------------
# Query intent classification tests
# ---------------------------------------------------------------------------


class TestQueryIntentClassification:

    def test_lookup_article_number(self):
        assert classify_intent("What does Article 5 say?") == INTENT_LOOKUP

    def test_lookup_clause(self):
        assert classify_intent("What is in clause 3?") == INTENT_LOOKUP

    def test_lookup_vietnamese(self):
        assert classify_intent("Điều 10 quy định gì?") == INTENT_LOOKUP

    def test_explanation_mean(self):
        assert classify_intent("What does 'force majeure' mean?") == INTENT_EXPLANATION

    def test_explanation_explain(self):
        assert classify_intent("Explain the termination clause.") == INTENT_EXPLANATION

    def test_comparison(self):
        assert classify_intent("Compare Article 5 and Article 6.") == INTENT_COMPARISON

    def test_comparison_vietnamese(self):
        assert classify_intent("So sánh khoản 1 và khoản 2.") == INTENT_COMPARISON

    def test_compliance(self):
        assert classify_intent("Is it allowed to terminate without notice?") == INTENT_COMPLIANCE

    def test_compliance_vietnamese(self):
        assert classify_intent("Có được phép hủy hợp đồng không?") == INTENT_COMPLIANCE

    def test_compliance_takes_priority_over_lookup(self):
        # "comply" + "Article 3" → compliance wins (higher priority)
        assert classify_intent("Does Article 3 comply with labor law?") == INTENT_COMPLIANCE

    def test_unknown_fallback(self):
        assert classify_intent("hello world") == INTENT_UNKNOWN

    def test_empty_query(self):
        assert classify_intent("") == INTENT_UNKNOWN


# ---------------------------------------------------------------------------
# ReasoningEngine edge cases
# ---------------------------------------------------------------------------


class TestReasoningEdgeCases:

    def test_empty_bundle_is_refusal(self):
        bundle = empty_bundle("q_empty", "No evidence.")
        engine = ReasoningEngine()
        result = engine.reason("What does the contract say?", bundle)
        assert result.is_refusal
        assert result.support_status == UNSUPPORTED

    def test_query_id_override(self):
        bundle = empty_bundle("bundle_id", "No evidence.")
        engine = ReasoningEngine()
        result = engine.reason("query", bundle, query_id="custom_id")
        assert result.query_id == "custom_id"

    def test_supported_bundle_no_caveat(self):
        chunk = _chunk("c1", "The sky is blue per Article 1.", confidence=0.95)
        bundle = _bundle("q1", SUPPORTED, 0.95, [chunk])
        engine = ReasoningEngine()
        result = engine.reason("What does Article 1 say?", bundle)
        assert not result.is_refusal
        assert "[Note:" not in result.answer

    def test_excerpt_truncation(self):
        long_content = "A" * 2000
        chunk = _chunk("c_long", long_content, confidence=0.95)
        bundle = _bundle("q_long", SUPPORTED, 0.95, [chunk])
        engine = ReasoningEngine(excerpt_max_chars=800)
        result = engine.reason("What does it say?", bundle)
        # excerpt should be capped
        assert all(len(ex) <= 810 for ex in result.evidence_excerpts)

    def test_reason_over_bundle_convenience(self):
        chunk = _chunk("c2", "Article 2 content here.", confidence=0.90)
        bundle = _bundle("q2", SUPPORTED, 0.90, [chunk])
        result = reason_over_bundle("What does Article 2 say?", bundle)
        assert not result.is_refusal
        assert "Article 2 content here" in result.answer
