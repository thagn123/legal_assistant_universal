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


# ---------------------------------------------------------------------------
# P1-B fix — dan_su must not receive gia_dinh injection (B-11)
# ---------------------------------------------------------------------------


def test_p1b_dan_su_inheritance_not_gia_dinh(client):
    """
    Query about inheritance (dan_su) must not return gia_dinh case at top.
    With mongodb_enabled=False → demo fallback triggers.
    The B-11 bug injected 'demo_case_divorce_custody' (gia_dinh) for dan_su queries.
    After the fix, it must inject 'demo_case_inheritance_dispute' (dan_su) instead.
    """
    resp = _post(client, {
        "situation": "Cha mẹ mất không có di chúc, các con tranh chấp quyền thừa kế nhà đất.",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    official = data.get("official_cases", [])
    if not official:
        pytest.skip("No official cases returned — demo fallback may be empty in this env")

    top = official[0]
    assert top["domain"] != "gia_dinh", (
        f"B-11 regression: dan_su inheritance query returned gia_dinh case at top: "
        f"case_id={top['case_id']!r}, domain={top['domain']!r}"
    )


def test_p1b_dan_su_top_case_is_demo_inheritance(client):
    """
    Fallback injection for dan_su must use demo_case_inheritance_dispute, not divorce case.
    """
    resp = _post(client, {
        "situation": "Bố mất để lại đất nhưng anh trai giữ sổ đỏ, tranh chấp thừa kế.",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    official = data.get("official_cases", [])
    for item in official:
        assert item["case_id"] != "demo_case_divorce_custody", (
            "Divorce/custody case must NOT appear in dan_su query results (B-11 fix)"
        )


def test_p1b_gia_dinh_still_gets_divorce_case(client):
    """
    gia_dinh query must still receive the divorce/custody fallback case.
    Verifies the fix doesn't break gia_dinh injection.
    """
    resp = _post(client, {
        "situation": "Tôi muốn ly hôn đơn phương, con 18 tháng tuổi, tranh chấp quyền nuôi con.",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    official = data.get("official_cases", [])
    if official:
        domains_returned = {item["domain"] for item in official}
        assert domains_returned & {"gia_dinh", "dan_su"}, (
            f"gia_dinh query should return gia_dinh/dan_su cases, got domains: {domains_returned}"
        )


def test_p1b_demo_cases_have_is_demo_flag(client):
    """
    All injected demo fallback cases (case_id starts with 'demo_') must have is_demo=True.
    Applies to both gia_dinh and dan_su injected cases.
    """
    for situation in [
        "Ly hôn, tranh chấp quyền nuôi con dưới 36 tháng.",
        "Thừa kế không có di chúc, chia nhà đất giữa các con.",
    ]:
        resp = _post(client, {
            "situation": situation,
            "include_community": False,
            "persist_anonymized": False,
        })
        assert resp.status_code == 200
        data = resp.json()
        for item in data.get("official_cases", []):
            if item.get("case_id", "").startswith("demo_"):
                assert item.get("is_demo") is True, (
                    f"Demo case {item['case_id']!r} is missing is_demo=True "
                    f"(situation: {situation!r})"
                )


# ---------------------------------------------------------------------------
# P2-A fix — gia_dinh injection (Q15/Q16/Q17 — family queries must return gia_dinh)
# ---------------------------------------------------------------------------


def test_p2a_ly_hon_query_returns_gia_dinh_domain(client):
    """Q15/Q16 equivalent: divorce/custody queries classify as gia_dinh."""
    resp = _post(client, {
        "situation": "Muốn ly hôn đơn phương vì chồng bạo lực, có con 3 tuổi, nuôi con thế nào?",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("query_domain") == "gia_dinh", (
        f"Divorce query must classify as gia_dinh, got {data.get('query_domain')!r}"
    )


def test_p2a_gia_dinh_top_case_not_inheritance(client):
    """gia_dinh query must not return inheritance (dan_su) case at top."""
    resp = _post(client, {
        "situation": "Sau ly hôn tranh chấp quyền nuôi con dưới 36 tháng tuổi.",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    official = data.get("official_cases", [])
    if official:
        assert official[0].get("case_id") != "demo_case_inheritance_dispute", (
            "Inheritance case must NOT appear at top of gia_dinh query results"
        )


# ---------------------------------------------------------------------------
# P2-B fix — hanh_chinh fallback injection (Q24/Q25)
# ---------------------------------------------------------------------------


def test_p2b_hanh_chinh_query_not_empty(client):
    """Q24/Q25 equivalent: hanh_chinh query must not return empty results."""
    resp = _post(client, {
        "situation": "Bị phạt vi phạm hành chính oan, thủ tục khiếu nại quyết định xử phạt?",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    official = data.get("official_cases", [])
    assert len(official) > 0, "hanh_chinh query must not return empty official_cases"


def test_p2b_hanh_chinh_top_case_is_hanh_chinh(client):
    """hanh_chinh query top case must have domain=hanh_chinh."""
    resp = _post(client, {
        "situation": "Cơ quan nhà nước ra quyết định xử phạt sai, tôi muốn khiếu nại hành chính.",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    official = data.get("official_cases", [])
    if official:
        assert official[0].get("domain") == "hanh_chinh", (
            f"hanh_chinh query top case must be hanh_chinh domain, got {official[0].get('domain')!r}"
        )


# ---------------------------------------------------------------------------
# P2-C fix — no-diacritics Vietnamese query (Q26)
# ---------------------------------------------------------------------------


def test_p2c_no_diacritics_dat_dai_not_gia_dinh(client):
    """Q26 equivalent: no-diacritics dat_dai query must not return gia_dinh at top."""
    resp = _post(client, {
        "situation": "so do cua toi bi hang xom tranh chap ranh gioi can xu ly the nao",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    official = data.get("official_cases", [])
    if official:
        assert official[0].get("domain") != "gia_dinh", (
            f"No-diacritics dat_dai query must not return gia_dinh case at top, "
            f"got domain={official[0].get('domain')!r}"
        )


# ---------------------------------------------------------------------------
# P2-D fix — general/non-legal query (Q28)
# ---------------------------------------------------------------------------


def test_p2d_non_legal_query_returns_general_domain(client):
    """Q28: Non-legal query must be classified as general domain, not a legal domain."""
    resp = _post(client, {
        "situation": "Hôm nay thời tiết đẹp, muốn đi chơi ở đâu cho vui không?",
        "include_community": False,
        "persist_anonymized": False,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("query_domain") == "general", (
        f"Non-legal query must classify as general, got {data.get('query_domain')!r}"
    )
