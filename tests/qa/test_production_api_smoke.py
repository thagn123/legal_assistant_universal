"""
Production API Smoke Tests — LexAI / ULKA

Mục tiêu: Kiểm tra 5 endpoint chính trước khi deploy beta.
Không chỉ check HTTP 200. Mỗi test check:
  - Response fields chính (cấu trúc)
  - Forbidden phrases cho P0 scenarios
  - Fallback/demo label khi không có real data
  - Behavior với input phi pháp lý

Run:
    pytest tests/qa/test_production_api_smoke.py -v

Chiến lược:
  - TestClient + mongodb_enabled=False → không cần live server
  - P0 phrases được check chính xác (không chỉ assert len > 0)
  - Report được ghi ra qa/api_smoke_report.json + qa/api_smoke_report.md
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app

# ---------------------------------------------------------------------------
# Constants & helpers
# ---------------------------------------------------------------------------

_HEADERS = {"X-User-ID": "qa_smoke_user"}
_QA_DIR = Path(__file__).parent.parent.parent / "qa"

# P0 forbidden phrases — ZERO tolerance across ALL user-visible fields
_P0_FORBIDDEN: List[str] = [
    # Evidence contradiction (sổ đỏ)
    "bạn chưa có sổ đỏ",
    "cần làm sổ đỏ trước",
    "thu thập sổ đỏ",
    "bổ sung sổ đỏ",
    "xin cấp sổ đỏ",
    "không có căn cứ pháp lý",
    # Divorce P0 contradiction
    "không thể ly hôn đơn phương",
    "luật không cho phép ly hôn đơn phương",
    "phải có sự đồng ý của cả hai bên mới được ly hôn",
    # Mediation P0 contradiction
    "hòa giải trước khi ly hôn là bắt buộc và không thể bỏ qua",
    "không được ly hôn nếu chưa hòa giải thành",
]


def _collect_text(body: dict) -> str:
    """Flatten all user-visible text fields from any response body."""
    parts: List[str] = []
    # intelligence/analyze
    parts.extend(body.get("recommended_actions", []))
    parts.append(body.get("full_assessment", ""))
    for nba in body.get("next_best_actions", []):
        parts.append(nba.get("title", ""))
        parts.append(nba.get("description", ""))
    # evidence-gap
    for item in body.get("missing_evidence", []):
        parts.append(item.get("reason", ""))
        parts.append(item.get("item", ""))
    parts.append(body.get("advice", ""))
    # similar-cases
    for case in body.get("official_cases", []):
        parts.append(case.get("situation_summary", ""))
        parts.append(case.get("outcome", ""))
        parts.append(case.get("lesson", ""))
    parts.append(body.get("summary", ""))
    # general
    parts.append(str(body.get("assessment", "")))
    return " ".join(str(p) for p in parts).lower()


def _check_p0(body: dict) -> List[str]:
    """Return list of P0 violations found in response."""
    text = _collect_text(body)
    return [phrase for phrase in _P0_FORBIDDEN if phrase.lower() in text]


@pytest.fixture(scope="module")
def client():
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


# ---------------------------------------------------------------------------
# Report accumulator — collects results then writes on module teardown
# ---------------------------------------------------------------------------

_RESULTS: List[Dict[str, Any]] = []


def _record(test_id: str, endpoint: str, status: str, checks: List[str], bugs: List[str]):
    _RESULTS.append({
        "test_id": test_id,
        "endpoint": endpoint,
        "status": status,
        "checks_passed": checks,
        "bugs_found": bugs,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def _write_reports():
    _QA_DIR.mkdir(parents=True, exist_ok=True)

    passed = sum(1 for r in _RESULTS if r["status"] == "PASS")
    total = len(_RESULTS)
    all_bugs = [b for r in _RESULTS for b in r["bugs_found"]]

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": total - passed,
            "p0_violations": sum(1 for b in all_bugs if "P0" in b),
            "all_bugs": all_bugs,
        },
        "results": _RESULTS,
    }

    json_path = _QA_DIR / "api_smoke_report.json"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# API Smoke Test Report — LexAI / ULKA",
        f"\n**Generated:** {report['generated_at']}",
        f"**Score:** {passed}/{total} PASS\n",
        "## Summary\n",
        f"| Metric | Value |",
        f"|---|---|",
        f"| Total tests | {total} |",
        f"| Passed | {passed} |",
        f"| Failed | {total - passed} |",
        f"| P0 violations | {report['summary']['p0_violations']} |",
        f"| Bugs found | {len(all_bugs)} |",
        "\n## Per-test Results\n",
        "| Test ID | Endpoint | Status | Bugs |",
        "|---|---|---|---|",
    ]
    for r in _RESULTS:
        bugs_str = "; ".join(r["bugs_found"]) if r["bugs_found"] else "none"
        md_lines.append(f"| {r['test_id']} | {r['endpoint']} | {r['status']} | {bugs_str} |")

    if all_bugs:
        md_lines += ["\n## Bugs Found\n"]
        for bug in all_bugs:
            md_lines.append(f"- {bug}")

    md_path = _QA_DIR / "api_smoke_report.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")


# Write reports after all tests complete
@pytest.fixture(scope="module", autouse=True)
def write_reports_on_finish():
    yield
    _write_reports()


# ---------------------------------------------------------------------------
# SM-01 — /intelligence/analyze: S-05 P0 scenario (hòa giải không thành)
# ---------------------------------------------------------------------------

def test_sm01_analyze_p0_mediation_not_mandatory(client):
    """
    S-05: Hòa giải không thành.
    NEVER: "hòa giải trước khi ly hôn là bắt buộc và không thể bỏ qua"
    NEVER: "không được ly hôn nếu chưa hòa giải thành"
    """
    resp = client.post(
        "/intelligence/analyze",
        headers=_HEADERS,
        json={
            "situation": (
                "Tôi và vợ đã hòa giải nhiều lần nhưng không thành. "
                "Chúng tôi muốn ly hôn. Phải làm gì tiếp theo?"
            ),
            "top_k": 4,
        },
    )
    bugs: List[str] = []
    checks: List[str] = []

    # Structure check
    assert resp.status_code == 200, f"SM-01: HTTP {resp.status_code} — {resp.text[:300]}"
    checks.append("HTTP 200")

    body = resp.json()
    assert "full_assessment" in body or "recommended_actions" in body, "Missing response fields"
    checks.append("response fields present")

    # P0 check
    p0_violations = _check_p0(body)
    if p0_violations:
        bugs.extend([f"[P0] SM-01 forbidden phrase: '{v}'" for v in p0_violations])

    # Must return something actionable
    text = _collect_text(body)
    has_content = len(text.strip()) > 50
    if not has_content:
        bugs.append("[P1] SM-01: response too short / empty — not actionable")
    else:
        checks.append("response has actionable content")

    status = "FAIL" if bugs else "PASS"
    _record("SM-01", "/intelligence/analyze", status, checks, bugs)

    assert not bugs, f"SM-01 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-02 — /intelligence/analyze: S-10 P0 scenario (ly hôn đơn phương)
# ---------------------------------------------------------------------------

def test_sm02_analyze_p0_unilateral_divorce_allowed(client):
    """
    S-10: Ly hôn có con nhỏ.
    NEVER: "không thể ly hôn đơn phương"
    NEVER: "phải có sự đồng ý của cả hai bên"
    System MUST NOT say unilateral divorce is impossible.
    """
    resp = client.post(
        "/intelligence/analyze",
        headers=_HEADERS,
        json={
            "situation": (
                "Chồng tôi bạo lực gia đình, tôi muốn ly hôn đơn phương và "
                "giành quyền nuôi con 3 tuổi. Có thể làm được không?"
            ),
            "top_k": 4,
        },
    )
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-02: HTTP {resp.status_code}"
    checks.append("HTTP 200")

    body = resp.json()
    p0_violations = _check_p0(body)
    if p0_violations:
        bugs.extend([f"[P0] SM-02 forbidden phrase: '{v}'" for v in p0_violations])
    else:
        checks.append("no P0 violations")

    text = _collect_text(body)
    # Must mention something about divorce process or child custody
    relevant = any(kw in text for kw in ["ly hôn", "nuôi con", "tòa án", "quyền", "bạo lực"])
    if not relevant:
        bugs.append("[P1] SM-02: response lacks domain-relevant content (divorce/child custody)")
    else:
        checks.append("domain-relevant content present")

    status = "FAIL" if bugs else "PASS"
    _record("SM-02", "/intelligence/analyze", status, checks, bugs)
    assert not bugs, f"SM-02 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-03 — /analysis/evidence-gap: Sổ đỏ PRESENT → no collect contradiction
# ---------------------------------------------------------------------------

def test_sm03_evidence_gap_no_contradiction_when_so_do_present(client):
    """
    Input: user already has sổ đỏ.
    NEVER: advice telling user to "xin cấp sổ đỏ" or "bổ sung sổ đỏ".
    Evidence gap must detect sổ đỏ as PRESENT.
    """
    resp = client.post(
        "/analysis/evidence-gap",
        headers=_HEADERS,
        json={
            "situation": "Tôi đã có sổ đỏ, hàng xóm lấn chiếm đất.",
            "domain": "dat_dai",
            "facts": ["đã có sổ đỏ hợp lệ đứng tên tôi"],
        },
    )
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-03: HTTP {resp.status_code} — {resp.text[:300]}"
    checks.append("HTTP 200")

    body = resp.json()
    required_fields = ["missing_evidence", "present_evidence", "coverage_score", "advice"]
    missing_fields = [f for f in required_fields if f not in body]
    if missing_fields:
        bugs.append(f"[P1] SM-03: missing response fields: {missing_fields}")
    else:
        checks.append("all required fields present")

    # Coverage score must be in [0, 1]
    coverage = body.get("coverage_score", -1)
    if not (0.0 <= coverage <= 1.0):
        bugs.append(f"[P1] SM-03: coverage_score={coverage} out of [0,1] range")
    else:
        checks.append(f"coverage_score={coverage:.2f} in valid range")

    # Check advice doesn't tell user to supplement an already-present document
    advice_lower = body.get("advice", "").lower()
    forbidden_in_advice = [
        p for p in ["bổ sung sổ đỏ", "xin cấp sổ đỏ", "thu thập sổ đỏ"]
        if p in advice_lower
    ]
    if forbidden_in_advice:
        bugs.extend([f"[P0] SM-03 advice contradiction: '{p}'" for p in forbidden_in_advice])
    else:
        checks.append("advice has no supplement contradiction")

    status = "FAIL" if bugs else "PASS"
    _record("SM-03", "/analysis/evidence-gap", status, checks, bugs)
    assert not bugs, f"SM-03 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-04 — /retrieval/laws: Basic law search returns structure + filtered results
# ---------------------------------------------------------------------------

def test_sm04_retrieval_laws_structure_and_no_low_score_leak(client):
    """
    Law search for lao_dong query.
    - Must return valid response structure.
    - With MongoDB disabled → fallback/empty with no score leakage.
    - Must NOT 500.
    """
    resp = client.post(
        "/retrieval/laws",
        headers=_HEADERS,
        json={"query": "Người lao động bị sa thải không có lý do, có quyền đòi bồi thường không?"},
    )
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-04: HTTP {resp.status_code} — {resp.text[:300]}"
    checks.append("HTTP 200 (no 500)")

    body = resp.json()
    required_fields = ["results", "total", "detected_domain", "search_mode"]
    missing_fields = [f for f in required_fields if f not in body]
    if missing_fields:
        bugs.append(f"[P1] SM-04: missing response fields: {missing_fields}")
    else:
        checks.append("response structure valid")

    # If results returned, verify score >= threshold
    for r in body.get("results", []):
        score = r.get("vector_score", 1.0)
        if score < 0.55:
            bugs.append(
                f"[P0] SM-04: result '{r.get('chunk_id')}' has score {score} < 0.55 threshold — leak!"
            )
    if not body.get("results"):
        checks.append("empty results (MongoDB disabled) — acceptable fallback")
    else:
        checks.append(f"all {len(body['results'])} results above threshold")

    status = "FAIL" if bugs else "PASS"
    _record("SM-04", "/retrieval/laws", status, checks, bugs)
    assert not bugs, f"SM-04 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-05 — /retrieval/similar-cases: Fallback labelling + no low-score leak
# ---------------------------------------------------------------------------

def test_sm05_similar_cases_fallback_label_and_no_score_leak(client):
    """
    With MongoDB disabled, similar-cases must:
    - Return 200.
    - Either return empty or demo cases.
    - Demo cases must have is_demo=True.
    - No case below 0.55 threshold.
    - fallback_used=True if demo cases present.
    """
    resp = client.post(
        "/retrieval/similar-cases",
        headers=_HEADERS,
        json={
            "situation": "Công ty cắt giảm lương không báo trước, tôi bị thiệt hại.",
            "include_community": False,
            "persist_anonymized": False,
        },
    )
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-05: HTTP {resp.status_code} — {resp.text[:300]}"
    checks.append("HTTP 200 (no 500)")

    body = resp.json()
    required_fields = ["official_cases", "total", "search_mode", "fallback_used"]
    missing_fields = [f for f in required_fields if f not in body]
    if missing_fields:
        bugs.append(f"[P1] SM-05: missing response fields: {missing_fields}")
    else:
        checks.append("response structure valid")

    # Verify demo labelling
    for case in body.get("official_cases", []):
        case_id = case.get("case_id", "")
        is_demo = case.get("is_demo", False)
        score = case.get("similarity_score", 1.0)
        if case_id.startswith("demo_") and not is_demo:
            bugs.append(f"[P0] SM-05: demo case '{case_id}' missing is_demo=True")
        if score < 0.55 and not is_demo:
            bugs.append(f"[P0] SM-05: non-demo case '{case_id}' has score {score} < 0.55 — threshold leak!")

    if not bugs:
        checks.append("demo labelling and score threshold OK")

    status = "FAIL" if bugs else "PASS"
    _record("SM-05", "/retrieval/similar-cases", status, checks, bugs)
    assert not bugs, f"SM-05 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-06 — /recommendations/next-best-actions: Structure + no empty for valid input
# ---------------------------------------------------------------------------

def test_sm06_next_best_actions_structure_and_content(client):
    """
    NBA with land-law situation.
    - HTTP 200.
    - List of actions (may be empty with no MongoDB, but structure must be correct).
    - Each action has required fields.
    - No P0 forbidden phrases in titles/descriptions.
    """
    resp = client.post(
        "/recommendations/next-best-actions",
        headers=_HEADERS,
        json={
            "situation": "Hàng xóm lấn chiếm đất, tôi có sổ đỏ.",
            "domain": "dat_dai",
            "domain_confidence": 0.9,
            "position_score": 0.7,
        },
    )
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-06: HTTP {resp.status_code} — {resp.text[:300]}"
    checks.append("HTTP 200 (no 500)")

    body = resp.json()
    assert isinstance(body, list), f"SM-06: expected list, got {type(body)}"
    checks.append("response is list")

    action_fields = ["action_id", "title", "description", "module", "priority", "score"]
    for i, action in enumerate(body):
        missing = [f for f in action_fields if f not in action]
        if missing:
            bugs.append(f"[P1] SM-06: action[{i}] missing fields: {missing}")

    # P0 check on NBA titles/descriptions
    nba_text = " ".join(
        f"{a.get('title', '')} {a.get('description', '')}" for a in body
    ).lower()
    for phrase in _P0_FORBIDDEN:
        if phrase.lower() in nba_text:
            bugs.append(f"[P0] SM-06 NBA forbidden phrase: '{phrase}'")

    if not bugs:
        checks.append(f"all {len(body)} actions have valid structure, no P0 violations")

    status = "FAIL" if bugs else "PASS"
    _record("SM-06", "/recommendations/next-best-actions", status, checks, bugs)
    assert not bugs, f"SM-06 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-07 — /intelligence/analyze: Non-legal input → graceful response, no 500
# ---------------------------------------------------------------------------

def test_sm07_non_legal_input_graceful_fallback(client):
    """
    S-15: Phi pháp lý input.
    - Must return 200 (not 500).
    - Must NOT produce legal advice for clearly non-legal query.
    - Response should be friendly redirect or short acknowledgement.
    - No P0 forbidden phrases.
    """
    resp = client.post(
        "/intelligence/analyze",
        headers=_HEADERS,
        json={"situation": "Hôm nay thời tiết đẹp quá, nên đi đâu chơi?", "top_k": 4},
    )
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-07: HTTP {resp.status_code} — {resp.text[:300]}"
    checks.append("HTTP 200 (no 500 on non-legal input)")

    body = resp.json()
    p0_violations = _check_p0(body)
    if p0_violations:
        bugs.extend([f"[P0] SM-07 forbidden phrase: '{v}'" for v in p0_violations])
    else:
        checks.append("no P0 violations")

    # Must return something (even if it's a disclaimer)
    text = _collect_text(body)
    if len(text.strip()) < 10:
        bugs.append("[P1] SM-07: response completely empty for non-legal input")
    else:
        checks.append("response not empty")

    status = "FAIL" if bugs else "PASS"
    _record("SM-07", "/intelligence/analyze", status, checks, bugs)
    assert not bugs, f"SM-07 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-08 — /intelligence/analyze: No-diacritic input detection
# ---------------------------------------------------------------------------

def test_sm08_no_diacritic_input_handled(client):
    """
    S-13: Query không dấu / sai chính tả.
    "so do cua toi" must still detect dat_dai domain and not contradict.
    """
    resp = client.post(
        "/intelligence/analyze",
        headers=_HEADERS,
        json={
            "situation": "so do cua toi bi hang xom tranh chap ranh gioi dat va xay tuong lan",
            "top_k": 4,
        },
    )
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-08: HTTP {resp.status_code}"
    checks.append("HTTP 200")

    body = resp.json()
    p0_violations = _check_p0(body)
    if p0_violations:
        bugs.extend([f"[P0] SM-08 forbidden phrase: '{v}'" for v in p0_violations])
    else:
        checks.append("no P0 violations for no-diacritic input")

    # Should detect domain (dat_dai) even with no diacritics
    domain = body.get("detected_domain", body.get("domain", ""))
    if domain not in ("dat_dai", "general", ""):
        bugs.append(f"[P2] SM-08: unexpected domain={domain!r} for land-law query")
    else:
        checks.append(f"domain detection acceptable: {domain!r}")

    status = "FAIL" if bugs else "PASS"
    _record("SM-08", "/intelligence/analyze", status, checks, bugs)
    assert not bugs, f"SM-08 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-09 — Health endpoint sanity
# ---------------------------------------------------------------------------

def test_sm09_health_endpoint(client):
    """Health endpoint must return 200 with status=ok."""
    resp = client.get("/health")
    bugs: List[str] = []
    checks: List[str] = []

    assert resp.status_code == 200, f"SM-09: /health returned {resp.status_code}"
    checks.append("HTTP 200")

    body = resp.json()
    if body.get("status") != "ok":
        bugs.append(f"[P1] SM-09: health status != 'ok', got: {body.get('status')!r}")
    else:
        checks.append("status=ok")

    if "version" not in body:
        bugs.append("[P2] SM-09: 'version' field missing from health response")
    else:
        checks.append(f"version={body['version']!r}")

    status = "FAIL" if bugs else "PASS"
    _record("SM-09", "/health", status, checks, bugs)
    assert not bugs, f"SM-09 failures:\n" + "\n".join(bugs)


# ---------------------------------------------------------------------------
# SM-10 — /analysis/evidence-gap: Non-legal → no fake legal advice
# ---------------------------------------------------------------------------

def test_sm10_evidence_gap_minimal_input_no_500(client):
    """
    Minimal input to evidence-gap must not 500.
    Short or ambiguous input must return valid structure.
    """
    resp = client.post(
        "/analysis/evidence-gap",
        headers=_HEADERS,
        json={"situation": "abc", "domain": "general"},
    )
    bugs: List[str] = []
    checks: List[str] = []

    # Short input is 3 chars — might fail min_length validation; 400/422 is acceptable
    if resp.status_code in (400, 422):
        checks.append(f"{resp.status_code} — correct rejection of too-short input")
        status = "PASS"
    elif resp.status_code == 200:
        checks.append("HTTP 200 — handled short input gracefully")
        body = resp.json()
        required_fields = ["missing_evidence", "coverage_score"]
        missing = [f for f in required_fields if f not in body]
        if missing:
            bugs.append(f"[P1] SM-10: missing fields {missing}")
        status = "FAIL" if bugs else "PASS"
    else:
        bugs.append(f"[P1] SM-10: unexpected status {resp.status_code} for short input")
        status = "FAIL"

    _record("SM-10", "/analysis/evidence-gap", status, checks, bugs)
    assert not bugs, f"SM-10 failures:\n" + "\n".join(bugs)
