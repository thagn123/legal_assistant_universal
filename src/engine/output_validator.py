"""
OutputValidator — post-generation safety layer.

Runs after LLM generates recommended_actions (and optionally full_assessment text).
Rewrites or removes any action that contradicts PRESENT evidence in the current session.

Rule: if evidence item has status=PRESENT, no output may ask the user to
"thu thập", "bổ sung", "xin cấp", "chuẩn bị", "cần có", "nộp thêm" that same item.

Never raises — on any error returns the original list unchanged.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List

from src.evidence.evidence_gap_engine import filter_contradictory_recommendations
from src.evidence.evidence_normalizer import normalize_text

logger = logging.getLogger(__name__)

# Supplement verbs — Vietnamese phrases that indicate "go collect this document"
_SUPPLEMENT_VERBS = [
    "thu thập",
    "bổ sung",
    "xin cấp",
    "xin cấp lần đầu",
    "cần có",
    "cần thu thập",
    "cần bổ sung",
    "cần chuẩn bị",
    "nộp thêm",
    "cung cấp thêm",
    "cần nộp",
    "làm thủ tục cấp",
    "đăng ký cấp",
    "chưa có",
    "chưa thu thập",
]

# All known aliases for land_certificate — used to catch text-level contradictions
_LAND_CERT_ALIASES = [
    "sổ đỏ", "sổ hồng", "gcn qsdđ", "gcn qsdd",
    "giấy chứng nhận quyền sử dụng đất",
    "giấy chứng nhận qsdd",
    "bìa đỏ", "bìa hồng",
    "giấy nhà đất",
    "land certificate",
]

# Pattern: supplement verb followed by land alias within 40 chars (diacritics input)
_LAND_SUPPLEMENT_RE = re.compile(
    r"(" + "|".join(re.escape(v) for v in _SUPPLEMENT_VERBS) + r")"
    r".{0,40}"
    r"(" + "|".join(re.escape(a) for a in _LAND_CERT_ALIASES) + r")",
    re.IGNORECASE | re.UNICODE,
)
_LAND_SUPPLEMENT_RE2 = re.compile(
    r"(" + "|".join(re.escape(a) for a in _LAND_CERT_ALIASES) + r")"
    r".{0,40}"
    r"(" + "|".join(re.escape(v) for v in _SUPPLEMENT_VERBS) + r")",
    re.IGNORECASE | re.UNICODE,
)

# No-diacritics versions for sanitize_prose — needed because normalize_text()
# strips diacritics, and the patterns above won't match the folded output.
_SUPPLEMENT_VERBS_NORM = [normalize_text(v) for v in _SUPPLEMENT_VERBS]
_LAND_CERT_ALIASES_NORM = [normalize_text(a) for a in _LAND_CERT_ALIASES]

_LAND_SUPPLEMENT_RE_NORM = re.compile(
    r"(" + "|".join(re.escape(v) for v in _SUPPLEMENT_VERBS_NORM) + r")"
    r".{0,40}"
    r"(" + "|".join(re.escape(a) for a in _LAND_CERT_ALIASES_NORM) + r")",
    re.IGNORECASE | re.UNICODE,
)

# Safe document operations: making copies, photocopy, notarising.
# These are fine even when the document is already PRESENT — user is working
# WITH the document, not being asked to acquire it from scratch.
# Uses character classes to handle both diacritics and normalized (no-diacritics) text.
_SAFE_COPY_RE = re.compile(
    r"ban sao|b[aả]n sao|photo|s[aá]o ch[uú]p|c[oô]ng ch[uứ]ng",
    re.IGNORECASE | re.UNICODE,
)

# Rewrite templates for sanitize_prose()
_PROSE_REWRITE_GENERIC = (
    "Bạn đã có sổ đỏ; hãy kiểm tra thông tin người đứng tên, diện tích, "
    "ranh giới và chuẩn bị bản sao công chứng nếu cần nộp hồ sơ."
)
_PROSE_REWRITE_FIRST_ISSUANCE = (
    "Vì bạn đã có giấy chứng nhận quyền sử dụng đất, trọng tâm là kiểm tra "
    "tính hợp lệ và chứng cứ về phần diện tích tranh chấp."
)

# Cues in normalized text that indicate "first issuance" → use specific rewrite
_FIRST_ISSUANCE_CUES = [
    "lan dau", "cap lan dau", "dang ky cap", "lam thu tuc cap", "xin cap",
]


class OutputValidator:
    """
    Post-generation safety layer.

    validate(actions, evidence_context)    — filters recommended_actions list.
    scan_text(text, evidence_context)      — returns list of suspicious sentences.
    sanitize_prose(text, evidence_context) — rewrites/removes contradictory
                                             sentences in prose; returns (clean, flagged).
    """

    def validate(
        self,
        recommended_actions: List[str],
        evidence_context: Any,
    ) -> List[str]:
        """
        Rewrite recommended_actions that contradict PRESENT evidence.
        Falls back to original list on any error.
        """
        if not evidence_context or not recommended_actions:
            return recommended_actions
        present = getattr(evidence_context, "present_evidence", None)
        if not present:
            return recommended_actions
        try:
            return filter_contradictory_recommendations(recommended_actions, present)
        except Exception as exc:
            logger.warning("OutputValidator.validate failed (non-fatal): %s", exc)
            return recommended_actions

    def scan_text(
        self,
        text: str,
        evidence_context: Any,
    ) -> List[str]:
        """
        Scan free-form text for sentences that contradict PRESENT evidence.
        Returns list of suspicious sentences (for logging, does NOT rewrite).
        Checks both diacritics and no-diacritics inputs.
        """
        if not evidence_context or not text:
            return []
        present = getattr(evidence_context, "present_evidence", None)
        if not present:
            return []

        present_ids = {
            getattr(item, "evidence_id", None) or item.get("evidence_id", "")
            for item in present
        }

        suspicious: List[str] = []
        if "land_certificate" in present_ids:
            for sentence in re.split(r"[.!?\n]", text):
                s_folded = normalize_text(sentence)
                # Check original diacritics text AND normalized text
                if (
                    _LAND_SUPPLEMENT_RE.search(sentence)
                    or _LAND_SUPPLEMENT_RE2.search(sentence)
                    or _LAND_SUPPLEMENT_RE_NORM.search(s_folded)
                ):
                    suspicious.append(sentence.strip())

        return suspicious

    def sanitize_prose(
        self,
        text: str,
        evidence_context: Any,
    ) -> "tuple[str, List[str]]":
        """
        Rewrite or remove sentences in free-form prose that contradict PRESENT evidence.

        If land_certificate is PRESENT, sentences asking the user to acquire/obtain it
        are rewritten to safe equivalents.  Sentences involving copies, scans, or
        notarisation are left untouched (safe operations on a document already owned).

        Detection strategy:
        - Apply _LAND_SUPPLEMENT_RE to the ORIGINAL sentence (handles diacritics input)
        - Apply _LAND_SUPPLEMENT_RE_NORM to NORMALIZED sentence (handles no-diacritics input)
        - Only flags supplement_verb BEFORE land_alias to avoid false positives like
          "Sổ đỏ của bạn; cần bổ sung biên lai" where the object is not land_certificate.

        Returns (sanitized_text, list_of_flagged_original_sentences).
        Never raises — on any error returns (original_text, []).
        """
        if not evidence_context or not text:
            return text, []
        present = getattr(evidence_context, "present_evidence", None)
        if not present:
            return text, []

        present_ids = {
            getattr(item, "evidence_id", None) or item.get("evidence_id", "")
            for item in present
        }

        if "land_certificate" not in present_ids:
            return text, []

        try:
            flagged: List[str] = []
            # Split on sentence-ending punctuation/newlines, keeping delimiters
            parts = re.split(r"([.!?\n]+)", text)
            output_parts: List[str] = []

            i = 0
            while i < len(parts):
                chunk = parts[i]
                sep = parts[i + 1] if i + 1 < len(parts) else ""
                i += 2

                stripped = chunk.strip()
                if not stripped:
                    output_parts.append(chunk + sep)
                    continue

                s_folded = normalize_text(chunk)

                # Check both diacritics original AND normalized — covers all input forms
                is_contradictory = (
                    _LAND_SUPPLEMENT_RE.search(chunk)           # diacritics text
                    or _LAND_SUPPLEMENT_RE_NORM.search(s_folded)  # no-diacritics text
                )
                if not is_contradictory:
                    output_parts.append(chunk + sep)
                    continue

                # Safe operations (copy / photo / notarise) on original text.
                # _SAFE_COPY_RE uses char classes that cover both diacritics and normalized.
                if _SAFE_COPY_RE.search(chunk):
                    output_parts.append(chunk + sep)
                    continue

                # Genuine contradiction — rewrite in place.
                flagged.append(stripped)
                rewrite = (
                    _PROSE_REWRITE_FIRST_ISSUANCE
                    if any(c in s_folded for c in _FIRST_ISSUANCE_CUES)
                    else _PROSE_REWRITE_GENERIC
                )
                leading = chunk[: len(chunk) - len(chunk.lstrip())]
                output_parts.append(leading + rewrite + sep)

            return "".join(output_parts), flagged

        except Exception as exc:
            logger.warning("sanitize_prose inner error (non-fatal): %s", exc)
            return text, []
