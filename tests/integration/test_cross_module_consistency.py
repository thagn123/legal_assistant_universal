"""
Integration tests for cross-module consistency:
- Evidence Gap API → no contradictory recommendations for PRESENT evidence
- NBA API → accepts session_id field without 422
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_evidence_gap_present_no_supplement_recommendation():
    """
    When land_certificate is PRESENT, recommendations must not ask to collect it.
    Covers the cross-module contradiction regression (B-1 from deep_audit_v2).
    """
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "integration_cm_001"},
            json={
                "situation": "Tôi đã có sổ đỏ, hàng xóm xây tường lấn 50cm",
                "domain": "dat_dai",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()

    present_ids = {item.get("evidence_id", "") for item in body["present_evidence"]}
    assert "land_certificate" in present_ids, (
        "land_certificate must be PRESENT for 'Tôi đã có sổ đỏ'"
    )

    BAD_PATTERNS = [
        "thu thập sổ đỏ", "bổ sung sổ đỏ", "xin cấp sổ đỏ",
        "cần có sổ đỏ", "nộp thêm sổ đỏ", "xin cấp lần đầu",
    ]
    recs = " ".join(body.get("recommendations", [])).lower()
    for bad in BAD_PATTERNS:
        assert bad not in recs, (
            f"Cross-module contradiction: '{bad}' in recommendations despite land_certificate PRESENT"
        )


def test_nba_endpoint_accepts_session_id():
    """NBA endpoint must accept session_id field (not return 422)."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/recommendations/next-best-actions",
            headers={"X-User-ID": "integration_cm_002"},
            json={
                "situation": "Tôi đã có sổ đỏ, hàng xóm lấn đất",
                "domain": "dat_dai",
                "session_id": "test_session_abc123",
                "recommended_actions": ["Thu thập sổ đỏ hoặc GCN QSDĐ"],
                "limit": 4,
            },
        )
    assert resp.status_code != 422, (
        f"NBA endpoint rejected session_id field (422): {resp.json()}"
    )
    assert resp.status_code == 200, (
        f"NBA endpoint returned unexpected status {resp.status_code}: {resp.text[:300]}"
    )


def test_nba_without_session_id_still_works():
    """NBA must still work normally when session_id is omitted (backward-compat)."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/recommendations/next-best-actions",
            headers={"X-User-ID": "integration_cm_003"},
            json={
                "situation": "Tôi bị sa thải không có lý do",
                "domain": "lao_dong",
                "limit": 4,
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list), "NBA should return a list of actions"
