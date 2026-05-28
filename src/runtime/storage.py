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
from typing import Any, Dict, List, Optional


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

CREATE TABLE IF NOT EXISTS checklist_progress (
    user_id       TEXT NOT NULL,
    checklist_id  TEXT NOT NULL,
    checked_json  TEXT NOT NULL DEFAULT '[]',
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (user_id, checklist_id)
);

CREATE TABLE IF NOT EXISTS analysis_history (
    item_id   TEXT NOT NULL,
    user_id   TEXT NOT NULL,
    type      TEXT NOT NULL,
    title     TEXT NOT NULL,
    domain    TEXT,
    summary   TEXT NOT NULL DEFAULT '',
    data_json TEXT NOT NULL DEFAULT '{}',
    saved_at  TEXT NOT NULL,
    PRIMARY KEY (user_id, item_id)
);

CREATE TABLE IF NOT EXISTS interactions (
    interaction_id TEXT PRIMARY KEY,
    user_id        TEXT NOT NULL,
    doc_id         TEXT NOT NULL DEFAULT '',
    action_type    TEXT NOT NULL,
    context_json   TEXT NOT NULL DEFAULT '{}',
    chunk_id       TEXT,
    timestamp      TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_interactions_user_time
    ON interactions(user_id, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_interactions_action
    ON interactions(action_type);

CREATE TABLE IF NOT EXISTS conversation_sessions (
    session_id    TEXT NOT NULL,
    user_id       TEXT NOT NULL,
    title         TEXT NOT NULL,
    domain        TEXT,
    turns_json    TEXT NOT NULL DEFAULT '[]',
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at    TEXT NOT NULL,
    last_active   TEXT NOT NULL,
    PRIMARY KEY (user_id, session_id)
);

CREATE INDEX IF NOT EXISTS idx_conversation_user_active
    ON conversation_sessions(user_id, last_active DESC);

CREATE TABLE IF NOT EXISTS community_case_patterns (
    pattern_id           TEXT PRIMARY KEY,
    summary              TEXT NOT NULL,
    legal_domain         TEXT NOT NULL DEFAULT 'general',
    user_goal_json       TEXT NOT NULL DEFAULT '[]',
    resolution_summary   TEXT NOT NULL DEFAULT '',
    recommended_steps_json TEXT NOT NULL DEFAULT '[]',
    citations_json       TEXT NOT NULL DEFAULT '[]',
    tags_json            TEXT NOT NULL DEFAULT '[]',
    source_user_segment  TEXT NOT NULL DEFAULT '',
    impressions          INTEGER NOT NULL DEFAULT 0,
    clicks               INTEGER NOT NULL DEFAULT 0,
    saves                INTEGER NOT NULL DEFAULT 0,
    useful               INTEGER NOT NULL DEFAULT 0,
    not_useful           INTEGER NOT NULL DEFAULT 0,
    created_at           TEXT NOT NULL,
    last_seen_at         TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_community_domain
    ON community_case_patterns(legal_domain, useful DESC);
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
            except sqlite3.OperationalError:
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

    # ------------------------------------------------------------------
    # Checklist progress (local fallback when MongoDB is unavailable)
    # ------------------------------------------------------------------

    def get_checklist_progress(self, user_id: str, checklist_id: str) -> List[str]:
        """Return saved checklist item keys for a user/checklist pair."""
        with self._lock:
            row = self._conn.execute(
                """
                SELECT checked_json
                FROM checklist_progress
                WHERE user_id=? AND checklist_id=?
                """,
                (user_id, checklist_id),
            ).fetchone()
        if row is None:
            return []
        try:
            value = json.loads(row["checked_json"])
        except json.JSONDecodeError:
            return []
        return value if isinstance(value, list) else []

    def save_checklist_progress(
        self,
        user_id: str,
        checklist_id: str,
        checked_items: List[str],
    ) -> None:
        """Persist saved checklist item keys for a user/checklist pair."""
        unique_items = list(dict.fromkeys(str(item) for item in checked_items))
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO checklist_progress(user_id, checklist_id, checked_json, updated_at)
                VALUES (?,?,?,?)
                ON CONFLICT(user_id, checklist_id) DO UPDATE SET
                    checked_json=excluded.checked_json,
                    updated_at=excluded.updated_at
                """,
                (user_id, checklist_id, json.dumps(unique_items), _now()),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Analysis history (backend-persisted, user-scoped)
    # ------------------------------------------------------------------

    def save_analysis_history(
        self,
        user_id: str,
        item_id: str,
        type_: str,
        title: str,
        domain: Optional[str],
        summary: str,
        data_json: str,
        saved_at: str,
    ) -> None:
        """Upsert one analysis history entry."""
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO analysis_history(item_id, user_id, type, title, domain, summary, data_json, saved_at)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id, item_id) DO UPDATE SET
                    title=excluded.title,
                    domain=excluded.domain,
                    summary=excluded.summary,
                    data_json=excluded.data_json,
                    saved_at=excluded.saved_at
                """,
                (item_id, user_id, type_, title, domain, summary, data_json, saved_at),
            )
            self._conn.commit()

    def list_analysis_history(
        self,
        user_id: str,
        type_filter: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict]:
        """Return analysis history for a user, newest first."""
        if type_filter:
            with self._lock:
                rows = self._conn.execute(
                    """
                    SELECT item_id, type, title, domain, summary, data_json, saved_at
                    FROM analysis_history
                    WHERE user_id=? AND type=?
                    ORDER BY saved_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, type_filter, limit, offset),
                ).fetchall()
        else:
            with self._lock:
                rows = self._conn.execute(
                    """
                    SELECT item_id, type, title, domain, summary, data_json, saved_at
                    FROM analysis_history
                    WHERE user_id=?
                    ORDER BY saved_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, limit, offset),
                ).fetchall()
        result = []
        for r in rows:
            try:
                data = json.loads(r["data_json"])
            except (json.JSONDecodeError, TypeError):
                data = {}
            result.append({
                "id": r["item_id"],
                "type": r["type"],
                "title": r["title"],
                "domain": r["domain"],
                "summary": r["summary"],
                "data": data,
                "savedAt": r["saved_at"],
            })
        return result

    def delete_analysis_history_item(self, user_id: str, item_id: str) -> bool:
        """Delete one history item. Returns True if it existed."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM analysis_history WHERE user_id=? AND item_id=?",
                (user_id, item_id),
            )
            self._conn.commit()
        return cur.rowcount > 0

    def clear_analysis_history(self, user_id: str) -> int:
        """Delete all history for a user. Returns number of rows deleted."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM analysis_history WHERE user_id=?", (user_id,)
            )
            self._conn.commit()
        return cur.rowcount

    # ------------------------------------------------------------------
    # Interaction log (SQLite fallback for behavior recommendations)
    # ------------------------------------------------------------------

    def log_interaction(
        self,
        user_id: str,
        doc_id: str,
        action_type: str,
        context: Optional[Dict] = None,
        chunk_id: Optional[str] = None,
    ) -> str:
        """Record one user gesture/action for local behavior recommendations."""
        interaction_id = str(uuid.uuid4())
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO interactions(interaction_id, user_id, doc_id, action_type, context_json, chunk_id, timestamp)
                VALUES (?,?,?,?,?,?,?)
                """,
                (
                    interaction_id,
                    user_id,
                    doc_id or "",
                    action_type,
                    json.dumps(context or {}, ensure_ascii=False),
                    chunk_id,
                    _now(),
                ),
            )
            self._conn.commit()
        return interaction_id

    def get_user_interaction_history(
        self,
        user_id: str,
        days: int = 60,
        limit: int = 200,
    ) -> List[Dict]:
        """Return recent interactions for one user, newest first."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT doc_id, action_type, context_json, chunk_id, timestamp
                FROM interactions
                WHERE user_id=?
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        cutoff = datetime.fromtimestamp(0, timezone.utc)
        try:
            from datetime import timedelta
            cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        except Exception:
            pass

        result = []
        for row in rows:
            ts = row["timestamp"]
            try:
                parsed = datetime.fromisoformat(ts)
                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)
                if parsed < cutoff:
                    continue
            except (TypeError, ValueError):
                pass
            try:
                context = json.loads(row["context_json"])
            except (json.JSONDecodeError, TypeError):
                context = {}
            result.append({
                "doc_id": row["doc_id"],
                "action_type": row["action_type"],
                "context": context,
                "chunk_id": row["chunk_id"],
                "timestamp": ts,
            })
        return result

    def get_user_action_frequency(self, user_id: str) -> Dict[str, int]:
        """Return action_type -> count for a user."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT action_type, COUNT(*) AS count
                FROM interactions
                WHERE user_id=?
                GROUP BY action_type
                """,
                (user_id,),
            ).fetchall()
        return {row["action_type"]: int(row["count"]) for row in rows}

    def get_user_active_hours(self, user_id: str) -> List[int]:
        """Return hours of day when the user is most active."""
        history = self.get_user_interaction_history(user_id, days=90, limit=500)
        counts: Dict[int, int] = {}
        for item in history:
            try:
                hour = datetime.fromisoformat(item["timestamp"]).hour
            except (TypeError, ValueError):
                continue
            counts[hour] = counts.get(hour, 0) + 1
        return [hour for hour, _ in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))]

    def get_user_law_types_since(self, user_id: str, days: int = 7) -> List[str]:
        """Return distinct law_type values from recent interactions."""
        history = self.get_user_interaction_history(user_id, days=days, limit=300)
        values = []
        for item in history:
            law_type = (item.get("context") or {}).get("law_type")
            if law_type and law_type not in values:
                values.append(law_type)
        return values

    def get_trending_law_types(self, limit: int = 5) -> List[str]:
        """Return globally frequent law_type values from local interactions."""
        with self._lock:
            rows = self._conn.execute(
                "SELECT context_json FROM interactions ORDER BY timestamp DESC LIMIT 1000"
            ).fetchall()
        counts: Dict[str, int] = {}
        for row in rows:
            try:
                context = json.loads(row["context_json"])
            except (json.JSONDecodeError, TypeError):
                continue
            law_type = context.get("law_type")
            if law_type:
                counts[law_type] = counts.get(law_type, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [law_type for law_type, _ in ranked[:limit]]

    def get_user_action_bigrams(self, user_id: str, limit: int = 20) -> List[Dict]:
        """Return consecutive action pairs from the user's local interaction log."""
        history = list(reversed(self.get_user_interaction_history(user_id, days=90, limit=500)))
        counts: Dict[tuple[str, str], int] = {}
        for first, second in zip(history, history[1:]):
            key = (first.get("action_type", ""), second.get("action_type", ""))
            if key[0] and key[1]:
                counts[key] = counts.get(key, 0) + 1
        ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
        return [
            {"first_action": first, "second_action": second, "count": count}
            for (first, second), count in ranked[:limit]
        ]

    def find_peer_users(self, user_id: str, top_domains: List[str], limit: int = 20) -> List[str]:
        """SQLite fallback: peer discovery is unavailable locally."""
        return []

    def get_user_viewed_docs(self, user_id: str, limit: int = 100) -> List[str]:
        """Return documents viewed by a user."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT DISTINCT doc_id
                FROM interactions
                WHERE user_id=? AND doc_id != ''
                ORDER BY timestamp DESC, rowid DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        return [row["doc_id"] for row in rows]

    def get_trending_content_for_peers(
        self,
        peer_user_ids: List[str],
        exclude_doc_ids: List[str],
        days: int = 14,
        limit: int = 10,
    ) -> List[Dict]:
        """SQLite fallback: no peer graph, so return no peer content."""
        return []

    # ------------------------------------------------------------------
    # Community case patterns (Phase 23 — SQLite fallback)
    # ------------------------------------------------------------------

    def save_community_case_pattern(
        self,
        pattern_id: str,
        summary: str,
        legal_domain: str,
        user_goal: List[str],
        resolution_summary: str,
        recommended_steps: List[str],
        citations: List[str],
        tags: List[str],
        source_user_segment: str = "",
    ) -> bool:
        """Upsert a community case pattern. Returns True if newly inserted."""
        now = _now()
        with self._lock:
            existing = self._conn.execute(
                "SELECT pattern_id FROM community_case_patterns WHERE pattern_id=?",
                (pattern_id,),
            ).fetchone()
            if existing:
                self._conn.execute(
                    "UPDATE community_case_patterns SET last_seen_at=?, impressions=impressions+1 WHERE pattern_id=?",
                    (now, pattern_id),
                )
                self._conn.commit()
                return False
            self._conn.execute(
                """
                INSERT INTO community_case_patterns(
                    pattern_id, summary, legal_domain, user_goal_json,
                    resolution_summary, recommended_steps_json,
                    citations_json, tags_json, source_user_segment,
                    impressions, clicks, saves, useful, not_useful,
                    created_at, last_seen_at
                ) VALUES (?,?,?,?,?,?,?,?,?,1,0,0,0,0,?,?)
                """,
                (
                    pattern_id, summary, legal_domain,
                    json.dumps(user_goal, ensure_ascii=False),
                    resolution_summary,
                    json.dumps(recommended_steps, ensure_ascii=False),
                    json.dumps(citations, ensure_ascii=False),
                    json.dumps(tags, ensure_ascii=False),
                    source_user_segment,
                    now, now,
                ),
            )
            self._conn.commit()
            return True

    def search_community_case_patterns(
        self,
        query: str,
        domain: Optional[str] = None,
        limit: int = 5,
    ) -> List[Dict]:
        """Keyword search over community case patterns."""
        import re
        keywords = [w for w in re.findall(r"[\wÀ-ỹ]+", query.lower()) if len(w) >= 3][:8]
        if not keywords:
            with self._lock:
                rows = self._conn.execute(
                    "SELECT * FROM community_case_patterns ORDER BY useful DESC, impressions DESC LIMIT ?",
                    (limit,),
                ).fetchall()
        else:
            like_clauses = " OR ".join(
                ["summary LIKE ? OR resolution_summary LIKE ? OR tags_json LIKE ?"] * len(keywords)
            )
            params: List = []
            for kw in keywords:
                params.extend([f"%{kw}%", f"%{kw}%", f"%{kw}%"])
            if domain and domain != "general":
                like_clauses = f"({like_clauses}) AND legal_domain=?"
                params.append(domain)
            params.append(limit)
            with self._lock:
                rows = self._conn.execute(
                    f"SELECT * FROM community_case_patterns WHERE {like_clauses} ORDER BY useful DESC LIMIT ?",
                    params,
                ).fetchall()

        result = []
        for row in rows:
            d: Dict[str, Any] = dict(row)
            for json_col, out_key in [
                ("user_goal_json", "user_goal"),
                ("recommended_steps_json", "recommended_steps"),
                ("citations_json", "citations"),
                ("tags_json", "tags"),
            ]:
                try:
                    d[out_key] = json.loads(d.pop(json_col, "[]"))
                except (json.JSONDecodeError, TypeError):
                    d[out_key] = []
            d["popularity"] = {
                "impressions": d.pop("impressions", 0),
                "clicks": d.pop("clicks", 0),
                "saves": d.pop("saves", 0),
                "useful": d.pop("useful", 0),
                "not_useful": d.pop("not_useful", 0),
            }
            result.append(d)
        return result

    def increment_community_case_signal(
        self,
        pattern_id: str,
        signal: str,
    ) -> None:
        """Increment a popularity counter for a community pattern."""
        valid_signals = {"clicks", "saves", "useful", "not_useful", "impressions"}
        if signal not in valid_signals:
            return
        now = _now()
        with self._lock:
            self._conn.execute(
                f"UPDATE community_case_patterns SET {signal}={signal}+1, last_seen_at=? WHERE pattern_id=?",
                (now, pattern_id),
            )
            self._conn.commit()

    # ------------------------------------------------------------------
    # Conversation sessions (backend-persisted chat history)
    # ------------------------------------------------------------------

    def save_conversation_session(
        self,
        user_id: str,
        session_id: str,
        title: str,
        domain: Optional[str],
        turns: List[Dict],
        metadata: Optional[Dict] = None,
    ) -> None:
        """Upsert a full conversation session for a user."""
        now = _now()
        with self._lock:
            existing = self._conn.execute(
                "SELECT created_at FROM conversation_sessions WHERE user_id=? AND session_id=?",
                (user_id, session_id),
            ).fetchone()
            created_at = existing["created_at"] if existing else now
            self._conn.execute(
                """
                INSERT INTO conversation_sessions(session_id, user_id, title, domain, turns_json, metadata_json, created_at, last_active)
                VALUES (?,?,?,?,?,?,?,?)
                ON CONFLICT(user_id, session_id) DO UPDATE SET
                    title=excluded.title,
                    domain=excluded.domain,
                    turns_json=excluded.turns_json,
                    metadata_json=excluded.metadata_json,
                    last_active=excluded.last_active
                """,
                (
                    session_id,
                    user_id,
                    title[:200],
                    domain,
                    json.dumps(turns[-80:], ensure_ascii=False),
                    json.dumps(metadata or {}, ensure_ascii=False),
                    created_at,
                    now,
                ),
            )
            self._conn.commit()

    def list_conversation_sessions(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Return recent conversation session summaries for a user."""
        with self._lock:
            rows = self._conn.execute(
                """
                SELECT session_id, title, domain, turns_json, metadata_json, created_at, last_active
                FROM conversation_sessions
                WHERE user_id=?
                ORDER BY last_active DESC
                LIMIT ?
                """,
                (user_id, limit),
            ).fetchall()
        result = []
        for row in rows:
            try:
                turns = json.loads(row["turns_json"])
            except (json.JSONDecodeError, TypeError):
                turns = []
            result.append({
                "id": row["session_id"],
                "title": row["title"],
                "domain": row["domain"],
                "createdAt": row["created_at"],
                "lastActive": row["last_active"],
                "turnCount": len(turns) if isinstance(turns, list) else 0,
                "turns": turns,
            })
        return result

    def get_conversation_session(self, user_id: str, session_id: str) -> Optional[Dict]:
        """Return one full conversation session for a user."""
        with self._lock:
            row = self._conn.execute(
                """
                SELECT session_id, title, domain, turns_json, metadata_json, created_at, last_active
                FROM conversation_sessions
                WHERE user_id=? AND session_id=?
                """,
                (user_id, session_id),
            ).fetchone()
        if row is None:
            return None
        try:
            turns = json.loads(row["turns_json"])
        except (json.JSONDecodeError, TypeError):
            turns = []
        try:
            metadata = json.loads(row["metadata_json"])
        except (json.JSONDecodeError, TypeError):
            metadata = {}
        return {
            "id": row["session_id"],
            "title": row["title"],
            "domain": row["domain"],
            "turns": turns,
            "metadata": metadata,
            "createdAt": row["created_at"],
            "lastActive": row["last_active"],
        }

    def delete_conversation_session(self, user_id: str, session_id: str) -> bool:
        """Delete one conversation session."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM conversation_sessions WHERE user_id=? AND session_id=?",
                (user_id, session_id),
            )
            self._conn.commit()
        return cur.rowcount > 0

    def clear_conversation_sessions(self, user_id: str) -> int:
        """Delete all conversation sessions for a user."""
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM conversation_sessions WHERE user_id=?",
                (user_id,),
            )
            self._conn.commit()
        return cur.rowcount

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
