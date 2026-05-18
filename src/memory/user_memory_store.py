"""
UserMemoryStore — persistent cross-session memory for personalization.

Unlike SessionStore (24h TTL), this collection never expires.
Stores personal facts the user reveals during conversations plus
compressed situation summaries (last 20 sessions).

Collection: user_memory
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.mongodb.client import get_db

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class PersonalInfo:
    name: Optional[str] = None
    age: Optional[int] = None
    occupation: Optional[str] = None
    location: Optional[str] = None
    notes: Optional[str] = None       # free-form: anything the user wants AI to remember


@dataclass
class SituationRecord:
    session_id: str
    date: str                          # YYYY-MM-DD
    domain: str                        # law domain code
    summary: str                       # 1-sentence description (≤ 150 chars)
    resolved: bool = False


@dataclass
class UserMemory:
    user_id: str
    personal_info: PersonalInfo = field(default_factory=PersonalInfo)
    situation_summaries: List[SituationRecord] = field(default_factory=list)
    updated_at: str = field(default_factory=_now)

    @property
    def has_personal_info(self) -> bool:
        pi = self.personal_info
        return any([pi.name, pi.age, pi.occupation, pi.location, pi.notes])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "personal_info": asdict(self.personal_info),
            "situation_summaries": [asdict(s) for s in self.situation_summaries],
            "updated_at": self.updated_at,
        }


# ---------------------------------------------------------------------------
# Store
# ---------------------------------------------------------------------------


class UserMemoryStore:
    """
    CRUD for user_memory collection.
    Safe to construct multiple times — all share the same pymongo connection pool.
    """

    def __init__(self) -> None:
        db = get_db()
        self.col = db["user_memory"]
        self._setup_indexes()

    def _setup_indexes(self) -> None:
        try:
            self.col.create_index("user_id", unique=True, background=True)
        except Exception as exc:
            logger.debug("user_memory index: %s", exc)

    # ── Read ──────────────────────────────────────────────────────────────────

    def get(self, user_id: str) -> UserMemory:
        doc = self.col.find_one({"user_id": user_id}, {"_id": 0})
        if not doc:
            return UserMemory(user_id=user_id)
        pi_raw = doc.get("personal_info") or {}
        return UserMemory(
            user_id=user_id,
            personal_info=PersonalInfo(
                name=pi_raw.get("name"),
                age=pi_raw.get("age"),
                occupation=pi_raw.get("occupation"),
                location=pi_raw.get("location"),
                notes=pi_raw.get("notes"),
            ),
            situation_summaries=[
                SituationRecord(**s)
                for s in (doc.get("situation_summaries") or [])
            ],
            updated_at=doc.get("updated_at", _now()),
        )

    # ── Write ─────────────────────────────────────────────────────────────────

    def save(self, memory: UserMemory) -> None:
        memory.updated_at = _now()
        self.col.update_one(
            {"user_id": memory.user_id},
            {"$set": memory.to_dict()},
            upsert=True,
        )

    def update_personal_info(self, user_id: str, updates: Dict[str, Any]) -> None:
        """Partial upsert — only sets non-None values.  Clears a field by passing None."""
        set_ops: Dict[str, Any] = {"updated_at": _now()}
        unset_ops: Dict[str, int] = {}
        for k, v in updates.items():
            if v is not None:
                set_ops[f"personal_info.{k}"] = v
            else:
                unset_ops[f"personal_info.{k}"] = 1
        op: Dict[str, Any] = {"$set": set_ops}
        if unset_ops:
            op["$unset"] = unset_ops
        self.col.update_one({"user_id": user_id}, op, upsert=True)

    def upsert_situation_summary(self, user_id: str, record: SituationRecord) -> None:
        """Add or replace summary for this session_id; keep last 20."""
        # Remove existing entry for same session_id to avoid duplicates
        self.col.update_one(
            {"user_id": user_id},
            {"$pull": {"situation_summaries": {"session_id": record.session_id}}},
            upsert=True,
        )
        self.col.update_one(
            {"user_id": user_id},
            {
                "$push": {
                    "situation_summaries": {
                        "$each": [asdict(record)],
                        "$slice": -20,
                    }
                },
                "$set": {"updated_at": _now()},
            },
            upsert=True,
        )

    def mark_situation_resolved(self, user_id: str, session_id: str) -> None:
        self.col.update_one(
            {"user_id": user_id, "situation_summaries.session_id": session_id},
            {"$set": {"situation_summaries.$.resolved": True, "updated_at": _now()}},
        )

    # ── Prompt helper ─────────────────────────────────────────────────────────

    def get_context_for_prompt(self, user_id: str) -> str:
        """
        Returns a compact block to prepend to LLM user-messages.
        Returns empty string if no memory exists.
        """
        memory = self.get(user_id)
        lines: List[str] = []

        pi = memory.personal_info
        if pi.name:
            lines.append(f"- Tên: {pi.name}")
        if pi.age:
            lines.append(f"- Tuổi: {pi.age}")
        if pi.occupation:
            lines.append(f"- Nghề nghiệp: {pi.occupation}")
        if pi.location:
            lines.append(f"- Địa điểm: {pi.location}")
        if pi.notes:
            lines.append(f"- Ghi chú: {pi.notes}")

        recent = (memory.situation_summaries or [])[-3:]
        if recent:
            lines.append("- Vụ việc gần đây:")
            for s in recent:
                status = "✓ Đã giải quyết" if s.resolved else "⏳ Đang xử lý"
                lines.append(f"  • [{s.domain}] {s.summary} ({status})")

        if not lines:
            return ""

        return "Thông tin người dùng đã biết:\n" + "\n".join(lines)
