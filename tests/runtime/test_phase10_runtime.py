"""
Phase 10 validation: Product Runtime — storage, auth, audit, job runner.

Pass criteria (from docs/07-implementation/development-pipeline.md):
  1. Jobs are resumable and auditable.
  2. Users can query only their own document spaces.
  3. Every answer links back to stored evidence.

All tests are deterministic — no LLM calls, no file I/O beyond :memory: SQLite.
"""

from __future__ import annotations

import hashlib
import os
import tempfile
import threading
import time

import pytest

from src.actions.action_schema import ACTION_SUMMARIZE, ActionResult, STATUS_COMPLETE
from src.runtime.audit import AuditLayer
from src.runtime.auth import AuthLayer
from src.runtime.job_runner import JobRunner
from src.runtime.storage import StorageLayer


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def storage() -> StorageLayer:
    return StorageLayer(":memory:")


@pytest.fixture
def auth(storage: StorageLayer) -> AuthLayer:
    return AuthLayer(storage)


@pytest.fixture
def audit(storage: StorageLayer) -> AuditLayer:
    return AuditLayer(storage)


# ---------------------------------------------------------------------------
# Tenant isolation (Pass criterion 2)
# ---------------------------------------------------------------------------


class TestTenantIsolation:

    def test_documents_isolated_by_user(self, storage: StorageLayer):
        user_a = storage.create_user("key_a")
        user_b = storage.create_user("key_b")
        doc_a = storage.create_document(user_a.user_id, "contract_a.pdf")
        storage.create_document(user_b.user_id, "contract_b.pdf")

        docs_a = storage.list_documents(user_a.user_id)
        assert len(docs_a) == 1
        assert docs_a[0].doc_id == doc_a.doc_id

    def test_get_document_cross_tenant_returns_none(self, storage: StorageLayer):
        user_a = storage.create_user("key_a2")
        user_b = storage.create_user("key_b2")
        doc_a = storage.create_document(user_a.user_id, "doc_a.pdf")

        result = storage.get_document(user_b.user_id, doc_a.doc_id)
        assert result is None

    def test_jobs_isolated_by_user(self, storage: StorageLayer):
        user_a = storage.create_user("key_a3")
        user_b = storage.create_user("key_b3")
        doc_a = storage.create_document(user_a.user_id, "d_a.pdf")
        doc_b = storage.create_document(user_b.user_id, "d_b.pdf")
        job_a = storage.create_job(user_a.user_id, doc_a.doc_id)
        job_b = storage.create_job(user_b.user_id, doc_b.doc_id)

        ids_a = {j.job_id for j in storage.list_jobs(user_a.user_id)}
        assert job_a.job_id in ids_a
        assert job_b.job_id not in ids_a

    def test_get_job_cross_tenant_returns_none(self, storage: StorageLayer):
        user_a = storage.create_user("key_a4")
        user_b = storage.create_user("key_b4")
        doc_a = storage.create_document(user_a.user_id, "x.pdf")
        job_a = storage.create_job(user_a.user_id, doc_a.doc_id)

        result = storage.get_job(user_b.user_id, job_a.job_id)
        assert result is None

    def test_audit_trail_isolated_by_user(self, storage: StorageLayer, audit: AuditLayer):
        user_a = storage.create_user("key_a5")
        user_b = storage.create_user("key_b5")

        audit.log_action_result(
            user_a.user_id,
            ActionResult("req_a", ACTION_SUMMARIZE, STATUS_COMPLETE, "[GENERATED] A"),
        )
        audit.log_action_result(
            user_b.user_id,
            ActionResult("req_b", ACTION_SUMMARIZE, STATUS_COMPLETE, "[GENERATED] B"),
        )

        ids_a = {r.request_id for r in audit.get_trail(user_a.user_id)}
        ids_b = {r.request_id for r in audit.get_trail(user_b.user_id)}

        assert "req_a" in ids_a and "req_b" not in ids_a
        assert "req_b" in ids_b and "req_a" not in ids_b


# ---------------------------------------------------------------------------
# Job resumability (Pass criterion 1)
# ---------------------------------------------------------------------------


class TestJobResumability:

    def test_job_created_in_queued_state(self, storage: StorageLayer):
        user = storage.create_user("key_r1")
        doc = storage.create_document(user.user_id, "f.pdf")
        job = storage.create_job(user.user_id, doc.doc_id)
        assert job.status == "queued"

    def test_job_state_persists_across_storage_instances(self):
        """Simulate process restart: job state survives in SQLite file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name
        s1 = s2 = None
        try:
            s1 = StorageLayer(db_path)
            user = s1.create_user("key_persist")
            doc = s1.create_document(user.user_id, "doc.pdf")
            job = s1.create_job(user.user_id, doc.doc_id)
            s1.update_job(job.job_id, "running", checkpoint={"stage": "extract"})
            s1.close()
            s1 = None

            # New storage instance (simulated restart)
            s2 = StorageLayer(db_path)
            recovered = s2.get_job_by_id(job.job_id)
            assert recovered is not None
            assert recovered.status == "running"
            assert recovered.checkpoint == {"stage": "extract"}
            s2.close()
            s2 = None
        finally:
            if s1 is not None:
                s1.close()
            if s2 is not None:
                s2.close()
            os.unlink(db_path)

    def test_checkpoint_stored_and_retrieved(self, storage: StorageLayer):
        user = storage.create_user("key_ckpt")
        doc = storage.create_document(user.user_id, "d.pdf")
        job = storage.create_job(user.user_id, doc.doc_id)

        storage.update_job(job.job_id, "running", checkpoint={"stage": "chunk", "page": 5})
        updated = storage.get_job_by_id(job.job_id)
        assert updated.checkpoint == {"stage": "chunk", "page": 5}

    def test_failed_job_preserved_with_error_message(self, storage: StorageLayer):
        user = storage.create_user("key_fail")
        doc = storage.create_document(user.user_id, "bad.pdf")
        job = storage.create_job(user.user_id, doc.doc_id)

        storage.update_job(job.job_id, "failed", error="OCR timeout")
        failed = storage.get_job_by_id(job.job_id)
        assert failed.status == "failed"
        assert failed.error == "OCR timeout"
        assert failed.completed_at is not None

    def test_list_resumable_returns_queued_and_running_only(self, storage: StorageLayer):
        user = storage.create_user("key_res")
        d1 = storage.create_document(user.user_id, "d1.pdf")
        d2 = storage.create_document(user.user_id, "d2.pdf")
        d3 = storage.create_document(user.user_id, "d3.pdf")

        j1 = storage.create_job(user.user_id, d1.doc_id)          # queued
        j2 = storage.create_job(user.user_id, d2.doc_id)
        storage.update_job(j2.job_id, "running")                   # running
        j3 = storage.create_job(user.user_id, d3.doc_id)
        storage.update_job(j3.job_id, "complete")                  # complete

        resumable_ids = {j.job_id for j in storage.list_resumable_jobs()}
        assert j1.job_id in resumable_ids
        assert j2.job_id in resumable_ids
        assert j3.job_id not in resumable_ids

    def test_job_runner_processes_job_to_complete(self, storage: StorageLayer):
        """JobRunner transitions job queued → complete."""
        done = threading.Event()

        def fast_processor(user_id, doc_id, checkpoint):
            done.set()
            return {"stage": "index"}

        user = storage.create_user("key_run")
        doc = storage.create_document(user.user_id, "run.pdf")
        runner = JobRunner(storage, processor=fast_processor, workers=1)
        job = runner.submit(user.user_id, doc.doc_id)

        done.wait(timeout=5.0)
        time.sleep(0.15)  # let storage commit

        updated = storage.get_job_by_id(job.job_id)
        assert updated.status == "complete"
        runner.shutdown()

    def test_job_runner_recovers_running_jobs_on_start(self, storage: StorageLayer):
        """Jobs left 'running' (crash) are reset and reprocessed on next startup."""
        user = storage.create_user("key_crash")
        doc = storage.create_document(user.user_id, "stale.pdf")
        job = storage.create_job(user.user_id, doc.doc_id)
        storage.update_job(job.job_id, "running")  # simulate crash mid-job

        done = threading.Event()

        def recovery_processor(user_id, doc_id, checkpoint):
            done.set()
            return {"stage": "index"}

        runner = JobRunner(storage, processor=recovery_processor, workers=1)
        done.wait(timeout=5.0)
        time.sleep(0.15)

        updated = storage.get_job_by_id(job.job_id)
        assert updated.status == "complete"
        runner.shutdown()

    def test_document_marked_ready_after_job_complete(self, storage: StorageLayer):
        user = storage.create_user("key_ready")
        doc = storage.create_document(user.user_id, "ready.pdf")

        done = threading.Event()

        def mark_processor(user_id, doc_id, checkpoint):
            done.set()
            return {"stage": "index"}

        runner = JobRunner(storage, processor=mark_processor, workers=1)
        runner.submit(user.user_id, doc.doc_id)
        done.wait(timeout=5.0)
        time.sleep(0.15)

        updated_doc = storage.get_document(user.user_id, doc.doc_id)
        assert updated_doc.status == "ready"
        runner.shutdown()


# ---------------------------------------------------------------------------
# Auth layer
# ---------------------------------------------------------------------------


class TestAuthLayer:

    def test_valid_key_accepted(self, auth: AuthLayer):
        auth.create_user("secret_key")
        assert auth.verify("secret_key") is not None

    def test_invalid_key_rejected(self, auth: AuthLayer):
        assert auth.verify("wrong_key") is None

    def test_require_raises_on_invalid_key(self, auth: AuthLayer):
        with pytest.raises(ValueError, match="Invalid"):
            auth.require("bad_key")

    def test_different_keys_map_to_different_users(self, auth: AuthLayer):
        auth.create_user("key_x")
        auth.create_user("key_y")
        assert auth.verify("key_x") != auth.verify("key_y")

    def test_api_key_not_stored_as_plaintext(self, storage: StorageLayer):
        """API keys must be hashed before storage."""
        storage.create_user("plaintext_key")
        with storage._lock:
            row = storage._conn.execute(
                "SELECT api_key_hash FROM users WHERE api_key_hash=?",
                ("plaintext_key",),
            ).fetchone()
        assert row is None, "API key stored as plaintext — must be hashed."


# ---------------------------------------------------------------------------
# Audit trail (Pass criterion 3)
# ---------------------------------------------------------------------------


class TestAuditTrail:

    def test_action_result_logged_with_correct_fields(self, storage: StorageLayer, audit: AuditLayer):
        user = storage.create_user("key_aud1")
        result = ActionResult("req_001", ACTION_SUMMARIZE, STATUS_COMPLETE, "[GENERATED] output")
        record = audit.log_action_result(user.user_id, result)
        assert record.request_id == "req_001"
        assert record.action_type == ACTION_SUMMARIZE
        assert record.status == STATUS_COMPLETE

    def test_output_hash_matches_sha256_of_output(self, storage: StorageLayer, audit: AuditLayer):
        """output_hash enables verification that no tampering occurred."""
        user = storage.create_user("key_aud2")
        output_text = "[GENERATED] The contract requires 30-day payment terms."
        result = ActionResult("req_002", ACTION_SUMMARIZE, STATUS_COMPLETE, output_text)
        record = audit.log_action_result(user.user_id, result)
        expected = hashlib.sha256(output_text.encode("utf-8")).hexdigest()
        assert record.output_hash == expected

    def test_multiple_results_all_retrievable(self, storage: StorageLayer, audit: AuditLayer):
        user = storage.create_user("key_aud3")
        for i in range(3):
            r = ActionResult(f"req_{i:03d}", ACTION_SUMMARIZE, STATUS_COMPLETE, f"[GENERATED] {i}")
            audit.log_action_result(user.user_id, r)
        trail = audit.get_trail(user.user_id)
        assert len(trail) == 3

    def test_request_id_present_in_trail(self, storage: StorageLayer, audit: AuditLayer):
        user = storage.create_user("key_aud4")
        result = ActionResult("req_xyz", ACTION_SUMMARIZE, STATUS_COMPLETE, "[GENERATED] x")
        audit.log_action_result(user.user_id, result)
        trail = audit.get_trail(user.user_id)
        assert any(r.request_id == "req_xyz" for r in trail)


# ---------------------------------------------------------------------------
# Checklist progress local persistence (Phase 15)
# ---------------------------------------------------------------------------


class TestChecklistProgressStorage:

    def test_checklist_progress_round_trip(self, storage: StorageLayer):
        storage.save_checklist_progress("user_a", "checklist_1", ["a", "b"])
        assert storage.get_checklist_progress("user_a", "checklist_1") == ["a", "b"]

    def test_checklist_progress_is_user_scoped(self, storage: StorageLayer):
        storage.save_checklist_progress("user_a", "checklist_1", ["a"])
        storage.save_checklist_progress("user_b", "checklist_1", ["b"])
        assert storage.get_checklist_progress("user_a", "checklist_1") == ["a"]
        assert storage.get_checklist_progress("user_b", "checklist_1") == ["b"]

    def test_checklist_progress_deduplicates_items(self, storage: StorageLayer):
        storage.save_checklist_progress("user_a", "checklist_1", ["a", "a", "b"])
        assert storage.get_checklist_progress("user_a", "checklist_1") == ["a", "b"]
