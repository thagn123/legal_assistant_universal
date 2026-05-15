"""
Phase 9 validation: Action Engine.

Tests the three scenarios from the Phase 9 pass criteria:
  1. Draft an employment contract clause from uploaded labor law
  2. Check a policy against uploaded regulation
  3. Detect risky or missing clauses in a sample contract

Plus: safety rule enforcement, schema validation, and cross-document comparison.

Pass criteria (from docs/07-implementation/development-pipeline.md):
  - Drafts cite source basis and assumptions.
  - Risk findings cite exact source evidence.
  - Compliance checks expose missing evidence.

Plus action-engine.md safety rules:
  - Generated content is marked [GENERATED].
  - Source quotations are marked [SOURCE].
  - No compliance claim without both sides of evidence.
  - Insufficient evidence → STATUS_INSUFFICIENT_EVIDENCE (not refused).

All tests are deterministic — no LLM calls.
"""

from __future__ import annotations

import pytest

from src.actions.action_engine import ActionEngine
from src.actions.action_schema import (
    ACTION_COMPLIANCE,
    ACTION_COMPARE,
    ACTION_DRAFT,
    ACTION_RECOMMEND,
    ACTION_RISK,
    ACTION_SUMMARIZE,
    ActionRequest,
    STATUS_COMPLETE,
    STATUS_INSUFFICIENT_EVIDENCE,
    STATUS_PARTIAL,
    STATUS_REFUSED,
)
from src.graphrag.evidence_bundle import (
    SUPPORTED,
    PARTIALLY_SUPPORTED,
    UNSUPPORTED,
    EvidenceBundle,
    empty_bundle,
)
from src.schemas.chunk import Chunk


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


def _chunk(
    chunk_id: str,
    content: str,
    confidence: float = 0.92,
    degraded: bool = False,
    citations: list[str] | None = None,
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="doc_test",
        chunk_type="text",
        content=content,
        confidence=confidence,
        degraded=degraded,
        degraded_reasons=["low_ocr"] if degraded else [],
        citations=citations or [],
        structure_path=["Article 1"],
        hierarchy_path="Article 1",
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
# Fixture 1: Draft employment clause from uploaded labor law
# ---------------------------------------------------------------------------


class TestDraftingWorkflow:

    def setup_method(self):
        self.labor_chunk = _chunk(
            "chunk_labor_art5",
            content=(
                "Article 5. Working Hours.\n"
                "Normal working hours shall not exceed 8 hours per day and 48 hours per week. "
                "Overtime shall be compensated at 150% of the regular hourly rate."
            ),
            confidence=0.93,
            citations=["Labor Code 2019, Article 5"],
        )
        self.bundle = _bundle("q_labor", SUPPORTED, 0.93, [self.labor_chunk])
        self.engine = ActionEngine()

    def test_status_complete(self):
        req = ActionRequest(ACTION_DRAFT, "Draft an employment clause for working hours.", request_id="r1")
        result = self.engine.execute(req, [self.bundle])
        assert result.status in (STATUS_COMPLETE, STATUS_PARTIAL)

    def test_output_has_generated_label(self):
        req = ActionRequest(ACTION_DRAFT, "Draft an employment clause for working hours.", request_id="r2")
        result = self.engine.execute(req, [self.bundle])
        assert "[GENERATED]" in result.output

    def test_output_has_source_label(self):
        req = ActionRequest(ACTION_DRAFT, "Draft an employment clause for working hours.", request_id="r3")
        result = self.engine.execute(req, [self.bundle])
        assert "[SOURCE]" in result.output

    def test_citations_present(self):
        req = ActionRequest(ACTION_DRAFT, "Draft an employment clause for working hours.", request_id="r4")
        result = self.engine.execute(req, [self.bundle])
        assert len(result.citations) > 0

    def test_evidence_refs_present(self):
        req = ActionRequest(ACTION_DRAFT, "Draft employment clause.", request_id="r5")
        result = self.engine.execute(req, [self.bundle])
        assert len(result.evidence_refs) > 0

    def test_assumptions_stated(self):
        req = ActionRequest(ACTION_DRAFT, "Draft employment clause.", request_id="r6")
        result = self.engine.execute(req, [self.bundle])
        assert len(result.assumptions) > 0

    def test_source_content_in_evidence_refs(self):
        req = ActionRequest(ACTION_DRAFT, "Draft employment clause.", request_id="r7")
        result = self.engine.execute(req, [self.bundle])
        excerpts = [r.excerpt for r in result.evidence_refs]
        assert any("working hours" in ex.lower() or "overtime" in ex.lower() for ex in excerpts)

    def test_no_evidence_gives_insufficient(self):
        empty = empty_bundle("q_empty", "No evidence.")
        req = ActionRequest(ACTION_DRAFT, "Draft something.", request_id="r8")
        result = self.engine.execute(req, [empty])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE

    def test_is_marked_as_generated(self):
        req = ActionRequest(ACTION_DRAFT, "Draft clause.", request_id="r9")
        result = self.engine.execute(req, [self.bundle])
        assert result.is_generated is True


# ---------------------------------------------------------------------------
# Fixture 2: Compliance check — policy against regulation
# ---------------------------------------------------------------------------


class TestComplianceWorkflow:

    def setup_method(self):
        self.policy_chunk = _chunk(
            "chunk_policy_overtime",
            content="Section 3. Overtime Policy. Overtime will be paid at 120% of base rate.",
            confidence=0.90,
            citations=["CompanyCo HR Policy, Section 3"],
        )
        self.regulation_chunk = _chunk(
            "chunk_reg_overtime",
            content=(
                "Article 97. Overtime compensation shall not be less than 150% of the "
                "normal hourly wage for weekday overtime."
            ),
            confidence=0.95,
            citations=["Labor Code 2019, Article 97"],
        )
        self.policy_bundle = _bundle("q_policy", SUPPORTED, 0.90, [self.policy_chunk])
        self.reg_bundle = _bundle("q_regulation", SUPPORTED, 0.95, [self.regulation_chunk])
        self.engine = ActionEngine()

    def test_status_complete_when_both_sides_present(self):
        req = ActionRequest(ACTION_COMPLIANCE, "Check overtime policy against labor law.", request_id="c1")
        result = self.engine.execute(req, [self.policy_bundle, self.reg_bundle])
        assert result.status in (STATUS_COMPLETE, STATUS_PARTIAL)

    def test_output_cites_both_sides(self):
        req = ActionRequest(ACTION_COMPLIANCE, "Check overtime policy.", request_id="c2")
        result = self.engine.execute(req, [self.policy_bundle, self.reg_bundle])
        assert "CompanyCo" in result.output or "Policy" in result.output
        assert "Labor Code" in result.output or "Article 97" in result.output

    def test_generated_label_present(self):
        req = ActionRequest(ACTION_COMPLIANCE, "Check overtime policy.", request_id="c3")
        result = self.engine.execute(req, [self.policy_bundle, self.reg_bundle])
        assert "[GENERATED]" in result.output

    def test_insufficient_when_only_one_bundle(self):
        req = ActionRequest(ACTION_COMPLIANCE, "Check overtime policy.", request_id="c4")
        result = self.engine.execute(req, [self.policy_bundle])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE

    def test_insufficient_when_target_missing(self):
        req = ActionRequest(ACTION_COMPLIANCE, "Check policy.", request_id="c5")
        result = self.engine.execute(req, [empty_bundle("q_empty", "No evidence."), self.reg_bundle])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE

    def test_missing_evidence_described(self):
        req = ActionRequest(ACTION_COMPLIANCE, "Check policy.", request_id="c6")
        result = self.engine.execute(req, [self.policy_bundle])
        assert len(result.missing_evidence) > 0

    def test_no_compliance_claim_without_evidence(self):
        """Core safety rule: no claim of compliance/non-compliance without both sides."""
        req = ActionRequest(ACTION_COMPLIANCE, "Is our policy compliant?", request_id="c7")
        result = self.engine.execute(req, [empty_bundle("q1", "no seeds."), empty_bundle("q2", "no seeds.")])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE
        # The output must not assert compliance
        assert "compliant" not in result.output.lower() or "cannot" in result.output.lower()


# ---------------------------------------------------------------------------
# Fixture 3: Risk analysis — risky or missing clauses
# ---------------------------------------------------------------------------


class TestRiskWorkflow:

    def setup_method(self):
        self.risky_chunk = _chunk(
            "chunk_risky_termination",
            content=(
                "Article 8. Termination. Either party may terminate this agreement "
                "with 3 days notice, without cause or compensation."
            ),
            confidence=0.88,
            citations=["ServiceContract v1.0, Article 8"],
        )
        self.bundle = _bundle("q_risk", SUPPORTED, 0.88, [self.risky_chunk])
        self.engine = ActionEngine()

    def test_status_complete(self):
        req = ActionRequest(ACTION_RISK, "Identify risky clauses in the service contract.", request_id="rk1")
        result = self.engine.execute(req, [self.bundle])
        assert result.status in (STATUS_COMPLETE, STATUS_PARTIAL)

    def test_evidence_refs_cite_source_clause(self):
        req = ActionRequest(ACTION_RISK, "Identify risky clauses.", request_id="rk2")
        result = self.engine.execute(req, [self.bundle])
        assert len(result.evidence_refs) > 0
        excerpts = " ".join(r.excerpt for r in result.evidence_refs)
        assert "termination" in excerpts.lower() or "terminate" in excerpts.lower()

    def test_source_label_in_output(self):
        req = ActionRequest(ACTION_RISK, "Identify risky clauses.", request_id="rk3")
        result = self.engine.execute(req, [self.bundle])
        assert "[SOURCE]" in result.output

    def test_generated_label_in_output(self):
        req = ActionRequest(ACTION_RISK, "Identify risky clauses.", request_id="rk4")
        result = self.engine.execute(req, [self.bundle])
        assert "[GENERATED]" in result.output

    def test_no_evidence_gives_insufficient(self):
        req = ActionRequest(ACTION_RISK, "Identify risks.", request_id="rk5")
        result = self.engine.execute(req, [empty_bundle("q_empty", "No evidence.")])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE

    def test_citations_match_source(self):
        req = ActionRequest(ACTION_RISK, "Identify risks.", request_id="rk6")
        result = self.engine.execute(req, [self.bundle])
        assert "ServiceContract v1.0, Article 8" in result.citations


# ---------------------------------------------------------------------------
# Summarization workflow
# ---------------------------------------------------------------------------


class TestSummarizeWorkflow:

    def test_summary_from_supported_bundle(self):
        chunk = _chunk("c_sum", "Article 3. Obligations. The seller shall deliver on time.", confidence=0.91,
                       citations=["Contract, Art 3"])
        bundle = _bundle("q_sum", SUPPORTED, 0.91, [chunk])
        req = ActionRequest(ACTION_SUMMARIZE, "Summarise the obligations.", request_id="s1")
        result = ActionEngine().execute(req, [bundle])
        assert result.status in (STATUS_COMPLETE, STATUS_PARTIAL)
        assert "[GENERATED]" in result.output
        assert "[SOURCE" in result.output

    def test_no_evidence_gives_insufficient(self):
        req = ActionRequest(ACTION_SUMMARIZE, "Summarise.", request_id="s2")
        result = ActionEngine().execute(req, [empty_bundle("q", "no seeds.")])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE


# ---------------------------------------------------------------------------
# Cross-document comparison
# ---------------------------------------------------------------------------


class TestCompareWorkflow:

    def test_comparison_requires_two_bundles(self):
        chunk = _chunk("c1", "Article 1 content.", citations=["Doc A, Art 1"])
        bundle = _bundle("q_a", SUPPORTED, 0.90, [chunk])
        req = ActionRequest(ACTION_COMPARE, "Compare the two contracts.", request_id="cmp1")
        result = ActionEngine().execute(req, [bundle])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE

    def test_comparison_with_two_bundles(self):
        chunk_a = _chunk("ca", "Contract A: payment in 30 days.", citations=["Contract A, Art 5"])
        chunk_b = _chunk("cb", "Contract B: payment in 60 days.", citations=["Contract B, Art 5"])
        bundle_a = _bundle("q_a", SUPPORTED, 0.90, [chunk_a])
        bundle_b = _bundle("q_b", SUPPORTED, 0.90, [chunk_b])
        req = ActionRequest(ACTION_COMPARE, "Compare payment terms.", request_id="cmp2")
        result = ActionEngine().execute(req, [bundle_a, bundle_b])
        assert result.status in (STATUS_COMPLETE, STATUS_PARTIAL)
        assert "[SOURCE]" in result.output
        assert "[GENERATED]" in result.output
        # Both sides cited
        assert "Contract A" in result.output or "30 days" in result.output
        assert "Contract B" in result.output or "60 days" in result.output


# ---------------------------------------------------------------------------
# Clause recommendation
# ---------------------------------------------------------------------------


class TestRecommendWorkflow:

    def test_recommend_from_evidence(self):
        chunk = _chunk("cr", "Standard NDA clause: Confidential information shall not be disclosed.",
                       citations=["Model NDA, Clause 2"])
        bundle = _bundle("q_nda", SUPPORTED, 0.90, [chunk])
        req = ActionRequest(ACTION_RECOMMEND, "Recommend an NDA clause.", request_id="rec1")
        result = ActionEngine().execute(req, [bundle])
        assert result.status in (STATUS_COMPLETE, STATUS_PARTIAL)
        assert "[SOURCE]" in result.output
        assert len(result.citations) > 0

    def test_no_evidence_gives_insufficient(self):
        req = ActionRequest(ACTION_RECOMMEND, "Recommend a clause.", request_id="rec2")
        result = ActionEngine().execute(req, [empty_bundle("q", "no evidence.")])
        assert result.status == STATUS_INSUFFICIENT_EVIDENCE


# ---------------------------------------------------------------------------
# ActionRequest schema validation
# ---------------------------------------------------------------------------


class TestActionRequestValidation:

    def test_invalid_action_type_raises(self):
        with pytest.raises(ValueError, match="Unknown action_type"):
            ActionRequest("magic_action", "Do something.", request_id="x")

    def test_valid_action_types_accepted(self):
        for action in (ACTION_DRAFT, ACTION_COMPLIANCE, ACTION_RISK,
                       ACTION_RECOMMEND, ACTION_SUMMARIZE, ACTION_COMPARE):
            req = ActionRequest(action, "Some query.", request_id="v1")
            assert req.action_type == action


# ---------------------------------------------------------------------------
# ActionEngine safety rules
# ---------------------------------------------------------------------------


class TestActionEngineSafety:

    def test_unknown_action_type_refused(self):
        engine = ActionEngine()
        # Bypass schema validation by constructing manually
        req = ActionRequest.__new__(ActionRequest)
        req.action_type = "forbidden_action"
        req.query = "Do something bad."
        req.document_ids = []
        req.parameters = {}
        req.request_id = "safe1"
        result = engine.execute(req, [])
        assert result.status == STATUS_REFUSED

    def test_actionresult_is_actionable(self):
        from src.actions.action_schema import ActionResult
        r = ActionResult("r", ACTION_SUMMARIZE, STATUS_COMPLETE, "output")
        assert r.is_actionable() is True

    def test_actionresult_insufficient_not_actionable(self):
        from src.actions.action_schema import ActionResult
        r = ActionResult("r", ACTION_SUMMARIZE, STATUS_INSUFFICIENT_EVIDENCE, "no evidence")
        assert r.is_actionable() is False

    def test_refused_not_actionable(self):
        from src.actions.action_schema import ActionResult
        r = ActionResult("r", ACTION_DRAFT, STATUS_REFUSED, "refused", refusal_reason="safety")
        assert r.is_actionable() is False
