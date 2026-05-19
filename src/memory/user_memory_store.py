"""
UserMemoryStore — persistent cross-session memory for personalization.

Unlike SessionStore (24h TTL), this collection never expires.
Stores personal facts the user reveals during conversations plus
compressed situation summaries (last 20 sessions).

Collection: user_memory

Security:
  All user-controlled fields (especially 'notes') are sanitized through
  _sanitize_field() before storage and before LLM prompt injection.
  get_context_for_prompt() wraps output in structural delimiters so the
  LLM can distinguish trusted system context from user-controlled text.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

from src.mongodb.client import get_db

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.utcnow().isoformat()


# ---------------------------------------------------------------------------
# Input sanitization — blocks prompt injection, enforces field limits
# ---------------------------------------------------------------------------

# C0 control chars (keep tab \x09 and newline \x0a, \x0d)
_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

# Classic prompt-injection phrases (English + transliterated forms)
_INJECTION_RE = re.compile(
    r"\b(?:ignore|forget|disregard|override|bypass)\b.{0,40}"
    r"(?:previous|prior|above|all|system|instruction|rule|prompt|constraint)",
    re.IGNORECASE | re.DOTALL,
)

# Role-switching attempts
_ROLE_SWITCH_RE = re.compile(
    r"\b(?:"
    r"you\s+are\s+now"
    r"|act\s+as"
    r"|pretend\s+to\s+be"
    r"|from\s+now\s+on\s+you\s+are"
    r"|your\s+new\s+(?:role|persona|identity)"
    r")\b",
    re.IGNORECASE,
)

# LLM message-format injection tokens (ChatML / Llama / Mistral / etc.)
_FORMAT_INJ_RE = re.compile(
    r"(?:"
    r"<\|(?:system|user|assistant)\|>"        # ChatML tokens
    r"|\[/?(?:INST|SYS|SYSTEM)\]"             # Llama/Mistral tags
    r"|(?:(?:^|\n)\s*(?:system|assistant)\s*:)"  # "system:" / "assistant:" role markers
    r")",
    re.IGNORECASE | re.MULTILINE,
)

_REDACTED = "[đã lọc]"

# Per-field max lengths (characters)
_FIELD_LIMITS: Dict[str, int] = {
    "name":       80,
    "occupation": 100,
    "location":   100,
    "notes":      500,
    "summary":    150,
}


def _sanitize_field(value: Optional[str], field_name: str = "notes") -> Optional[str]:
    """
    Sanitize a user-provided string before storage or LLM prompt injection.

    Steps:
      1. Strip C0 control characters (tabs/newlines kept)
      2. Remove LLM message-format injection tokens
      3. Replace prompt-injection phrases with placeholder
      4. Replace role-switch attempts
      5. Truncate to field-specific limit

    Returns None if empty after sanitization.
    """
    if not value:
        return value
    if not isinstance(value, str):
        value = str(value)
    max_len = _FIELD_LIMITS.get(field_name, 200)
    value = _CTRL_RE.sub("", value)
    value = _FORMAT_INJ_RE.sub(_REDACTED, value)
    value = _INJECTION_RE.sub(_REDACTED, value)
    value = _ROLE_SWITCH_RE.sub(_REDACTED, value)
    value = value[:max_len].strip()
    return value or None


def _sanitize_age(value: Optional[int]) -> Optional[int]:
    """Validate age is in a realistic human range."""
    if value is None:
        return None
    try:
        v = int(value)
        return v if 10 <= v <= 100 else None
    except (ValueError, TypeError):
        return None


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
        """
        Partial upsert — sanitizes all string fields before storage.
        Clears a field by passing None.
        """
        set_ops: Dict[str, Any] = {"updated_at": _now()}
        unset_ops: Dict[str, int] = {}

        for k, v in updates.items():
            if v is None:
                unset_ops[f"personal_info.{k}"] = 1
            elif k == "age":
                sanitized = _sanitize_age(v)
                if sanitized is not None:
                    set_ops[f"personal_info.{k}"] = sanitized
                else:
                    unset_ops[f"personal_info.{k}"] = 1
            else:
                sanitized = _sanitize_field(str(v), field_name=k)
                if sanitized:
                    set_ops[f"personal_info.{k}"] = sanitized
                else:
                    unset_ops[f"personal_info.{k}"] = 1

        op: Dict[str, Any] = {"$set": set_ops}
        if unset_ops:
            op["$unset"] = unset_ops
        self.col.update_one({"user_id": user_id}, op, upsert=True)

    def upsert_situation_summary(self, user_id: str, record: SituationRecord) -> None:
        """Add or replace summary for this session_id; sanitize before storing; keep last 20."""
        # Sanitize the LLM-generated summary before persisting
        record.summary = _sanitize_field(record.summary, field_name="summary") or ""
        if not record.summary:
            return

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
        Returns a sanitized, delimiter-wrapped block to prepend to LLM user-messages.
        The structural delimiters help the model distinguish trusted system context
        from user-controlled content, reducing prompt-injection risk.
        Returns empty string if no memory exists.
        """
        memory = self.get(user_id)
        lines: List[str] = []

        pi = memory.personal_info
        # Re-sanitize at read time as a defence-in-depth measure
        if pi.name:
            lines.append(f"- Tên: {_sanitize_field(pi.name, 'name') or ''}")
        if pi.age:
            lines.append(f"- Tuổi: {pi.age}")
        if pi.occupation:
            lines.append(f"- Nghề nghiệp: {_sanitize_field(pi.occupation, 'occupation') or ''}")
        if pi.location:
            lines.append(f"- Địa điểm: {_sanitize_field(pi.location, 'location') or ''}")
        if pi.notes:
            sanitized_notes = _sanitize_field(pi.notes, "notes")
            if sanitized_notes:
                lines.append(f"- Ghi chú: {sanitized_notes}")

        recent = (memory.situation_summaries or [])[-3:]
        if recent:
            lines.append("- Vụ việc gần đây:")
            for s in recent:
                safe_summary = _sanitize_field(s.summary, "summary") or ""
                status = "✓ Đã giải quyết" if s.resolved else "⏳ Đang xử lý"
                lines.append(f"  • [{s.domain}] {safe_summary} ({status})")

        # Remove empty lines produced by failed sanitization
        lines = [ln for ln in lines if ln.strip() and ln.strip() not in ("- Tên: ", "- Nghề nghiệp: ", "- Địa điểm: ")]

        if not lines:
            return ""

        # Structural delimiters — signal to LLM that this is system-provided, read-only data
        return (
            "--- THÔNG TIN CÁ NHÂN (hệ thống cung cấp, chỉ đọc) ---\n"
            + "Thông tin người dùng đã biết:\n"
            + "\n".join(lines)
            + "\n--- KẾT THÚC THÔNG TIN CÁ NHÂN ---"
        )
