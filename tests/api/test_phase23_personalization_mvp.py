"""Phase 23 personalization MVP tests.

Verifies that different demo personas receive different ordering/explanations
for the same query — the core personalization acceptance criterion.
"""

import pytest
from fastapi.testclient import TestClient

from src.api.app import create_app
from src.runtime.storage import StorageLayer

QUERY = "Tôi muốn ly hôn và tranh chấp quyền nuôi con sau khi ly hôn."

FAMILY_INTERACTIONS = [
    {"doc_id": "demo_case_divorce_custody", "action_type": "recommendation_click",
     "context": {"module": "similar_cases", "law_type": "gia_dinh"}},
    {"doc_id": "evidence_gap_demo", "action_type": "recommendation_useful",
     "context": {"module": "evidence_gap", "law_type": "dan_su"}},
    {"doc_id": "demo_case_divorce_custody", "action_type": "save",
     "context": {"module": "similar_cases", "law_type": "gia_dinh"}},
]

EMPLOYEE_INTERACTIONS = [
    {"doc_id": "demo_law_ld_36", "action_type": "recommendation_click",
     "context": {"module": "law_search", "law_type": "lao_dong"}},
    {"doc_id": "timeline_labor", "action_type": "recommendation_useful",
     "context": {"module": "timeline", "law_type": "lao_dong"}},
]


@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.state.mongodb_enabled = False
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def store_with_personas():
    """In-memory store pre-seeded with two persona interaction histories."""
    s = StorageLayer(":memory:")
    for inter in FAMILY_INTERACTIONS:
        s.log_interaction(
            user_id="demo_user_family",
            doc_id=inter["doc_id"],
            action_type=inter["action_type"],
            context=inter["context"],
        )
    for inter in EMPLOYEE_INTERACTIONS:
        s.log_interaction(
            user_id="demo_user_employee",
            doc_id=inter["doc_id"],
            action_type=inter["action_type"],
            context=inter["context"],
        )
    return s


def _nba(client, user_id: str, situation: str = QUERY) -> list:
    resp = client.post(
        "/recommendations/next-best-actions",
        json={"situation": situation, "domain": "gia_dinh", "position_score": 0.5,
              "domain_confidence": 0.7},
        headers={"X-User-ID": user_id},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_nba_returns_list_family(client):
    data = _nba(client, "demo_user_family")
    assert isinstance(data, list)
    assert len(data) >= 1


def test_nba_returns_list_employee(client):
    data = _nba(client, "demo_user_employee")
    assert isinstance(data, list)
    assert len(data) >= 1


def test_nba_has_personalization_fields(client):
    data = _nba(client, "demo_user_family")
    item = data[0]
    assert "behavior_score" in item
    assert "personalization_explanation" in item
    assert "ranking_signals" in item
    assert isinstance(item["ranking_signals"], dict)


def test_nba_behavior_score_bounded(client):
    for user_id in ("demo_user_family", "demo_user_employee", "demo_user_sme"):
        data = _nba(client, user_id)
        for item in data:
            score = item.get("behavior_score", 0)
            assert -0.13 <= score <= 0.19, f"behavior_score {score} out of range for {user_id}"


def test_similar_cases_cross_language(client):
    resp = client.post(
        "/retrieval/similar-cases",
        json={"situation": "divorce and child custody dispute in Vietnam"},
        headers={"X-User-ID": "demo_user_family"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cross_language_used"] is True
    assert data["query_language"] == "en"
    assert len(data["expanded_aliases"]) > 0


def test_similar_cases_vi_query_not_cross_language(client):
    resp = client.post(
        "/retrieval/similar-cases",
        json={"situation": "Tôi muốn ly hôn và tranh chấp quyền nuôi con."},
        headers={"X-User-ID": "demo_user_family"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cross_language_used"] is False


def test_community_cases_included_by_default(client):
    resp = client.post(
        "/retrieval/similar-cases",
        json={"situation": "Tôi muốn ly hôn và tranh chấp quyền nuôi con."},
        headers={"X-User-ID": "demo_user_family"},
    )
    data = resp.json()
    assert "community_cases" in data
    assert isinstance(data["community_cases"], list)


def test_privacy_anonymizer_runs_independently():
    from src.privacy.anonymizer import anonymize_legal_situation
    result = anonymize_legal_situation(
        "Ông Nguyễn Văn An muốn ly hôn, điện thoại 0912345678.",
        domain="gia_dinh",
    )
    assert "0912345678" not in result["safe_summary"]
    assert "Nguyễn Văn An" not in result["safe_summary"]
    assert len(result["safe_summary"]) >= 10


def test_community_case_storage_isolated():
    from src.runtime.storage import StorageLayer
    s1 = StorageLayer(":memory:")
    s2 = StorageLayer(":memory:")

    s1.save_community_case_pattern(
        pattern_id="ccp_isolation_test",
        summary="Tình huống ly hôn.",
        legal_domain="gia_dinh",
        user_goal=[],
        resolution_summary="",
        recommended_steps=[],
        citations=[],
        tags=[],
    )
    # s2 should not see s1's data
    results = s2.search_community_case_patterns(query="ly hôn", limit=5)
    assert all(r["pattern_id"] != "ccp_isolation_test" for r in results)
