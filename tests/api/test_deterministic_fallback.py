"""Tests for deterministic fallback behavior (Phase 23).

Verifies that when AI key and MongoDB are unavailable,
the system does NOT return HTTP 500 for normal legal queries.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app


@pytest.fixture(scope="module")
def client_no_mongo():
    app = create_app()
    app.state.mongodb_enabled = False
    with TestClient(app) as c:
        yield c


LEGAL_QUERY = "Tôi muốn ly hôn và tranh chấp quyền nuôi con."
LABOR_QUERY = "Tôi bị sa thải không có văn bản giải thích và không được trả trợ cấp."
CONTRACT_QUERY = "Hợp đồng dịch vụ bị vi phạm, đối tác không thanh toán sau 30 ngày."


def test_similar_cases_no_500(client_no_mongo):
    resp = client_no_mongo.post(
        "/retrieval/similar-cases",
        json={"situation": LEGAL_QUERY},
        headers={"X-User-ID": "fallback_test_user"},
    )
    assert resp.status_code != 500, f"Got 500: {resp.text}"
    assert resp.status_code == 200


def test_similar_cases_has_fallback_flag(client_no_mongo):
    resp = client_no_mongo.post(
        "/retrieval/similar-cases",
        json={"situation": LEGAL_QUERY},
        headers={"X-User-ID": "fallback_test_user"},
    )
    data = resp.json()
    # Should either use demo fallback or keyword with fallback_used flag
    assert isinstance(data.get("fallback_used"), bool)


def test_law_search_no_500(client_no_mongo):
    resp = client_no_mongo.post(
        "/retrieval/laws",
        json={"query": LABOR_QUERY},
        headers={"X-User-ID": "fallback_test_user"},
    )
    assert resp.status_code != 500


def test_law_search_returns_results_or_empty(client_no_mongo):
    resp = client_no_mongo.post(
        "/retrieval/laws",
        json={"query": LEGAL_QUERY},
        headers={"X-User-ID": "fallback_test_user"},
    )
    data = resp.json()
    assert isinstance(data.get("results"), list)
    assert data.get("total", -1) >= 0


def test_next_best_actions_no_500(client_no_mongo):
    resp = client_no_mongo.post(
        "/recommendations/next-best-actions",
        json={
            "situation": LEGAL_QUERY,
            "domain": "gia_dinh",
            "position_score": 0.6,
            "domain_confidence": 0.8,
        },
        headers={"X-User-ID": "fallback_test_user"},
    )
    assert resp.status_code != 500


def test_next_best_actions_returns_list(client_no_mongo):
    resp = client_no_mongo.post(
        "/recommendations/next-best-actions",
        json={
            "situation": LABOR_QUERY,
            "domain": "lao_dong",
            "position_score": 0.45,
            "domain_confidence": 0.7,
        },
        headers={"X-User-ID": "fallback_test_user"},
    )
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_next_best_actions_has_phase23_fields(client_no_mongo):
    resp = client_no_mongo.post(
        "/recommendations/next-best-actions",
        json={
            "situation": CONTRACT_QUERY,
            "domain": "hop_dong",
            "position_score": 0.5,
            "domain_confidence": 0.6,
        },
        headers={"X-User-ID": "fallback_test_user"},
    )
    data = resp.json()
    assert isinstance(data, list)
    if data:
        item = data[0]
        assert "behavior_score" in item
        assert "personalization_explanation" in item
        assert "ranking_signals" in item


def test_recommendations_situation_no_500(client_no_mongo):
    resp = client_no_mongo.post(
        "/recommendations/situation",
        json={"situation": LEGAL_QUERY, "user_role": "nguyen_don"},
        headers={"X-User-ID": "fallback_test_user"},
    )
    assert resp.status_code != 500


def test_behavior_digest_no_500(client_no_mongo):
    resp = client_no_mongo.get(
        "/recommendations/behavior/digest",
        headers={"X-User-ID": "fallback_test_user"},
    )
    assert resp.status_code != 500


def test_behavior_profile_no_500(client_no_mongo):
    resp = client_no_mongo.get(
        "/recommendations/behavior/profile",
        headers={"X-User-ID": "fallback_test_user"},
    )
    assert resp.status_code != 500
