"""
Action Engine — Phase 9 dispatcher.

Routes ActionRequests to the appropriate workflow and enforces the safety
rules from docs/05-actions/action-engine.md before any output is returned.

Safety rules enforced here (not in individual workflows):
  1. Output containing no evidence_refs is refused for ACTION_DRAFT and ACTION_COMPLIANCE.
  2. Generated content is always present in the output as [GENERATED] labels.
  3. An action that would claim compliance without evidence is blocked.
  4. Unknown action types are refused.

Usage:
    from src.actions.action_engine import ActionEngine
    from src.actions.action_schema import ActionRequest, ACTION_SUMMARIZE

    engine = ActionEngine()
    result = engine.execute(
        request=ActionRequest(ACTION_SUMMARIZE, "Summarise Article 1", request_id="r1"),
        bundles=[bundle],
    )
    print(result.status, result.output[:200])
"""

from __future__ import annotations

from typing import List

from src.actions.action_schema import (
    ACTION_COMPLIANCE,
    ACTION_COMPARE,
    ACTION_DRAFT,
    ACTION_RECOMMEND,
    ACTION_RISK,
    ACTION_SUMMARIZE,
    ActionRequest,
    ActionResult,
    STATUS_REFUSED,
)
from src.actions.workflows import (
    workflow_compare,
    workflow_compliance,
    workflow_draft,
    workflow_recommend,
    workflow_risk,
    workflow_summarize,
)
from src.graphrag.evidence_bundle import EvidenceBundle


# ---------------------------------------------------------------------------
# Safety checks
# ---------------------------------------------------------------------------

# Actions that must not produce authoritative output without evidence refs
_EVIDENCE_REQUIRED = {ACTION_DRAFT, ACTION_COMPLIANCE, ACTION_RISK}

_GENERATED_LABEL = "[GENERATED]"


def _safety_check(result: ActionResult) -> ActionResult:
    """
    Apply post-execution safety checks to an ActionResult.

    Returns the result unchanged if all checks pass.
    Returns a STATUS_REFUSED result if a safety rule is violated.
    """
    # Rule 1: Evidence-critical actions must cite at least one source
    if result.action_type in _EVIDENCE_REQUIRED and result.is_generated:
        if not result.evidence_refs:
            return ActionResult(
                request_id=result.request_id,
                action_type=result.action_type,
                status=STATUS_REFUSED,
                output=(
                    "Action refused: generated output for this action type requires "
                    "at least one evidence source. No evidence was found."
                ),
                refusal_reason=(
                    f"{result.action_type} cannot produce generated output without evidence."
                ),
            )

    # Rule 2: Generated output must carry [GENERATED] labels
    if result.is_generated and _GENERATED_LABEL not in result.output:
        return ActionResult(
            request_id=result.request_id,
            action_type=result.action_type,
            status=STATUS_REFUSED,
            output=(
                "Action refused: generated output was produced without proper "
                "[GENERATED] labels. This is an internal safety violation."
            ),
            refusal_reason="Generated content label missing from output.",
        )

    return result


# ---------------------------------------------------------------------------
# ActionEngine
# ---------------------------------------------------------------------------


class ActionEngine:
    """
    Dispatches ActionRequests to workflow functions and enforces safety rules.

    Args:
        authority_threshold: Minimum chunk confidence to consider authoritative (default 0.65).
    """

    def __init__(self, authority_threshold: float = 0.65) -> None:
        self.authority_threshold = authority_threshold

        self._dispatch = {
            ACTION_SUMMARIZE:  workflow_summarize,
            ACTION_COMPLIANCE: workflow_compliance,
            ACTION_RISK:       workflow_risk,
            ACTION_DRAFT:      workflow_draft,
            ACTION_RECOMMEND:  workflow_recommend,
            ACTION_COMPARE:    workflow_compare,
        }

    def execute(
        self,
        request: ActionRequest,
        bundles: List[EvidenceBundle],
    ) -> ActionResult:
        """
        Execute an action request against the provided evidence bundles.

        Args:
            request: The ActionRequest describing what to do.
            bundles: Evidence bundles assembled from retrieval + traversal.

        Returns:
            ActionResult with output, citations, and status.
        """
        workflow_fn = self._dispatch.get(request.action_type)
        if workflow_fn is None:
            return ActionResult(
                request_id=request.request_id,
                action_type=request.action_type,
                status=STATUS_REFUSED,
                output=f"Unknown action type: {request.action_type!r}.",
                refusal_reason=f"Action type {request.action_type!r} is not supported.",
            )

        result = workflow_fn(request, bundles, self.authority_threshold)
        return _safety_check(result)
