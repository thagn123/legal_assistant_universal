"""
T-THR tests — verify vector_score >= 0.55 threshold actually filters results.

Strategy:
- Patch _get_vector_storage() to inject a _MockVS with controlled scores.
- Patch embed_text to return a fixed vector (no model load, no real MongoDB).
- Use include_community=False, persist_anonymized=False for similar-cases routes.
- Assert on actual kept/dropped chunk/case IDs — not just HTTP status codes.

Filters under test:
  retrieval_routes.py:410  — search_laws post-vector filter
  retrieval_routes.py:576  — find_similar_cases post-vector filter
  retrieval_fusion.py:139  — Signal 1 per-chunk guard
  retrieval_routes.py:670+ — domain-priority sort (T-THR-5)
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.api.app import create_app

# Fake 384-dim embedding — direction irrelevant for mock VS tests
_FAKE_EMBEDDING = [0.0] * 384
_HEADERS = {"X-User-ID": "thr_test_user"}


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class _MockVS:
    """Fixed-response mock that returns controlled chunks/cases regardless of query args."""

    def __init__(self, chunks=None, cases=None):
        self._chunks = list(chunks or [])
        self._cases = list(cases or [])

    def vector_search_chunks(self, *args, **kwargs):
        return self._chunks[:]

    def keyword_search_chunks(self, *args, **kwargs):
        return []

    def vector_search_cases(self, *args, **kwargs):
        return self._cases[:]

    def keyword_search_cases(self, *args, **kwargs):
        return []

    def get_user_law_types(self, *args, **kwargs):
        return []

    def search_community_case_patterns(self, *args, **kwargs):
        return []

    def save_community_case_pattern(self, *args, **kwargs):
        pass


def _law_chunk(chunk_id: str, score: float, law_type: str = "dat_dai") -> dict:
    return {
        "chunk_id": chunk_id,
        "doc_id": f"doc_{chunk_id}",
        "law_reference": f"Điều {chunk_id}",
        "law_type": law_type,
        "content": f"Nội dung điều luật {chunk_id} về tranh chấp đất đai.",
        "vector_score": score,
        "is_global": True,
    }


def _case(case_id: str, score: float, law_type: str = "dat_dai") -> dict:
    return {
        "case_id": case_id,
        "title": f"Vụ {case_id}",
        "situation_summary": f"Tranh chấp {case_id} liên quan đến {law_type}.",
        "outcome": "Thắng kiện",
        "lesson": "Bài học từ vụ việc",
        "law_type": law_type,
        "stage": "dispute",
        "key_laws": [],
        "vector_score": score,
    }


def _make_app():
    """Fresh app with MongoDB disabled so startup does not attempt a real connection."""
    app = create_app()
    app.state.mongodb_enabled = False
    return app


# ---------------------------------------------------------------------------
# T-THR-1 — search_laws keeps score >= 0.55, drops < 0.55
# ---------------------------------------------------------------------------


def test_thr1_search_laws_filters_low_score():
    """
    Mock VS returns 4 chunks with scores [0.72, 0.58, 0.54, 0.30].
    The inline filter at retrieval_routes.py:410 must keep [0.72, 0.58] only.
    """
    chunks = [
        _law_chunk("c_72", 0.72),
        _law_chunk("c_58", 0.58),
        _law_chunk("c_54", 0.54),   # below 0.55 — must be dropped
        _law_chunk("c_30", 0.30),   # well below — must be dropped
    ]
    mock_vs = _MockVS(chunks=chunks)

    with patch("src.api.retrieval_routes._get_vector_storage", return_value=mock_vs), \
         patch("src.pipeline.embedding_stage.embed_text", return_value=_FAKE_EMBEDDING):
        with TestClient(_make_app(), raise_server_exceptions=True) as client:
            resp = client.post(
                "/retrieval/laws",
                json={"query": "Tranh chấp đất đai hàng xóm lấn chiếm ranh giới."},
                headers=_HEADERS,
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    result_ids = {r["chunk_id"] for r in data["results"]}
    assert "c_72" in result_ids, "Score 0.72 must be kept (above threshold)"
    assert "c_58" in result_ids, "Score 0.58 must be kept (at boundary — 0.58 >= 0.55)"
    assert "c_54" not in result_ids, (
        f"Score 0.54 must be filtered (0.54 < 0.55). Got result_ids: {result_ids}"
    )
    assert "c_30" not in result_ids, (
        f"Score 0.30 must be filtered. Got result_ids: {result_ids}"
    )
    assert data["total"] == 2, (
        f"Expected total=2 after 0.55 filter, got {data['total']}. result_ids: {result_ids}"
    )


# ---------------------------------------------------------------------------
# T-THR-2 — find_similar_cases keeps score >= 0.55, drops < 0.55
# ---------------------------------------------------------------------------


def test_thr2_similar_cases_filters_low_score():
    """
    Mock VS returns 4 cases with scores [0.72, 0.58, 0.54, 0.30].
    The inline filter at retrieval_routes.py:576 must keep [0.72, 0.58] only.
    """
    cases = [
        _case("case_72", 0.72),
        _case("case_58", 0.58),
        _case("case_54", 0.54),   # must be dropped
        _case("case_30", 0.30),   # must be dropped
    ]
    mock_vs = _MockVS(cases=cases)

    with patch("src.api.retrieval_routes._get_vector_storage", return_value=mock_vs), \
         patch("src.pipeline.embedding_stage.embed_text", return_value=_FAKE_EMBEDDING):
        with TestClient(_make_app(), raise_server_exceptions=True) as client:
            resp = client.post(
                "/retrieval/similar-cases",
                json={
                    "situation": "Hàng xóm lấn chiếm đất tranh chấp ranh giới đất đai.",
                    "include_community": False,
                    "persist_anonymized": False,
                },
                headers=_HEADERS,
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    official_ids = {c["case_id"] for c in data["official_cases"]}
    assert "case_72" in official_ids, "Score 0.72 must be kept"
    assert "case_58" in official_ids, "Score 0.58 must be kept"
    assert "case_54" not in official_ids, (
        f"Score 0.54 must be filtered. Got official_ids: {official_ids}"
    )
    assert "case_30" not in official_ids, (
        f"Score 0.30 must be filtered. Got official_ids: {official_ids}"
    )


# ---------------------------------------------------------------------------
# T-THR-3 — all candidates below threshold → fallback triggered, no leakage
# ---------------------------------------------------------------------------


def test_thr3_all_below_threshold_triggers_fallback():
    """
    All mock cases have score < 0.55. After the filter, raw=[] → keyword search
    (also returns []) → demo fallback. The original low-score cases must not appear.
    Response must declare fallback_used=True or search_mode in (demo_fallback, keyword).
    Any injected demo cases must carry is_demo=True.
    """
    cases = [
        _case("bad_1", 0.32, law_type="lao_dong"),
        _case("bad_2", 0.44, law_type="lao_dong"),
        _case("bad_3", 0.51, law_type="lao_dong"),   # closest but still < 0.55
    ]
    mock_vs = _MockVS(cases=cases)

    with patch("src.api.retrieval_routes._get_vector_storage", return_value=mock_vs), \
         patch("src.pipeline.embedding_stage.embed_text", return_value=_FAKE_EMBEDDING):
        with TestClient(_make_app(), raise_server_exceptions=True) as client:
            resp = client.post(
                "/retrieval/similar-cases",
                json={
                    "situation": "Bị sa thải không có lý do chính đáng, công ty không trả lương.",
                    "include_community": False,
                    "persist_anonymized": False,
                },
                headers=_HEADERS,
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Original low-score cases must not leak into results
    bad_ids = {"bad_1", "bad_2", "bad_3"}
    returned_ids = {c["case_id"] for c in data["official_cases"]}
    leaked = bad_ids & returned_ids
    assert not leaked, (
        f"Cases with score < 0.55 leaked into results despite threshold filter: {leaked}"
    )

    # Fallback must be declared (or result is empty)
    uses_fallback = (
        data.get("fallback_used") is True
        or data.get("search_mode") in ("demo_fallback", "keyword")
    )
    is_empty = data["total"] == 0
    assert uses_fallback or is_empty, (
        f"Expected fallback_used=True or empty response, got: "
        f"fallback_used={data.get('fallback_used')!r}, "
        f"search_mode={data.get('search_mode')!r}, total={data['total']}"
    )

    # Any demo case must be labelled is_demo=True
    for item in data["official_cases"]:
        if item.get("case_id", "").startswith("demo_"):
            assert item.get("is_demo") is True, (
                f"Demo case {item['case_id']!r} is missing is_demo=True"
            )


# ---------------------------------------------------------------------------
# T-THR-4 — retrieval_fusion Signal 1 rejects chunks below 0.55 (direct unit test)
# ---------------------------------------------------------------------------


def test_thr4_fusion_signal1_drops_low_score_chunk():
    """
    RetrievalFusionEngine.fuse() with a mock VS that returns:
      - chunk_A: vector_score=0.70 → must enter candidates from Signal 1
      - chunk_B: vector_score=0.53 → must be SKIPPED (retrieval_fusion.py:139)
    BM25 returns [] → chunk_B has no alternative entry path.
    Asserts: chunk_A in results, chunk_B absent, vector_hits == 1.
    """
    from src.engine.query_planner import QueryPlan
    from src.engine.retrieval_fusion import RetrievalFusionEngine

    class _FusionMockVS:
        def vector_search_chunks(self, *args, **kwargs):
            return [
                {
                    "chunk_id": "chunk_A",
                    "doc_id": "doc_A",
                    "content": "Nội dung điều luật A về tranh chấp đất đai.",
                    "law_type": "dat_dai",
                    "law_reference": "Điều 166 Luật Đất Đai 2013",
                    "vector_score": 0.70,
                    "is_global": True,
                },
                {
                    "chunk_id": "chunk_B",
                    "doc_id": "doc_B",
                    "content": "Điều khoản khiếu nại về đất đai.",
                    "law_type": "dat_dai",
                    "law_reference": "Điều 204 Luật Đất Đai 2013",
                    "vector_score": 0.53,   # below 0.55 — Signal 1 must reject this
                    "is_global": True,
                },
            ]

        def keyword_search_chunks(self, *args, **kwargs):
            return []   # no BM25 hits → chunk_B has no back-door entry

        def get_user_law_types(self, *args, **kwargs):
            return []

    plan = QueryPlan(
        plan_id="thr4_test",
        original_query="Tranh chấp ranh giới đất đai hàng xóm.",
        detected_domain="dat_dai",
        domain_confidence=0.85,
        extracted_entities={
            "laws": [], "parties": [], "amounts": [], "dates": [], "locations": []
        },
        dispute_type="boundary",
        retrieval_strategy=["vector", "bm25"],
        query_variants=["Tranh chấp ranh giới đất đai hàng xóm."],
        requires_graph_expansion=False,
        requires_case_retrieval=False,
        requires_risk_analysis=False,
        planned_at=datetime.now(timezone.utc).isoformat(),
    )

    engine = RetrievalFusionEngine(vector_storage=_FusionMockVS())

    with patch("src.engine.retrieval_fusion.embed_text", return_value=_FAKE_EMBEDDING):
        result_set = engine.fuse(plan, user_id="thr_test_user", limit=10)

    candidate_ids = {r.item_id for r in result_set.results}

    assert "chunk_A" in candidate_ids, (
        f"chunk_A (score 0.70) must be accepted by Signal 1. Candidates: {candidate_ids}"
    )
    assert "chunk_B" not in candidate_ids, (
        f"chunk_B (score 0.53 < 0.55) must be rejected by Signal 1 threshold. "
        f"Got candidates: {candidate_ids}"
    )
    assert result_set.vector_hits == 1, (
        f"vector_hits must be 1 (only chunk_A passed 0.55 threshold), "
        f"got {result_set.vector_hits}"
    )


# ---------------------------------------------------------------------------
# T-THR-5 — same-domain case leads over cross-domain high-score case
# ---------------------------------------------------------------------------


def test_thr5_cross_domain_domain_priority_over_raw_score():
    """
    Query domain = dat_dai. Mock VS returns 3 cases (scores already above 0.55,
    so no case is dropped by the threshold filter):
      - lao_dong: 0.70 (highest score, wrong domain for dat_dai query)
      - gia_dinh: 0.62 (cross-domain — not in _allowed_domains("dat_dai"))
      - dat_dai:  0.60 (correct domain, lowest of the three)

    After domain-priority sort (retrieval_routes.py ~line 671):
      official_cases[0].domain must be "dat_dai", not "lao_dong".
      A cross-domain case with higher raw score must not top the list.
    """
    cases = [
        _case("lao_case_70", 0.70, law_type="lao_dong"),   # cross-domain, highest score
        _case("gd_case_62", 0.62, law_type="gia_dinh"),    # cross-domain for dat_dai
        _case("dat_case_60", 0.60, law_type="dat_dai"),    # same domain, lowest score
    ]
    mock_vs = _MockVS(cases=cases)

    with patch("src.api.retrieval_routes._get_vector_storage", return_value=mock_vs), \
         patch("src.pipeline.embedding_stage.embed_text", return_value=_FAKE_EMBEDDING):
        with TestClient(_make_app(), raise_server_exceptions=True) as client:
            resp = client.post(
                "/retrieval/similar-cases",
                json={
                    "situation": "Hàng xóm lấn chiếm đất tranh chấp ranh giới đất đai.",
                    "domain_hint": "dat_dai",
                    "include_community": False,
                    "persist_anonymized": False,
                },
                headers=_HEADERS,
            )

    assert resp.status_code == 200, resp.text
    data = resp.json()

    official = data["official_cases"]
    assert len(official) >= 1, f"Expected at least 1 official case, got empty list"

    top = official[0]
    assert top["domain"] == "dat_dai", (
        f"T-THR-5 FAIL: dat_dai case (score 0.60) must lead over cross-domain "
        f"lao_dong (0.70) and gia_dinh (0.62) when query domain is dat_dai. "
        f"Got top: domain={top['domain']!r}, case_id={top['case_id']!r}, "
        f"score={top['similarity_score']}"
    )
    assert top["case_id"] != "lao_case_70", (
        "lao_dong high-score case must not lead the list when a dat_dai case exists"
    )
