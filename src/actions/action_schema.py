"""
Action request and result schema for the Phase 9 Action Engine.

Actions are legal-workflow tasks that go beyond Q&A: drafting, compliance
checking, risk analysis, clause recommendation, and cross-document comparison.

Design rules (from docs/05-actions/action-engine.md):
  - Every action result cites source evidence.
  - Generated content is always marked as generated (never passed off as source).
  - Assumptions and missing information are always declared.
  - Compliance claims are only made when evidence supports them.
  - Actions with insufficient evidence return INSUFFICIENT_EVIDENCE status.

Usage:
    from src.actions.action_schema import ActionRequest, ActionResult, ACTION_DRAFT

    req = ActionRequest(
        action_type=ACTION_DRAFT,
        query="Draft an NDA clause based on uploaded law.",
        document_ids=["doc_abc"],
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Action type constants
# ---------------------------------------------------------------------------

ACTION_DRAFT = "contract_drafting"
ACTION_COMPLIANCE = "compliance_checking"
ACTION_RISK = "risk_analysis"
ACTION_RECOMMEND = "clause_recommendation"
ACTION_SUMMARIZE = "legal_summarization"
ACTION_COMPARE = "cross_document_comparison"

ALL_ACTION_TYPES = (
    ACTION_DRAFT,
    ACTION_COMPLIANCE,
    ACTION_RISK,
    ACTION_RECOMMEND,
    ACTION_SUMMARIZE,
    ACTION_COMPARE,
)

# ---------------------------------------------------------------------------
# Action result status constants
# ---------------------------------------------------------------------------

STATUS_COMPLETE = "complete"             # All evidence found, action fully executed
STATUS_PARTIAL = "partial"              # Executed with caveats; some evidence missing
STATUS_INSUFFICIENT_EVIDENCE = "insufficient_evidence"   # Cannot act without more evidence
STATUS_REFUSED = "refused"              # Safety rule violation; action cannot be performed

# ---------------------------------------------------------------------------
# Evidence reference: links one piece of generated output to its source
# ---------------------------------------------------------------------------


@dataclass
class EvidenceRef:
    """
    Links a claim or generated fragment to its source evidence.

    Fields:
        chunk_id:     The chunk that supports this claim.
        citation:     Human-readable citation string from the chunk.
        excerpt:      Verbatim text excerpt from the source chunk.
        confidence:   Source chunk confidence score.
        is_generated: True if the associated output text was generated (not quoted).
    """
    chunk_id: str
    citation: str = ""
    excerpt: str = ""
    confidence: float = 1.0
    is_generated: bool = False


# ---------------------------------------------------------------------------
# Action request
# ---------------------------------------------------------------------------


@dataclass
class ActionRequest:
    """
    A single action request from the user.

    Fields:
        action_type:    One of the ACTION_* constants.
        query:          The user's natural-language request.
        document_ids:   Which documents are in scope (empty = all uploaded).
        parameters:     Action-specific parameters (e.g. target_clause, jurisdiction).
        request_id:     Caller-assigned identifier for this request.
    """
    action_type: str
    query: str
    document_ids: List[str] = field(default_factory=list)
    parameters: Dict[str, str] = field(default_factory=dict)
    request_id: str = ""

    def __post_init__(self):
        if self.action_type not in ALL_ACTION_TYPES:
            raise ValueError(
                f"Unknown action_type {self.action_type!r}. "
                f"Must be one of: {ALL_ACTION_TYPES}"
            )


# ---------------------------------------------------------------------------
# Action result
# ---------------------------------------------------------------------------


@dataclass
class ActionResult:
    """
    Output of an action execution.

    Fields:
        request_id:         Matches the ActionRequest.request_id.
        action_type:        The action that was performed.
        status:             complete | partial | insufficient_evidence | refused
        output:             The primary action output (generated text, analysis, etc.)
        evidence_refs:      All source evidence backing material claims.
        assumptions:        Explicitly stated assumptions made during the action.
        missing_evidence:   Descriptions of evidence that was needed but not found.
        citations:          Deduplicated citation strings from all evidence_refs.
        warnings:           Non-fatal issues (low confidence sources, etc.)
        is_generated:       True if output contains generated (non-source) text.
        refusal_reason:     Set when status=refused, explains why action was rejected.
    """
    request_id: str
    action_type: str
    status: str
    output: str
    evidence_refs: List[EvidenceRef] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    missing_evidence: List[str] = field(default_factory=list)
    citations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    is_generated: bool = False
    refusal_reason: str = ""

    def is_actionable(self) -> bool:
        """True if the result contains usable output (complete or partial)."""
        return self.status in (STATUS_COMPLETE, STATUS_PARTIAL)

    def summary(self) -> str:
        return (
            f"ActionResult(type={self.action_type}, status={self.status}, "
            f"refs={len(self.evidence_refs)}, generated={self.is_generated})"
        )
