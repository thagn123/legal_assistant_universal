"""
Integration tests for /intelligence/analyze endpoint.

These tests go through the full 7-stage orchestrator pipeline and verify that:
- recommended_actions contains no contradictory phrases when evidence is PRESENT
- next_best_actions contains no contradictory phrases
- full_assessment prose contains no contradictory phrases (sanitize_prose wired)
- No-diacritic phrasing is detected
- Evidence MISSING still allows supplement recommendations
- OutputValidator.sanitize_prose works correctly in isolation

Run:
    pytest tests/integration/test_analyze_endpoint.py -v
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.engine.output_validator import OutputValidator
from src.evidence.evidence_gap_engine import analyze_evidence_gap
from src.evidence.evidence_schemas import MISSING, PRESENT, EvidenceAssessment


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def client():
    """App with MongoDB disabled — orchestrator uses deterministic fallback."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as c:
        yield c


BAD_PHRASES = [
    "thu thập sổ đỏ",
    "bổ sung sổ đỏ",
    "xin cấp sổ đỏ",
    "xin cấp giấy chứng nhận quyền sử dụng đất",
    "xin cấp gcn qsdđ",
    "xin cấp gcn qsdd",
    "cần có sổ đỏ",
    "cần bổ sung giấy chứng nhận quyền sử dụng đất",
    "cần thu thập giấy chứng nhận quyền sử dụng đất",
    "cần thu thập sổ đỏ",
    "nộp thêm sổ đỏ",
]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _collect_text(body: dict) -> str:
    """Flatten all user-visible text from /intelligence/analyze response."""
    parts = []
    parts.extend(body.get("recommended_actions", []))
    for nba in body.get("next_best_actions", []):
        parts.append(nba.get("title", ""))
        parts.append(nba.get("description", ""))
    parts.append(body.get("full_assessment", ""))
    return " ".join(parts).lower()


# ---------------------------------------------------------------------------
# T-A1: Main flow — no land_certificate contradiction when PRESENT
# ---------------------------------------------------------------------------

def test_analyze_no_land_cert_contradiction_in_actions_nba_and_prose(client):
    """
    When user states they have sổ đỏ, the response must not ask them to collect it.
    Covers recommended_actions, next_best_actions, AND full_assessment prose.
    """
    resp = client.post(
        "/intelligence/analyze",
        headers={"X-User-ID": "ta1_user"},
        json={
            "situation": "Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm đất của tôi.",
            "top_k": 4,
        },
    )
    assert resp.status_code == 200, f"T-A1: expected 200, got {resp.status_code}: {resp.text[:400]}"
    body = resp.json()

    all_text = _collect_text(body)
    for bad in BAD_PHRASES:
        assert bad not in all_text, (
            f"T-A1 FAIL: contradictory phrase '{bad}' found in response.\n"
            f"recommended_actions: {body.get('recommended_actions')}\n"
            f"next_best_actions: {body.get('next_best_actions')}\n"
            f"full_assessment[:400]: {body.get('full_assessment', '')[:400]}"
        )


# ---------------------------------------------------------------------------
# T-A2: No-diacritic phrasing — same guarantee
# ---------------------------------------------------------------------------

def test_analyze_no_diacritic_situation_no_contradiction(client):
    """
    'so do cua toi' (no diacritics) must still be detected as PRESENT.
    """
    resp = client.post(
        "/intelligence/analyze",
        headers={"X-User-ID": "ta2_user"},
        json={
            "situation": "so do cua toi bi hang xom tranh chap ranh gioi dat",
            "top_k": 4,
        },
    )
    assert resp.status_code == 200, f"T-A2: {resp.status_code} {resp.text[:300]}"
    body = resp.json()
    all_text = _collect_text(body)
    for bad in BAD_PHRASES:
        assert bad not in all_text, (
            f"T-A2 FAIL: bad phrase '{bad}' found despite no-diacritic sổ đỏ present"
        )


# ---------------------------------------------------------------------------
# T-A3: Allow valid land certificate actions (no over-filtering)
# ---------------------------------------------------------------------------

def test_analyze_does_not_over_filter_valid_land_actions(client):
    """
    Recommendations like 'đo đạc ranh giới', 'kiểm tra sổ đỏ', 'hòa giải'
    must NOT be removed by the sanitizer.
    """
    resp = client.post(
        "/intelligence/analyze",
        headers={"X-User-ID": "ta3_user"},
        json={
            "situation": "Tôi đã có sổ đỏ, hàng xóm lấn đất 50cm.",
            "top_k": 4,
        },
    )
    assert resp.status_code == 200, f"T-A3: {resp.status_code}"
    body = resp.json()

    # Response must still have some recommendations — sanitizer must not clear everything
    actions = body.get("recommended_actions", [])
    nba = body.get("next_best_actions", [])
    assert actions or nba, "T-A3 FAIL: sanitizer removed ALL recommendations (over-filtering)"


# ---------------------------------------------------------------------------
# T-A4: Missing evidence — supplement recommendation is valid
# ---------------------------------------------------------------------------

def test_analyze_missing_land_cert_allows_supplement_recommendation(client):
    """
    When user has NOT stated they have sổ đỏ, the system may recommend collecting it.
    Ensuring we don't accidentally suppress valid recommendations.
    """
    resp = client.post(
        "/intelligence/analyze",
        headers={"X-User-ID": "ta4_user"},
        json={
            "situation": "Tôi mua đất bằng giấy viết tay, bên bán không chịu ra công chứng.",
            "top_k": 4,
        },
    )
    assert resp.status_code == 200, f"T-A4: {resp.status_code}"
    body = resp.json()

    # System may suggest acquiring sổ đỏ — that's correct here
    all_text = _collect_text(body)
    # Just assert it returns something meaningful, not that it contains a specific phrase
    assert body.get("full_assessment") or body.get("recommended_actions"), (
        "T-A4 FAIL: no assessment or recommendations for missing evidence case"
    )


# ---------------------------------------------------------------------------
# T-A5: GCN QSDĐ alias — same guarantee as sổ đỏ
# ---------------------------------------------------------------------------

def test_analyze_gcn_qsdd_alias_no_contradiction(client):
    """GCN QSDĐ alias must be detected as PRESENT and filtered from prose."""
    resp = client.post(
        "/intelligence/analyze",
        headers={"X-User-ID": "ta5_user"},
        json={
            "situation": "GCN QSDĐ đứng tên tôi nhưng bị hàng xóm lấn chiếm phần phía Bắc.",
            "top_k": 4,
        },
    )
    assert resp.status_code == 200, f"T-A5: {resp.status_code}"
    body = resp.json()
    all_text = _collect_text(body)
    for bad in BAD_PHRASES:
        assert bad not in all_text, (
            f"T-A5 FAIL: GCN QSDĐ alias not detected; bad phrase '{bad}' in response"
        )


# ---------------------------------------------------------------------------
# OutputValidator.sanitize_prose — direct unit tests (no HTTP, fast)
# ---------------------------------------------------------------------------

class _MockContextPresent:
    """Minimal evidence_context mock with land_certificate PRESENT."""
    present_evidence = [
        EvidenceAssessment(
            evidence_id="land_certificate",
            title="Sổ đỏ / Giấy chứng nhận quyền sử dụng đất",
            category="certificate",
            domain="dat_dai",
            priority="high",
            status=PRESENT,
            matched_text="sổ đỏ của tôi",
            matched_alias="sổ đỏ",
            confidence=0.9,
        )
    ]
    missing_evidence = []


class _MockContextMissing:
    """Minimal evidence_context mock with land_certificate MISSING."""
    present_evidence = []
    missing_evidence = [
        EvidenceAssessment(
            evidence_id="land_certificate",
            title="Sổ đỏ / Giấy chứng nhận quyền sử dụng đất",
            category="certificate",
            domain="dat_dai",
            priority="high",
            status=MISSING,
            matched_text="",
            matched_alias="",
            confidence=0.0,
        )
    ]


def test_sanitize_prose_removes_supplement_verb_before_land_alias():
    """Core rule: 'cần bổ sung sổ đỏ' must be rewritten when PRESENT."""
    validator = OutputValidator()
    text = "Bạn cần bổ sung sổ đỏ để chứng minh quyền sử dụng đất. Sau đó hãy yêu cầu hòa giải tại UBND xã."
    sanitized, flagged = validator.sanitize_prose(text, _MockContextPresent())

    assert len(flagged) >= 1, "sanitize_prose must flag at least one contradictory sentence"
    assert "cần bổ sung sổ đỏ" not in sanitized.lower(), (
        f"Contradictory phrase survived sanitization: {sanitized}"
    )
    assert "hòa giải tại ubnd xã" in sanitized.lower(), (
        "sanitize_prose must NOT remove the valid 'hòa giải' sentence"
    )


def test_sanitize_prose_removes_thu_thap_so_do():
    """'thu thập sổ đỏ' must be rewritten."""
    validator = OutputValidator()
    text = "Trước tiên cần thu thập sổ đỏ hoặc GCN QSDĐ. Sau đó liên hệ UBND xã."
    sanitized, flagged = validator.sanitize_prose(text, _MockContextPresent())

    assert len(flagged) >= 1
    assert "thu thập sổ đỏ" not in sanitized.lower()
    assert "ubnd xã" in sanitized.lower()


def test_sanitize_prose_preserves_copy_actions():
    """'chuẩn bị bản sao công chứng sổ đỏ' is safe — must NOT be flagged."""
    validator = OutputValidator()
    text = "Hãy chuẩn bị bản sao công chứng sổ đỏ nếu cần nộp hồ sơ."
    sanitized, flagged = validator.sanitize_prose(text, _MockContextPresent())

    assert len(flagged) == 0, (
        f"sanitize_prose over-filtered a safe copy sentence. Flagged: {flagged}"
    )
    assert sanitized == text


def test_sanitize_prose_no_diacritic_detection():
    """'ban can bo sung so do' (no diacritics) must be detected and rewritten."""
    validator = OutputValidator()
    text = "Ban can bo sung so do de chung minh quyen su dung dat."
    sanitized, flagged = validator.sanitize_prose(text, _MockContextPresent())

    assert len(flagged) >= 1, "No-diacritic contradiction not detected"
    assert "bo sung so do" not in sanitized.lower()


def test_sanitize_prose_missing_evidence_not_flagged():
    """When land_certificate is MISSING, supplement recommendations are valid — must not be rewritten."""
    validator = OutputValidator()
    text = "Bạn cần bổ sung sổ đỏ để chứng minh quyền sử dụng đất."
    sanitized, flagged = validator.sanitize_prose(text, _MockContextMissing())

    assert len(flagged) == 0, (
        "sanitize_prose must NOT flag supplement advice when evidence is MISSING"
    )
    assert sanitized == text


def test_sanitize_prose_no_context_returns_original():
    """With no evidence context, prose must be returned unchanged."""
    validator = OutputValidator()
    text = "Bạn cần bổ sung sổ đỏ."
    sanitized, flagged = validator.sanitize_prose(text, None)

    assert sanitized == text
    assert flagged == []


def test_sanitize_prose_first_issuance_rewrite():
    """'xin cấp lần đầu' must trigger the first-issuance specific rewrite."""
    validator = OutputValidator()
    text = "Cần làm thủ tục xin cấp sổ đỏ lần đầu tại Văn phòng đăng ký đất đai."
    sanitized, flagged = validator.sanitize_prose(text, _MockContextPresent())

    assert len(flagged) >= 1
    # Should use the first-issuance rewrite (mentions "tính hợp lệ")
    assert "tính hợp lệ" in sanitized or "đã có" in sanitized.lower()
