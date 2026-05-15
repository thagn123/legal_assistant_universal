"""
Async job orchestration for document processing — Phase 10.

Jobs are persisted in SQLite before being dispatched, so they survive
process restarts. On startup, the runner requeues any job left in
'queued' or 'running' state from the previous session.

Pass criterion: Jobs are resumable and auditable.

Processor signature:
    def processor(user_id: str, doc_id: str, checkpoint: dict) -> dict:
        # Returns an updated checkpoint dict.
        # Should write intermediate state to checkpoint at each stage
        # so the job can be restarted from the last completed stage.
        ...

Default processor is a stub. Replace by passing `processor=` to JobRunner.
"""

from __future__ import annotations

import threading
from queue import Empty, Queue
from typing import Callable, Optional

from src.runtime.storage import JobRecord, StorageLayer

# Processor: (user_id, doc_id, checkpoint) → final checkpoint dict
ProcessorFn = Callable[[str, str, dict], dict]


def _default_processor(user_id: str, doc_id: str, checkpoint: dict) -> dict:
    """
    Stub processor — returns immediately with a complete checkpoint.

    Real implementation runs pipeline stages in order:
        profile → extract → chunk → embed → graph → index
    Each stage writes its output to the checkpoint dict so the job
    can resume from the last completed stage after a crash.
    """
    stages = ["profile", "extract", "chunk", "embed", "graph", "index"]
    last_stage = checkpoint.get("stage", "")
    start_idx = (stages.index(last_stage) + 1) if last_stage in stages else 0
    final_checkpoint = dict(checkpoint)
    for stage in stages[start_idx:]:
        final_checkpoint["stage"] = stage
    final_checkpoint["doc_id"] = doc_id
    final_checkpoint["chunks_produced"] = 0
    return final_checkpoint


class JobRunner:
    """
    Thread-pool job runner backed by a persistent SQLite job queue.

    Crash recovery: on __init__, all jobs in 'queued' or 'running' state
    from the previous session are reset and requeued automatically.
    """

    def __init__(
        self,
        storage: StorageLayer,
        processor: Optional[ProcessorFn] = None,
        workers: int = 2,
    ) -> None:
        self._storage = storage
        self._processor = processor or _default_processor
        self._queue: Queue[str] = Queue()
        self._shutdown = threading.Event()

        self._threads = [
            threading.Thread(
                target=self._worker,
                daemon=True,
                name=f"job-worker-{i}",
            )
            for i in range(workers)
        ]
        for t in self._threads:
            t.start()

        # Recover jobs interrupted by a previous crash
        self._resume_pending()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def submit(self, user_id: str, doc_id: str) -> JobRecord:
        """Create a new job record and enqueue it for processing."""
        job = self._storage.create_job(user_id, doc_id)
        self._queue.put(job.job_id)
        return job

    def shutdown(self, timeout: float = 2.0) -> None:
        """Signal workers to stop after finishing their current job."""
        self._shutdown.set()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _resume_pending(self) -> None:
        """Requeue jobs left in queued/running state from a previous session."""
        for job in self._storage.list_resumable_jobs():
            # Reset 'running' back to 'queued' so the worker re-runs it
            if job.status == "running":
                self._storage.update_job(job.job_id, "queued")
            self._queue.put(job.job_id)

    def _worker(self) -> None:
        while not self._shutdown.is_set():
            try:
                job_id = self._queue.get(timeout=0.1)
            except Empty:
                continue

            try:
                job = self._storage.get_job_by_id(job_id)
                if job is None or job.status == "complete":
                    self._queue.task_done()
                    continue

                checkpoint = job.checkpoint or {}
                self._storage.update_job(job_id, "running", checkpoint=checkpoint)

                result_checkpoint = self._processor(job.user_id, job.doc_id, checkpoint)

                self._storage.update_job(job_id, "complete", checkpoint=result_checkpoint)
                self._storage.update_document_status(job.doc_id, "ready")
            except Exception as exc:
                self._storage.update_job(job_id, "failed", error=str(exc))
                self._storage.update_document_status(job.doc_id, "failed")
            finally:
                self._queue.task_done()
