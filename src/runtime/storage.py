"""
Persistent storage layer for Phase 10 Product Runtime.

Uses SQLite (stdlib) for zero-dependency persistence.
All document and job queries are scoped to user_id for tenant isolation.
API keys are stored as SHA-256 hashes — never in plaintext.

Tables:
    users       — user_id, api_key_hash, created_at
    documents   — doc_id, user_id, filename, status, created_at, metadata_json
    jobs        — job_id, user_id, doc_id, status, created_at, completed_at, error_msg, checkpoint_json
    audit_log   — audit_id, user_id, request_id, action_type, status, output_hash, created_at
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional


# ---------------------------------------------------------------------------
# Record dataclasses
# ---------------------------------------------------------------------------


@dataclass
class UserRecord:
    user_id: str
    api_key_hash: str
    created_at: str


@dataclass
class DocumentRecord:
    doc_id: str
    user_id: str
    filename: str
    status: str          # "uploaded" | "processing" | "ready" | "failed"
    created_at: str
    metadata: Dict = field(default_factory=dict)


@dataclass
class JobRecord:
    job_id: str
    user_id: str
    doc_id: str
    status: str          # "queued" | "running" | "complete" | "failed"
    created_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    checkpoint: Optional[Dict] = None


@dataclass
class AuditRecord:
    audit_id: str
    user_id: str
    request_id: str
    action_type: str
    status: str
    output_hash: str
    created_at: str


# ---------------------------------------------------------------------------
# Schema DDL
# ---------------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id      TEXT PRIMARY KEY,
    api_key_hash TEXT UNIQUE NOT NULL,
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS documents (
    doc_id        TEXT PRIMARY KEY,
    user_id       TEXT NOT NULL,
    filename      TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'uploaded',
    created_at    TEXT NOT NULL,
    metadata_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS jobs (
    job_id          TEXT PRIMARY KEY,
    user_id         TEXT NOT NULL,
    doc_id          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'queued',
    created_at      TEXT NOT NULL,
    completed_at    TEXT,
    error_msg       TEXT,
    checkpoint_json TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    audit_id    TEXT PRIMARY KEY,
    user_id     TEXT NOT NULL,
    request_id  TEXT NOT NULL,
    action_type TEXT NOT NULL,
    status      TEXT NOT NULL,
    output_hash TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()


def _row_to_job(row: sqlite3.Row) -> JobRecord:
    cp = row["checkpoint_json"]
    return JobRecord(
        job_id=row["job_id"],
        user_id=row["user_id"],
        doc_id=row["doc_id"],
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        error=row["error_msg"],
        checkpoint=json.loads(cp) if cp else None,
    )


def _row_to_doc(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        doc_id=row["doc_id"],
        user_id=row["user_id"],
        filename=row["filename"],
        status=row["status"],
        created_at=row["created_at"],
        metadata=json.loads(row["metadata_json"]),
    )


# ---------------------------------------------------------------------------
# StorageLayer
# ---------------------------------------------------------------------------


class StorageLayer:
    """
    Thread-safe SQLite-backed storage with tenant isolation.

    All document and job lookups require the caller to supply user_id —
    cross-tenant access returns None / empty list rather than raising.
    """

    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self._db_path = str(db_path)
        self._lock = threading.Lock()
        # check_same_thread=False is safe because all access is serialised by _lock.
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL;")
        with self._lock:
            self._conn.executescript(_SCHEMA)
            self._conn.commit()

    # ------------------------------------------------------------------
    # Users
    # ------------------------------------------------------------------

    def create_user(self, api_key: str) -> UserRecord:
        record = UserRecord(
            user_id=str(uuid.uuid4()),
            api_key_hash=_hash_key(api_key),
            created_at=_now(),
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO users(user_id, api_key_hash, created_at) VALUES (?,?,?)",
                (record.user_id, record.api_key_hash, record.created_at),
            )
            self._conn.commit()
        return record

    def get_user_by_key(self, api_key: str) -> Optional[UserRecord]:
        key_hash = _hash_key(api_key)
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM users WHERE api_key_hash=?", (key_hash,)
            ).fetchone()
        if row is None:
            return None
        return UserRecord(
            user_id=row["user_id"],
            api_key_hash=row["api_key_hash"],
            created_at=row["created_at"],
        )

    # ------------------------------------------------------------------
    # Documents (all reads scoped to user_id)
    # ------------------------------------------------------------------

    def create_document(
        self,
        user_id: str,
        filename: str,
        metadata: Optional[Dict] = None,
    ) -> DocumentRecord:
        record = DocumentRecord(
            doc_id=str(uuid.uuid4()),
            user_id=user_id,
            filename=filename,
            status="uploaded",
            created_at=_now(),
            metadata=metadata or {},
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO documents(doc_id, user_id, filename, status, created_at, metadata_json)"
                " VALUES (?,?,?,?,?,?)",
                (
                    record.doc_id,
                    record.user_id,
                    record.filename,
                    record.status,
                    record.created_at,
                    json.dumps(record.metadata),
                ),
            )
            self._conn.commit()
        return record

    def get_document(self, user_id: str, doc_id: str) -> Optional[DocumentRecord]:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM documents WHERE user_id=? AND doc_id=?",
                (user_id, doc_id),
            ).fetchone()
        return _row_to_doc(row) if row else None

    def list_documents(self, user_id: str) -> List[DocumentRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM documents WHERE user_id=? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [_row_to_doc(r) for r in rows]

    def update_document_status(self, doc_id: str, status: str) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE documents SET status=? WHERE doc_id=?",
                (status, doc_id),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Jobs (reads scoped to user_id; internal lookup by job_id only)
    # ------------------------------------------------------------------

    def create_job(self, user_id: str, doc_id: str) -> JobRecord:
        record = JobRecord(
            job_id=str(uuid.uuid4()),
            user_id=user_id,
            doc_id=doc_id,
            status="queued",
            created_at=_now(),
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO jobs(job_id, user_id, doc_id, status, created_at) VALUES (?,?,?,?,?)",
                (record.job_id, record.user_id, record.doc_id, record.status, record.created_at),
            )
            self._conn.commit()
        return record

    def get_job(self, user_id: str, job_id: str) -> Optional[JobRecord]:
        """Tenant-scoped job lookup."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM jobs WHERE user_id=? AND job_id=?",
                (user_id, job_id),
            ).fetchone()
        return _row_to_job(row) if row else None

    def get_job_by_id(self, job_id: str) -> Optional[JobRecord]:
        """Internal lookup without user scope (used by job worker thread)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM jobs WHERE job_id=?", (job_id,)
            ).fetchone()
        return _row_to_job(row) if row else None

    def list_jobs(self, user_id: str) -> List[JobRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE user_id=? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [_row_to_job(r) for r in rows]

    def list_resumable_jobs(self) -> List[JobRecord]:
        """Return all jobs in 'queued' or 'running' state (for crash recovery)."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM jobs WHERE status IN ('queued', 'running')"
            ).fetchall()
        return [_row_to_job(r) for r in rows]

    def update_job(
        self,
        job_id: str,
        status: str,
        checkpoint: Optional[Dict] = None,
        error: Optional[str] = None,
    ) -> None:
        completed_at = _now() if status in ("complete", "failed") else None
        checkpoint_json = json.dumps(checkpoint) if checkpoint is not None else None
        with self._lock:
            self._conn.execute(
                """
                UPDATE jobs
                SET status=?, completed_at=?, error_msg=?, checkpoint_json=?
                WHERE job_id=?
                """,
                (status, completed_at, error, checkpoint_json, job_id),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Audit log (reads scoped to user_id)
    # ------------------------------------------------------------------

    def log_action(
        self,
        user_id: str,
        request_id: str,
        action_type: str,
        status: str,
        output_hash: str,
    ) -> AuditRecord:
        record = AuditRecord(
            audit_id=str(uuid.uuid4()),
            user_id=user_id,
            request_id=request_id,
            action_type=action_type,
            status=status,
            output_hash=output_hash,
            created_at=_now(),
        )
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO audit_log
                    (audit_id, user_id, request_id, action_type, status, output_hash, created_at)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    record.audit_id,
                    record.user_id,
                    record.request_id,
                    record.action_type,
                    record.status,
                    record.output_hash,
                    record.created_at,
                ),
            )
            self._conn.commit()
        return record

    def close(self) -> None:
        """Close the underlying SQLite connection (required on Windows before deleting the file)."""
        with self._lock:
            self._conn.close()

    def get_audit_trail(self, user_id: str) -> List[AuditRecord]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM audit_log WHERE user_id=? ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        return [
            AuditRecord(
                audit_id=r["audit_id"],
                user_id=r["user_id"],
                request_id=r["request_id"],
                action_type=r["action_type"],
                status=r["status"],
                output_hash=r["output_hash"],
                created_at=r["created_at"],
            )
            for r in rows
        ]
