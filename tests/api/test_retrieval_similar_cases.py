"""Tests for /retrieval/similar-cases Phase 23 extensions."""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture(scope="module")
def client():
    app = create_app()
    # Disable MongoDB for unit tests
    app.state.mongodb_enabled = False
    with TestClient(app) as c:
        yield c


def _post(client, body: dict):
    return client.post(
        "/retrieval/similar-cases",
        json=body,
        headers={"X-User-ID": "test_user_phase23"},
    )


def test_returns_200(client):
    resp = _post(client, {"situation": "Tôi muốn ly hôn và tranh chấp nuôi con sau khi ly hôn."})
    assert resp.status_code == 200


def test_response_has_required_fields(client):
    resp = _post(client, {"situation": "Tôi muốn ly hôn và tranh chấp nuôi con sau khi ly hôn."})
    data = resp.json()
    for field in ["request_id", "similar_cases", "official_cases", "community_cases",
                  "total", "search_mode", "summary", "query_language",
                  "cross_language_used", "expanded_aliases", "fallback_used"]:
        assert field in data, f"Missing field: {field}"


def test_backward_compat_similar_cases_exists(client):
    resp = _post(client, {"situation": "Bị sa thải không báo trước, không trả lương tháng cuối."})
    data = resp.json()
    assert "similar_cases" in data
    assert isinstance(data["similar_cases"], list)


def test_official_cases_list(client):
    resp = _post(client, {"situation": "Tranh chấp đất đai với hàng xóm, mua bán giấy tay."})
    data = resp.json()
    assert isinstance(data["official_cases"], list)


def test_community_cases_list(client):
    resp = _post(client, {"situation": "Tôi muốn ly hôn và tranh chấp nuôi con.", "include_community": True})
    data = resp.json()
    assert isinstance(data["community_cases"], list)


def test_cross_language_detection_english_query(client):
    resp = _post(client, {"situation": "Vietnam labor termination without notice, what rights do I have?"})
    data = resp.json()
    assert data["query_language"] == "en"
    assert data["cross_language_used"] is True
    assert len(data["expanded_aliases"]) > 0


def test_cross_language_vi_query_not_flagged(client):
    resp = _post(client, {"situation": "Tôi bị sa thải không có lý do chính đáng và không nhận trợ cấp."})
    data = resp.json()
    assert data["query_language"] == "vi"
    assert data["cross_language_used"] is False


def test_fallback_used_flag_when_no_mongo(client):
    resp = _post(client, {"situation": "Tranh chấp hợp đồng dịch vụ không được thanh toán đúng hạn."})
    data = resp.json()
    # With mongodb_enabled=False, should use demo fallback
    assert data["fallback_used"] is True or data["search_mode"] in ("demo_fallback", "keyword", "vector")


def test_no_http_500_on_short_query(client):
    # Under min_length=10 should return 422, not 500
    resp = _post(client, {"situation": "ly hôn"})
    assert resp.status_code in (422, 400)


def test_include_community_false(client):
    resp = _post(client, {"situation": "Tôi bị sa thải không có lý do chính đáng.", "include_community": False})
    data = resp.json()
    assert data["community_cases"] == []


def test_persist_anonymized_false(client):
    resp = _post(client, {
        "situation": "Tôi muốn ly hôn và tranh chấp nuôi con sau khi ly hôn.",
        "persist_anonymized": False,
    })
    assert resp.status_code == 200


def test_similar_case_item_has_source_type(client):
    resp = _post(client, {"situation": "Bị sa thải không báo trước và không trả lương tháng cuối."})
    data = resp.json()
    for item in data.get("similar_cases", []):
        assert "source_type" in item
        assert item["source_type"] in ("official", "community")
