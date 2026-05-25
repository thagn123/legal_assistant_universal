from __future__ import annotations

from src.recommenders.next_best_action import (
    NextBestActionRecommender,
    build_recommendation_context,
)


def test_low_evidence_prioritizes_evidence_gap_and_law_search():
    ctx = build_recommendation_context(
        situation="Toi mua dat bang giay tay, chua sang ten va ben ban doi lai dat.",
        domain="dat_dai",
        position_score=0.32,
        domain_confidence=0.8,
        citations=[],
        warnings=["Can bo sung can cu phap ly."],
        recommended_actions=["Thu thap giay to dat."],
        risk_assessment={"risks": ["Giao dich giay tay"], "risk_count": 1},
    )

    results = NextBestActionRecommender().recommend(ctx, limit=4)
    ids = [item.action_id for item in results]

    assert ids[0] == "evidence_gap"
    assert "law_search" in ids
    assert results[0].priority == "high"
    assert results[0].blocking_gaps


def test_contract_context_promotes_contract_review():
    ctx = build_recommendation_context(
        situation="Hop dong dat coc mua ban nha co phat vi pham 30%.",
        domain="hop_dong",
        position_score=0.68,
        domain_confidence=0.9,
        citations=["Bo luat Dan su 2015 - Dieu 328"],
        warnings=[],
        recommended_actions=["Ra soat dieu khoan phat vi pham."],
    )

    results = NextBestActionRecommender().recommend(ctx, limit=5)
    ids = [item.action_id for item in results]

    assert "contract_review" in ids
    contract = next(item for item in results if item.action_id == "contract_review")
    assert contract.score >= 0.5
    assert contract.action_url == "/contract"


def test_behavior_feedback_can_rerank_next_best_actions():
    ctx = build_recommendation_context(
        situation="Toi can xu ly tranh chap va muon biet buoc tiep theo.",
        domain="dan_su",
        position_score=0.6,
        domain_confidence=0.8,
        citations=["Bo luat Dan su 2015"],
        warnings=[],
        recommended_actions=["Lap ke hoach lam viec."],
    )

    baseline = NextBestActionRecommender().recommend(ctx, limit=6)
    personalized = NextBestActionRecommender().recommend(
        ctx,
        limit=6,
        behavior_scores={"action_plan": 0.18, "evidence_gap": -0.12},
    )

    assert personalized[0].action_id == "action_plan"
    assert next(item for item in personalized if item.action_id == "action_plan").score > next(
        item for item in baseline if item.action_id == "action_plan"
    ).score


def test_divorce_custody_context_adds_goal_aware_metadata():
    ctx = build_recommendation_context(
        situation=(
            "Toi muon ly hon, co hai con, muon nuoi con va giu tai san. "
            "Thu nhap cua toi cao hon vo va can biet tai san chia the nao."
        ),
        domain="dan_su",
        position_score=0.45,
        domain_confidence=0.8,
        citations=["Luat Hon nhan va Gia dinh 2014"],
        warnings=["Can bo sung chung cu ve dieu kien nuoi con."],
        recommended_actions=["Chuan bi ho so ly hon."],
    )

    results = NextBestActionRecommender().recommend(ctx, limit=5)
    first = results[0]

    assert "divorce" in first.detected_goals
    assert "child_custody" in first.detected_goals
    assert "asset_division" in first.detected_goals
    assert first.user_position == "parent_seeking_custody"
    assert any("con" in question.lower() for question in first.next_questions)
    assert first.journey_steps
    assert {"action_plan", "evidence_gap"}.intersection({item.action_id for item in results[:3]})
