"""
Privacy anonymizer for LexAI community case patterns.

Redacts PII from user-supplied legal situation text before storing as a
community case pattern.  Deterministic regex-based — no LLM calls needed.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

# ── Regex patterns ────────────────────────────────────────────────────────────

_EMAIL_RE = re.compile(
    r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"
)

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(?:0|\+84|84)"
    r"[\s.\-]?"
    r"(?:3[2-9]|5[6-9]|7[06-9]|8[0-9]|9[0-9])"
    r"[\s.\-]?\d{3}"
    r"[\s.\-]?\d{4}"
    r"(?!\d)"
)

_CITIZEN_ID_RE = re.compile(
    r"(?<!\d)\d{9}(?!\d)|(?<!\d)\d{12}(?!\d)"
)

# House number / specific address: "số 12", "12/3", "123 Lê Lợi"
_ADDRESS_RE = re.compile(
    r"(?:số\s*)?\d+(?:[/\-]\d+)*\s+(?:[A-ZÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐÊƠƯẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴỶỸ][a-zàáâãèéêìíòóôõùúýăđêơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ]+(?:\s+[A-Za-zÀ-ỹ]+){0,3})",
    re.UNICODE,
)

# Name after sensitive indicator phrases.
# Indicators are listed in both lowercase and Title case to handle both forms.
_VI_UPPER = r"ÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚÝĂĐƠƯẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴỶỸ"
_VI_LOWER = r"àáâãèéêìíòóôõùúýăđơưạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵỷỹ"
_NAME_START = rf"[A-Z{_VI_UPPER}]"
_NAME_CONT = rf"[a-z{_VI_LOWER}]"

_NAME_INDICATOR_RE = re.compile(
    r"(?:"
    r"(?:[Tt]ôi\s+tên|[Tt]ên\s+tôi)\s+(?:là\s+)?"
    r"|[Vv]ợ\s+tôi\s+tên\s+(?:là\s+)?"
    r"|[Cc]hồng\s+tôi\s+tên\s+(?:là\s+)?"
    r"|[Ôô]ng\s+"
    r"|[Bb]à\s+"
    r"|[Aa]nh\s+"
    r"|[Cc]hị\s+"
    r"|[Ee]m\s+"
    r"|[Cc]ô\s+"
    r"|[Cc]hú\s+"
    r"|[Bb]ác\s+"
    r")"
    + rf"({_NAME_START}{_NAME_CONT}+"
    + rf"(?:\s+{_NAME_START}{_NAME_CONT}+){{1,3}})"
    + r"(?=[,.\s]|$)",
    re.UNICODE,
)

# ── Domain fallback summaries ─────────────────────────────────────────────────

_DOMAIN_FALLBACK: Dict[str, str] = {
    "dat_dai":     "Tình huống liên quan đến đất đai và quyền sử dụng đất.",
    "hop_dong":    "Tình huống liên quan đến hợp đồng và tranh chấp hợp đồng.",
    "lao_dong":    "Tình huống liên quan đến quan hệ lao động và quyền lợi người lao động.",
    "doanh_nghiep":"Tình huống liên quan đến doanh nghiệp và hoạt động kinh doanh.",
    "dan_su":      "Tình huống liên quan đến dân sự và nghĩa vụ pháp lý.",
    "hinh_su":     "Tình huống liên quan đến vụ việc hình sự.",
    "hanh_chinh":  "Tình huống liên quan đến khiếu nại hành chính.",
    "gia_dinh":    "Tình huống liên quan đến hôn nhân và gia đình.",
    "general":     "Tình huống pháp lý cần tư vấn.",
}


# ── Public API ────────────────────────────────────────────────────────────────


def anonymize_legal_situation(
    text: str,
    domain: str = "general",
) -> Dict[str, Any]:
    """
    Redact PII from a legal situation description and return a safe summary.

    Returns:
        {
            "safe_summary": str,        # redacted text, never empty
            "redaction_count": int,
            "risk_flags": List[str],    # types of PII found
        }
    """
    if not isinstance(text, str):
        text = str(text)

    redaction_count = 0
    risk_flags: List[str] = []

    def _replace(pattern: re.Pattern, replacement: str, flag: str, t: str) -> str:
        nonlocal redaction_count
        result, n = pattern.subn(replacement, t)
        if n:
            redaction_count += n
            if flag not in risk_flags:
                risk_flags.append(flag)
        return result

    work = text

    # 1. Email
    work = _replace(_EMAIL_RE, "[EMAIL]", "email", work)

    # 2. Phone
    work = _replace(_PHONE_RE, "[SĐT]", "phone", work)

    # 3. Citizen ID / CMND / CCCD
    work = _replace(_CITIZEN_ID_RE, "[CMND/CCCD]", "citizen_id", work)

    # 4. Specific addresses
    work = _replace(_ADDRESS_RE, "[ĐỊA CHỈ]", "address", work)

    # 5. Names after indicator phrases (replace only the captured name group)
    def _name_sub(m: re.Match) -> str:
        nonlocal redaction_count
        redaction_count += 1
        if "name" not in risk_flags:
            risk_flags.append("name")
        prefix = m.group(0)[: m.start(1) - m.start()]
        return prefix + "[TÊN]"

    work, _ = _NAME_INDICATOR_RE.subn(_name_sub, work)

    # Strip leftover whitespace artefacts
    safe = re.sub(r"\s{2,}", " ", work).strip()

    # Ensure non-empty fallback
    if not safe or len(safe) < 10:
        safe = _DOMAIN_FALLBACK.get(domain, _DOMAIN_FALLBACK["general"])

    return {
        "safe_summary": safe,
        "redaction_count": redaction_count,
        "risk_flags": risk_flags,
    }
