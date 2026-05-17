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
    is_global: bool = False


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
    metadata_json TEXT NOT NULL DEFAULT '{}',
    is_global     INTEGER NOT NULL DEFAULT 0
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

CREATE TABLE IF NOT EXISTS file_uploads (
    doc_id    TEXT PRIMARY KEY,
    file_path TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    doc_id         TEXT PRIMARY KEY,
    chunk_set_json TEXT NOT NULL,
    created_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graphs (
    doc_id     TEXT PRIMARY KEY,
    graph_json TEXT NOT NULL,
    created_at TEXT NOT NULL
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
        is_global=bool(row["is_global"]) if "is_global" in row.keys() else False,
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
            # Migration: add is_global column to existing DBs that predate the schema change
            try:
                self._conn.execute("ALTER TABLE documents ADD COLUMN is_global INTEGER NOT NULL DEFAULT 0")
                self._conn.commit()
            except Exception:
                pass  # column already exists
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

    def create_global_document(
        self,
        filename: str,
        metadata: Optional[Dict] = None,
    ) -> DocumentRecord:
        """Create an admin-uploaded document visible to all users (is_global=1)."""
        record = DocumentRecord(
            doc_id=str(uuid.uuid4()),
            user_id="admin",
            filename=filename,
            status="uploaded",
            created_at=_now(),
            metadata=metadata or {},
            is_global=True,
        )
        with self._lock:
            self._conn.execute(
                "INSERT INTO documents(doc_id, user_id, filename, status, created_at, metadata_json, is_global)"
                " VALUES (?,?,?,?,?,?,?)",
                (
                    record.doc_id,
                    record.user_id,
                    record.filename,
                    record.status,
                    record.created_at,
                    json.dumps(record.metadata),
                    1,
                ),
            )
            self._conn.commit()
        return record

    def get_all_documents(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> List[DocumentRecord]:
        """Return all documents across all users (admin view)."""
        if status_filter:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM documents WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status_filter, limit, offset),
                ).fetchall()
        else:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM documents ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [_row_to_doc(r) for r in rows]

    def get_document_by_id(self, doc_id: str) -> Optional[DocumentRecord]:
        """Lookup a document without user scope (admin use)."""
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM documents WHERE doc_id=?", (doc_id,)
            ).fetchone()
        return _row_to_doc(row) if row else None

    def delete_document(self, doc_id: str) -> bool:
        """Delete a document and all its related records. Returns True if found."""
        with self._lock:
            cur = self._conn.execute("DELETE FROM documents WHERE doc_id=?", (doc_id,))
            self._conn.execute("DELETE FROM file_uploads WHERE doc_id=?", (doc_id,))
            self._conn.execute("DELETE FROM chunks WHERE doc_id=?", (doc_id,))
            self._conn.execute("DELETE FROM graphs WHERE doc_id=?", (doc_id,))
            self._conn.execute("DELETE FROM jobs WHERE doc_id=?", (doc_id,))
            self._conn.commit()
        return cur.rowcount > 0

    def list_all_jobs(
        self,
        limit: int = 100,
        offset: int = 0,
        status_filter: Optional[str] = None,
    ) -> List[JobRecord]:
        """Return all jobs across all users (admin view)."""
        if status_filter:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM jobs WHERE status=? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (status_filter, limit, offset),
                ).fetchall()
        else:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ? OFFSET ?",
                    (limit, offset),
                ).fetchall()
        return [_row_to_job(r) for r in rows]

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

    # ------------------------------------------------------------------
    # File uploads (path registry)
    # ------------------------------------------------------------------

    def save_file_path(self, doc_id: str, file_path: str) -> None:
        """Register the on-disk path for an uploaded document."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO file_uploads(doc_id, file_path) VALUES (?,?)",
                (doc_id, file_path),
            )
            self._conn.commit()

    def get_file_path(self, doc_id: str) -> Optional[str]:
        """Return the on-disk path for a document, or None if not registered."""
        with self._lock:
            row = self._conn.execute(
                "SELECT file_path FROM file_uploads WHERE doc_id=?", (doc_id,)
            ).fetchone()
        return row["file_path"] if row else None

    # ------------------------------------------------------------------
    # Chunk sets (post-pipeline artifacts)
    # ------------------------------------------------------------------

    def save_chunk_set(self, doc_id: str, chunk_set_json: str) -> None:
        """Persist the serialised ChunkSet for a document."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO chunks(doc_id, chunk_set_json, created_at) VALUES (?,?,?)",
                (doc_id, chunk_set_json, _now()),
            )
            self._conn.commit()

    def load_chunk_set_json(self, doc_id: str) -> Optional[str]:
        """Return the raw JSON string of a document's ChunkSet, or None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT chunk_set_json FROM chunks WHERE doc_id=?", (doc_id,)
            ).fetchone()
        return row["chunk_set_json"] if row else None

    # ------------------------------------------------------------------
    # Graphs (post-pipeline artifacts)
    # ------------------------------------------------------------------

    def save_graph(self, doc_id: str, graph_json: str) -> None:
        """Persist the serialised GraphSubgraph for a document."""
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO graphs(doc_id, graph_json, created_at) VALUES (?,?,?)",
                (doc_id, graph_json, _now()),
            )
            self._conn.commit()

    def load_graph_json(self, doc_id: str) -> Optional[str]:
        """Return the raw JSON string of a document's GraphSubgraph, or None."""
        with self._lock:
            row = self._conn.execute(
                "SELECT graph_json FROM graphs WHERE doc_id=?", (doc_id,)
            ).fetchone()
        return row["graph_json"] if row else None

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
