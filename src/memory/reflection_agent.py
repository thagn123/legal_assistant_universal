"""
ReflectionAgent — extracts personal facts and situation summaries from conversations.

Two-tier design:
  Tier 1 (instant, always):   regex patterns → name, age, occupation, location
  Tier 2 (async background):  LLM (gpt-4o-mini) → richer extraction + 1-sentence
                               situation summary.  Rate-limited to 1 call / 60s / user.

Integration:
  Called from orchestrator.py Stage 7 via reflect_async() — non-blocking.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional

from src.memory.user_memory_store import PersonalInfo, SituationRecord, UserMemoryStore, _sanitize_field, _sanitize_age

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Tier 1 — regex extractors
# ---------------------------------------------------------------------------

_NAME_PATTERNS = [
    # Vietnamese: "tên tôi là Nguyễn Văn A"
    re.compile(
        r"(?:tên tôi là|tên của tôi là|tôi tên là|gọi tôi là|mình tên là|tôi là)\s+"
        r"([A-ZÀÁẢÃẠĂẮẶẰẲẴÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ]"
        r"(?:[a-zàáảãạăắặằẳẵâấầẩẫậđèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵ"
        r"A-ZÀÁẢÃẠĂẮẶẰẲẴÂẤẦẨẪẬĐÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴ\s]{1,35}))",
        re.IGNORECASE,
    ),
]

_AGE_PATTERNS = [
    re.compile(r"(?:tôi|mình)\s+(\d{1,2})\s*tuổi", re.IGNORECASE),
    re.compile(r"\b(\d{1,2})\s*tuổi\b"),
]

_OCCUPATION_PATTERN = re.compile(
    r"(?:tôi là|tôi đang làm|nghề nghiệp|chức vụ|tôi làm)\s*:?\s*"
    r"(luật sư|kế toán|giám đốc|nhân viên|kỹ sư|bác sĩ|giáo viên|"
    r"chủ doanh nghiệp|chủ công ty|nhân sự|hr|kinh doanh|lập trình viên|"
    r"cán bộ|công chức|nông dân|thợ|thư ký|kế toán trưởng|trưởng phòng)",
    re.IGNORECASE,
)

_LOCATION_PATTERN = re.compile(
    r"(?:tôi ở|sống tại|ở tại|địa chỉ tại|tại)\s+"
    r"(TP\.?HCM|Hà Nội|Thành phố Hồ Chí Minh|Đà Nẵng|Hải Phòng|Cần Thơ|"
    r"Bình Dương|Đồng Nai|Bắc Ninh|Hưng Yên|Hà Nam|Thái Bình|Vĩnh Phúc|"
    r"Long An|Tiền Giang|An Giang|Khánh Hòa|Lâm Đồng|Đắk Lắk)",
    re.IGNORECASE,
)


def _extract_name(text: str) -> Optional[str]:
    for pat in _NAME_PATTERNS:
        m = pat.search(text)
        if m:
            name = m.group(1).strip()
            if 2 <= len(name) <= 45 and " " in name:  # require at least 2 words
                return name
    return None


def _extract_age(text: str) -> Optional[int]:
    for pat in _AGE_PATTERNS:
        m = pat.search(text)
        if m:
            val = int(m.group(1))
            if 10 <= val <= 100:
                return val
    return None


def _extract_occupation(text: str) -> Optional[str]:
    m = _OCCUPATION_PATTERN.search(text)
    return m.group(1).strip() if m else None


def _extract_location(text: str) -> Optional[str]:
    m = _LOCATION_PATTERN.search(text)
    return m.group(1).strip() if m else None


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class _RateLimiter:
    """Allow at most 1 LLM reflection per user per N seconds."""

    def __init__(self, min_interval_s: float = 60.0) -> None:
        self._last: Dict[str, float] = {}
        self._lock = threading.Lock()
        self._min = min_interval_s

    def allow(self, user_id: str) -> bool:
        with self._lock:
            now = time.monotonic()
            if now - self._last.get(user_id, 0.0) >= self._min:
                self._last[user_id] = now
                return True
            return False


# ---------------------------------------------------------------------------
# ReflectionAgent
# ---------------------------------------------------------------------------


class ReflectionAgent:
    """
    Post-turn reflection that enriches user memory without blocking the response.

    Usage (from orchestrator Stage 7):
        self._reflection.reflect_async(
            user_id=user_id,
            session_id=sid,
            query=situation,
            result_summary="...",
            domain=plan.detected_domain,
            session_turns=len(session_ctx.history),
        )
    """

    def __init__(self, memory_store: UserMemoryStore) -> None:
        self._store = memory_store
        self._rate = _RateLimiter(min_interval_s=60.0)

    def reflect_async(
        self,
        user_id: str,
        session_id: str,
        query: str,
        result_summary: str,
        domain: str,
        session_turns: int = 0,
    ) -> None:
        """Dispatch reflection to a daemon thread — returns immediately."""
        t = threading.Thread(
            target=self._reflect,
            args=(user_id, session_id, query, result_summary, domain, session_turns),
            daemon=True,
            name=f"reflect-{user_id[:8]}",
        )
        t.start()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _reflect(
        self,
        user_id: str,
        session_id: str,
        query: str,
        result_summary: str,
        domain: str,
        session_turns: int,
    ) -> None:
        try:
            self._tier1_patterns(user_id, query)
            # Tier 2: LLM only when there's enough context and rate allows
            if session_turns >= 1 and domain != "general" and self._rate.allow(user_id):
                self._tier2_llm(user_id, session_id, query, result_summary, domain)
        except Exception as exc:
            logger.debug("reflection error for %s: %s", user_id, exc)

    def _tier1_patterns(self, user_id: str, query: str) -> None:
        """Fast regex extraction — < 1ms, always runs."""
        current = self._store.get(user_id)
        pi = current.personal_info
        updates: Dict[str, Any] = {}

        if not pi.name:
            name = _extract_name(query)
            if name:
                updates["name"] = name
        if not pi.age:
            age = _extract_age(query)
            if age:
                updates["age"] = age
        if not pi.occupation:
            occ = _extract_occupation(query)
            if occ:
                updates["occupation"] = occ
        if not pi.location:
            loc = _extract_location(query)
            if loc:
                updates["location"] = loc

        if updates:
            # Sanitize before storing — guards against regex matching attacker-crafted strings
            if "name" in updates and updates["name"]:
                updates["name"] = _sanitize_field(updates["name"], "name")
            if "occupation" in updates and updates["occupation"]:
                updates["occupation"] = _sanitize_field(updates["occupation"], "occupation")
            if "location" in updates and updates["location"]:
                updates["location"] = _sanitize_field(updates["location"], "location")
            updates = {k: v for k, v in updates.items() if v is not None}
            if updates:
                self._store.update_personal_info(user_id, updates)
                logger.info("reflect[t1] %s → fields=%s", user_id[:8], list(updates.keys()))

    def _tier2_llm(
        self,
        user_id: str,
        session_id: str,
        query: str,
        result_summary: str,
        domain: str,
    ) -> None:
        """LLM extraction: personal facts + 1-sentence situation summary."""
        try:
            from src.llm.client import chat_complete, is_available
            if not is_available():
                return

            prompt = (
                "Phân tích đoạn hội thoại pháp lý sau.\n"
                "Trả về JSON:\n"
                '{"personal_info": {"name": null, "age": null, "occupation": null, "location": null},\n'
                ' "situation_summary": null}\n\n'
                f"Câu hỏi: {query[:500]}\n"
                f"Kết quả tư vấn (tóm tắt): {result_summary[:300]}\n\n"
                "Quy tắc:\n"
                "- personal_info: chỉ điền nếu người dùng TỰ tiết lộ rõ ràng, null nếu không có.\n"
                "- situation_summary: TÓM TẮT 1 CÂU (≤120 ký tự) về tình huống pháp lý cụ thể. "
                "  null nếu câu hỏi chung chung hoặc không đủ thông tin.\n"
                "Chỉ trả về JSON."
            )

            raw = chat_complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=200,
                temperature=0.0,
                response_format={"type": "json_object"},
            )
            if not raw:
                return

            data: Dict[str, Any] = json.loads(raw)

            # Update personal info (only missing fields)
            current = self._store.get(user_id)
            pi = current.personal_info
            pi_raw: Dict[str, Any] = data.get("personal_info") or {}
            updates: Dict[str, Any] = {}
            if pi_raw.get("name") and not pi.name:
                updates["name"] = _sanitize_field(str(pi_raw["name"]), "name")
            if pi_raw.get("age") and not pi.age:
                try:
                    updates["age"] = int(pi_raw["age"])
                except (ValueError, TypeError):
                    pass
            if pi_raw.get("occupation") and not pi.occupation:
                updates["occupation"] = _sanitize_field(str(pi_raw["occupation"]), "occupation")
            if pi_raw.get("location") and not pi.location:
                updates["location"] = _sanitize_field(str(pi_raw["location"]), "location")
            if updates:
                self._store.update_personal_info(user_id, updates)
                logger.info("reflect[t2] %s → fields=%s", user_id[:8], list(updates.keys()))

            # Upsert situation summary
            summary: str = (data.get("situation_summary") or "").strip()
            if summary and len(summary) > 10:
                record = SituationRecord(
                    session_id=session_id,
                    date=datetime.utcnow().strftime("%Y-%m-%d"),
                    domain=domain,
                    summary=summary[:150],
                )
                self._store.upsert_situation_summary(user_id, record)
                logger.info("reflect[t2] %s → situation saved (%s)", user_id[:8], domain)

        except Exception as exc:
            logger.debug("tier2 reflection failed %s: %s", user_id, exc)
