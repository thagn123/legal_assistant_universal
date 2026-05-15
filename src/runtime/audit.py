"""
Audit trail for generated legal outputs — Phase 10.

Every ActionResult delivered to a user is logged here.

Pass criterion: every answer links back to stored evidence via
    request_id  → matches the ActionRequest that produced it
    output_hash → SHA-256 of the exact output text delivered

This allows post-hoc verification that:
  - the output has not been tampered with, and
  - the request_id can be cross-referenced with evidence_refs in the result.
"""

from __future__ import annotations

import hashlib
from typing import List

from src.actions.action_schema import ActionResult
from src.runtime.storage import AuditRecord, StorageLayer


class AuditLayer:
    """Logs action results for traceability and regulatory compliance."""

    def __init__(self, storage: StorageLayer) -> None:
        self._storage = storage

    def log_action_result(self, user_id: str, result: ActionResult) -> AuditRecord:
        """
        Log a completed action result.

        output_hash is SHA-256 of the output text, allowing verification
        that the logged output matches what was delivered.
        """
        output_hash = hashlib.sha256(result.output.encode("utf-8")).hexdigest()
        return self._storage.log_action(
            user_id=user_id,
            request_id=result.request_id,
            action_type=result.action_type,
            status=result.status,
            output_hash=output_hash,
        )

    def get_trail(self, user_id: str) -> List[AuditRecord]:
        """Return the full audit trail for the given user, newest first."""
        return self._storage.get_audit_trail(user_id)
