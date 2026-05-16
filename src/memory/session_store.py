"""
SessionStore — MongoDB-backed multi-turn legal conversation memory.

Collections:
  conversation_sessions  — SessionContext documents (24h TTL on last_active)
  reasoning_traces       — per-query ReasoningTrace documents
  session_context        — lightweight per-turn context cache (TTL via expires_at)

Design goals:
  - Preserve legal domain context across turns (dispute continuity)
  - Reuse previous retrieval results to reduce redundant MongoDB calls
  - Store reasoning traces for debugging and competition demos
  - Automatic session expiry (24h TTL via MongoDB index)
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from src.mongodb.client import get_db

logger = logging.getLogger(__name__)

_TTL_HOURS = 24
_TTL_SECONDS = _TTL_HOURS * 3600


# ---------------------------------------------------------------------------
# SessionContext — in-memory representation of one conversation session
# ---------------------------------------------------------------------------


@dataclass
class SessionContext:
    session_id: str
    user_id: str
    created_at: str
    last_active: str
    history: List[Dict[str, Any]]          # [{query, trace_id, law_type, result_summary, ts}]
    law_type_preferences: List[str]        # top law_types from history
    last_query_plan: Optional[Dict[str, Any]]  # serialized QueryPlan from last turn
    metadata: Dict[str, Any]


# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------


class SessionStore:
    """
    Conversation and legal context memory backed by MongoDB.

    Thread-safe: pymongo Collection objects are thread-safe.
    """

    def __init__(self) -> None:
        db = get_db()
        self.sessions = db["conversation_sessions"]
        self.traces = db["reasoning_traces"]
        self.context_cache = db["session_context"]

    def setup_indexes(self) -> None:
        """
        Create all required indexes including TTL indexes.
        Safe to call multiple times (idempotent).
        """
        try:
            # conversation_sessions: TTL on last_active (24h)
            self.sessions.create_index(
                [("last_active", 1)],
                expireAfterSeconds=_TTL_SECONDS,
                name="session_ttl_idx",
            )
            self.sessions.create_index([("session_id", 1)], unique=True, name="session_id_unique")
            self.sessions.create_index([("user_id", 1)], name="session_user_idx")

            # reasoning_traces
            self.traces.create_index([("trace_id", 1)], unique=True, name="trace_id_unique")
            self.traces.create_index([("session_id", 1)], name="trace_session_idx")
            self.traces.create_index(
                [("user_id", 1), ("created_at", -1)],
                name="trace_user_time_idx",
            )

            # session_context: TTL via expires_at field
            self.context_cache.create_index(
                [("expires_at", 1)],
                expireAfterSeconds=0,
                name="context_cache_ttl_idx",
            )
            self.context_cache.create_index(
                [("session_id", 1)], unique=True, name="context_session_unique"
            )
            logger.info("SessionStore indexes created/verified.")
        except Exception as exc:
            logger.warning("SessionStore index setup: %s", exc)

    # ── Session CRUD ──────────────────────────────────────────────────────────

    def load_context(self, session_id: str, user_id: str) -> SessionContext:
        """
        Load an existing session or create a fresh empty one.
        Updates last_active to now. Never raises.
        """
        try:
            doc = self.sessions.find_one({"session_id": session_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("load_context find failed: %s", exc)
            doc = None

        now = _now()
        if doc and doc.get("user_id") == user_id:
            # Update last_active in place
            try:
                self.sessions.update_one(
                    {"session_id": session_id},
                    {"$set": {"last_active": now}},
                )
            except Exception:
                pass
            return SessionContext(
                session_id=doc["session_id"],
                user_id=doc["user_id"],
                created_at=doc.get("created_at", now),
                last_active=now,
                history=doc.get("history", []),
                law_type_preferences=doc.get("law_type_preferences", []),
                last_query_plan=doc.get("last_query_plan"),
                metadata=doc.get("metadata", {}),
            )

        # New session
        return SessionContext(
            session_id=session_id,
            user_id=user_id,
            created_at=now,
            last_active=now,
            history=[],
            law_type_preferences=[],
            last_query_plan=None,
            metadata={},
        )

    def save_context(
        self,
        context: SessionContext,
        result_summary: Dict[str, Any],
        trace_id: str,
        query_plan: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Append a turn to the session and persist to MongoDB."""
        now = _now()
        turn_entry = {
            "query": result_summary.get("query", "")[:300],
            "trace_id": trace_id,
            "law_type": result_summary.get("detected_domain", ""),
            "result_summary": {k: v for k, v in result_summary.items() if k != "query"},
            "timestamp": now,
        }

        # Update law_type preferences (add domain if not already at top)
        domain = result_summary.get("detected_domain", "")
        prefs = list(context.law_type_preferences)
        if domain and domain not in prefs[:3]:
            prefs.insert(0, domain)
            prefs = prefs[:10]

        try:
            self.sessions.update_one(
                {"session_id": context.session_id},
                {
                    "$set": {
                        "user_id": context.user_id,
                        "last_active": now,
                        "law_type_preferences": prefs,
                        "last_query_plan": query_plan,
                        "metadata": context.metadata,
                    },
                    "$setOnInsert": {"created_at": context.created_at},
                    "$push": {
                        "history": {
                            "$each": [turn_entry],
                            "$slice": -50,  # keep last 50 turns
                        }
                    },
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("save_context upsert failed: %s", exc)

    # ── Reasoning trace storage ───────────────────────────────────────────────

    def save_trace(self, trace: Any) -> None:
        """Persist a ReasoningTrace (or dict) to MongoDB."""
        try:
            trace_dict = trace.to_dict() if hasattr(trace, "to_dict") else dict(trace)
            trace_dict["saved_at"] = _now()
            self.traces.insert_one(trace_dict)
        except Exception as exc:
            logger.warning("save_trace failed: %s", exc)

    def get_trace(self, trace_id: str) -> Optional[Dict[str, Any]]:
        """Return a full reasoning trace by trace_id."""
        try:
            return self.traces.find_one({"trace_id": trace_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("get_trace failed: %s", exc)
            return None

    def get_session_traces(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return recent traces for a session (without bulky stage data for list view)."""
        try:
            return list(
                self.traces.find(
                    {"session_id": session_id},
                    {"_id": 0, "stages": 0},
                ).sort("created_at", -1).limit(limit)
            )
        except Exception as exc:
            logger.warning("get_session_traces failed: %s", exc)
            return []

    # ── Session retrieval ─────────────────────────────────────────────────────

    def get_session_history(
        self, session_id: str, limit: int = 20
    ) -> Optional[Dict[str, Any]]:
        """Return the session document with history (last N turns)."""
        try:
            doc = self.sessions.find_one({"session_id": session_id}, {"_id": 0})
            if doc:
                doc["history"] = doc.get("history", [])[-limit:]
            return doc
        except Exception as exc:
            logger.warning("get_session_history failed: %s", exc)
            return None

    def get_user_sessions(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return recent active sessions for a user (metadata only, no history)."""
        try:
            return list(
                self.sessions.find(
                    {"user_id": user_id},
                    {"_id": 0, "history": 0},
                ).sort("last_active", -1).limit(limit)
            )
        except Exception as exc:
            logger.warning("get_user_sessions failed: %s", exc)
            return []

    # ── Context cache ─────────────────────────────────────────────────────────

    def cache_retrieval_context(
        self,
        session_id: str,
        law_type: str,
        top_chunk_ids: List[str],
        top_case_ids: List[str],
        query_plan_dict: Dict[str, Any],
    ) -> None:
        """Cache the retrieval context for a session to avoid redundant retrieval."""
        expires_at = datetime.now(timezone.utc) + timedelta(hours=_TTL_HOURS)
        try:
            self.context_cache.update_one(
                {"session_id": session_id},
                {
                    "$set": {
                        "session_id": session_id,
                        "law_type": law_type,
                        "top_chunk_ids": top_chunk_ids[:20],
                        "top_case_ids": top_case_ids[:10],
                        "query_plan": query_plan_dict,
                        "updated_at": _now(),
                        "expires_at": expires_at,
                    }
                },
                upsert=True,
            )
        except Exception as exc:
            logger.warning("cache_retrieval_context failed: %s", exc)

    def get_cached_retrieval_context(
        self, session_id: str
    ) -> Optional[Dict[str, Any]]:
        """Retrieve cached context. Returns None if expired or not found."""
        try:
            return self.context_cache.find_one({"session_id": session_id}, {"_id": 0})
        except Exception as exc:
            logger.warning("get_cached_retrieval_context failed: %s", exc)
            return None


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
