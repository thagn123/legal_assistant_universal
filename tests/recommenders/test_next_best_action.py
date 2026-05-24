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
