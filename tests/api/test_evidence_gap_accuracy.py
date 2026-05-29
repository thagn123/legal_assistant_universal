from __future__ import annotations

from fastapi.testclient import TestClient

from src.api.app import create_app


def test_evidence_gap_api_does_not_report_present_so_do_missing():
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)

    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "evidence_accuracy_user"},
            json={
                "situation": (
                    "Tranh chấp về tài sản thừa kế đất đai giữa các anh chị em ruột. "
                    "tôi đã có sổ đỏ, Biên lai hoặc chứng từ thanh toán tiền mua đất"
                ),
                "domain": "land",
                "facts": [],
            },
        )

    assert resp.status_code == 200
    body = resp.json()
    missing_titles = {item["item"] for item in body["missing_evidence"]}
    present_titles = {item["item"] for item in body["present_evidence"]}

    assert not any("Sổ đỏ" in title for title in missing_titles)
    assert not any("Biên lai" in title for title in missing_titles)
    assert any("Sổ đỏ" in title for title in present_titles)
    assert any("Biên lai" in title for title in present_titles)
    assert body["coverage_score"] > 0.33


def test_evidence_gap_api_possessive_so_do_not_missing():
    """T02: 'sổ đỏ của tôi' → land_certificate must NOT appear in missing_evidence."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "t02_user"},
            json={
                "situation": "sổ đỏ của tôi bị hàng xóm tranh chấp ranh giới đất",
                "domain": "dat_dai",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    missing_ids = {item.get("evidence_id", "") for item in body["missing_evidence"]}
    present_ids = {item.get("evidence_id", "") for item in body["present_evidence"]}
    assert "land_certificate" not in missing_ids, (
        "T02 FAIL: land_certificate in missing when possessive phrase used"
    )
    assert "land_certificate" in present_ids, (
        "T02 FAIL: land_certificate not in present when possessive phrase used"
    )


def test_evidence_gap_api_labor_possessive_not_missing():
    """T03: 'hợp đồng lao động của tôi' → labor_contract must NOT appear in missing_evidence."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "t03_user"},
            json={
                "situation": "hợp đồng lao động của tôi bị vi phạm nghiêm trọng",
                "domain": "lao_dong",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    missing_ids = {item.get("evidence_id", "") for item in body["missing_evidence"]}
    present_ids = {item.get("evidence_id", "") for item in body["present_evidence"]}
    assert "labor_contract" not in missing_ids, (
        "T03 FAIL: labor_contract in missing when possessive phrase used"
    )
    assert "labor_contract" in present_ids, (
        "T03 FAIL: labor_contract not in present when possessive phrase used"
    )


def test_evidence_gap_api_recommendations_no_present_conflict():
    """T04: recommendations must not ask to collect evidence already PRESENT."""
    app = create_app(db_path=":memory:", use_real_pipeline=False, use_mongodb=False)
    with TestClient(app) as client:
        resp = client.post(
            "/analysis/evidence-gap",
            headers={"X-User-ID": "t04_user"},
            json={
                "situation": "Tôi đã có sổ đỏ và biên lai chuyển khoản, hàng xóm đang lấn đất",
                "domain": "dat_dai",
                "facts": [],
            },
        )
    assert resp.status_code == 200
    body = resp.json()
    recs = " ".join(body.get("recommendations", [])).lower()
    BAD = [
        "thu thập sổ đỏ", "bổ sung sổ đỏ", "xin cấp sổ đỏ", "cần có sổ đỏ",
        "thu thập biên lai", "bổ sung biên lai", "nộp thêm biên lai",
    ]
    for bad in BAD:
        assert bad not in recs, f"T04 FAIL: bad recommendation '{bad}' found in: {recs[:300]}"
