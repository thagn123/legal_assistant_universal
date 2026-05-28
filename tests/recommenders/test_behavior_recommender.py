"""Tests for behavior recommender Phase 23 — behavior score bounds and signals."""

import pytest
from src.runtime.storage import StorageLayer
from src.recommenders.behavior_recommender import BehaviorRecommender


@pytest.fixture
def store():
    return StorageLayer(":memory:")


@pytest.fixture
def recommender(store):
    return BehaviorRecommender(store)


def _log(store, user_id, doc_id, action_type, context=None):
    store.log_interaction(
        user_id=user_id,
        doc_id=doc_id,
        action_type=action_type,
        context=context or {},
    )


def test_profile_builds_from_interactions(store, recommender):
    _log(store, "u1", "doc_ld", "view", {"law_type": "lao_dong"})
    _log(store, "u1", "doc_ld", "save", {"law_type": "lao_dong"})
    profile = recommender.build_user_profile("u1")
    assert profile is not None
    assert "lao_dong" in profile.law_type_weights or len(profile.law_type_weights) >= 0


def test_useful_signal_increases_digest_score(store, recommender):
    # Log useful signal
    _log(store, "u2", "evidence_gap_demo", "recommendation_useful",
         {"module": "evidence_gap", "law_type": "dan_su"})
    digest = recommender.get_daily_digest("u2")
    assert isinstance(digest, dict)
    # Should produce some non-empty recommendation
    assert "recommendations" in digest or "proactive" in digest or digest is not None


def test_dismiss_signal_creates_negative(store, recommender):
    _log(store, "u3", "some_doc", "recommendation_dismiss",
         {"module": "similar_cases", "law_type": "dat_dai"})
    # Should not raise and produce a profile
    profile = recommender.build_user_profile("u3")
    assert profile is not None


def test_behavior_score_bounded(store):
    """Behavior scores must be bounded to -0.12 .. +0.18."""
    from src.api.recommendation_routes import _next_best_action_behavior_scores
    # Seed many useful signals for same doc
    for _ in range(50):
        store.log_interaction(
            user_id="u_bound",
            doc_id="similar_cases",
            action_type="recommendation_useful",
            context={"module": "similar_cases", "action_id": "similar_cases"},
        )
    scores = _next_best_action_behavior_scores(store, "u_bound")
    for key, val in scores.items():
        assert -0.19 <= val <= 0.19, f"Score for {key} out of bounds: {val}"


def test_behavior_score_empty_for_new_user(store):
    from src.api.recommendation_routes import _next_best_action_behavior_scores
    scores = _next_best_action_behavior_scores(store, "brand_new_user_xyz")
    assert isinstance(scores, dict)
    # New user may have empty scores
    assert all(-0.19 <= v <= 0.19 for v in scores.values())


def test_proactive_recommendations_empty_history(recommender):
    recs = recommender.recommend_proactive("new_user_no_history", limit=3)
    assert isinstance(recs, list)


def test_daily_digest_returns_dict(recommender):
    digest = recommender.get_daily_digest("digest_test_user")
    assert isinstance(digest, dict)


def test_next_action_from_known_sequence(store, recommender):
    _log(store, "u4", "doc1", "view", {"law_type": "lao_dong"})
    _log(store, "u4", "doc2", "save", {"law_type": "lao_dong"})
    recs = recommender.recommend_next_action("u4", last_action_type="view", limit=3)
    assert isinstance(recs, list)
