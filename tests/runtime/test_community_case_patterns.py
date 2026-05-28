"""Tests for community case pattern storage (Phase 23)."""

import pytest
from src.runtime.storage import StorageLayer


@pytest.fixture
def store():
    return StorageLayer(":memory:")


def _seed(store: StorageLayer, pattern_id: str = "ccp_test_001") -> str:
    store.save_community_case_pattern(
        pattern_id=pattern_id,
        summary="Người dùng muốn ly hôn và nuôi con.",
        legal_domain="gia_dinh",
        user_goal=["divorce", "child_custody"],
        resolution_summary="Cần chuẩn bị hồ sơ ly hôn và chứng cứ điều kiện nuôi con.",
        recommended_steps=["Lấy giấy khai sinh", "Chuẩn bị chứng cứ thu nhập"],
        citations=["Luật HNGD 2014, Điều 81"],
        tags=["ly_hon", "nuoi_con", "gia_dinh"],
        source_user_segment="parent_custody",
    )
    return pattern_id


def test_save_returns_true_on_insert(store):
    result = store.save_community_case_pattern(
        pattern_id="ccp_new",
        summary="Tình huống mới.",
        legal_domain="lao_dong",
        user_goal=["termination"],
        resolution_summary="Cần thu thập hồ sơ.",
        recommended_steps=["Thu thập hợp đồng"],
        citations=[],
        tags=["lao_dong"],
    )
    assert result is True


def test_save_returns_false_on_duplicate(store):
    _seed(store)
    result = store.save_community_case_pattern(
        pattern_id="ccp_test_001",
        summary="Cập nhật lần 2.",
        legal_domain="gia_dinh",
        user_goal=[],
        resolution_summary="",
        recommended_steps=[],
        citations=[],
        tags=[],
    )
    assert result is False


def test_search_by_keyword(store):
    _seed(store)
    results = store.search_community_case_patterns(query="ly hôn nuôi con", limit=5)
    assert len(results) >= 1
    assert results[0]["summary"]


def test_search_by_domain(store):
    _seed(store, "ccp_family")
    store.save_community_case_pattern(
        pattern_id="ccp_labor",
        summary="Người lao động bị sa thải không báo trước.",
        legal_domain="lao_dong",
        user_goal=["termination"],
        resolution_summary="Yêu cầu bồi thường.",
        recommended_steps=["Gửi khiếu nại"],
        citations=["Bộ luật Lao động 2019"],
        tags=["sa_thai", "lao_dong"],
    )
    results = store.search_community_case_patterns(query="sa thải", domain="lao_dong", limit=5)
    assert any(r["legal_domain"] == "lao_dong" for r in results)


def test_search_does_not_return_raw_pii(store):
    store.save_community_case_pattern(
        pattern_id="ccp_clean",
        summary="Người dùng [TÊN] muốn ly hôn.",
        legal_domain="gia_dinh",
        user_goal=[],
        resolution_summary="Hướng giải quyết ly hôn.",
        recommended_steps=[],
        citations=[],
        tags=[],
    )
    results = store.search_community_case_patterns(query="ly hôn", limit=5)
    for r in results:
        assert "@" not in r["summary"], "PII email leaked"
        assert r.get("pattern_id") is not None


def test_increment_signal_useful(store):
    _seed(store)
    store.increment_community_case_signal("ccp_test_001", "useful")
    store.increment_community_case_signal("ccp_test_001", "useful")
    results = store.search_community_case_patterns(query="ly hôn", limit=5)
    row = next((r for r in results if r["pattern_id"] == "ccp_test_001"), None)
    assert row is not None
    assert row["popularity"]["useful"] >= 2


def test_increment_signal_clicks(store):
    _seed(store)
    store.increment_community_case_signal("ccp_test_001", "clicks")
    results = store.search_community_case_patterns(query="ly hôn", limit=5)
    row = next((r for r in results if r["pattern_id"] == "ccp_test_001"), None)
    assert row is not None
    assert row["popularity"]["clicks"] >= 1


def test_increment_invalid_signal_ignored(store):
    _seed(store)
    # Should not raise
    store.increment_community_case_signal("ccp_test_001", "invalid_signal")


def test_search_empty_query_returns_all(store):
    _seed(store)
    results = store.search_community_case_patterns(query="", limit=5)
    # Empty query = return most popular
    assert isinstance(results, list)


def test_result_has_expected_keys(store):
    _seed(store)
    results = store.search_community_case_patterns(query="ly hôn", limit=5)
    assert results
    row = results[0]
    for key in ["pattern_id", "summary", "legal_domain", "user_goal", "resolution_summary",
                "recommended_steps", "citations", "tags", "popularity"]:
        assert key in row, f"Missing key: {key}"
    assert isinstance(row["user_goal"], list)
    assert isinstance(row["recommended_steps"], list)
    assert isinstance(row["popularity"], dict)
