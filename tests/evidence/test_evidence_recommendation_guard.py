from __future__ import annotations

from src.evidence.evidence_gap_engine import (
    analyze_evidence_gap,
    filter_contradictory_recommendations,
)


def test_guard_rewrites_supplement_action_for_present_evidence():
    gap = analyze_evidence_gap("tôi đã có sổ đỏ và biên lai chuyển khoản", domain="dat_dai")

    guarded = filter_contradictory_recommendations(
        [
            "Bạn cần bổ sung sổ đỏ.",
            "Thu thập biên lai thanh toán.",
            "Liên hệ UBND xã để xin xác nhận.",
        ],
        gap.present_evidence,
    )

    joined = " ".join(guarded).lower()
    assert "cần bổ sung sổ đỏ" not in joined
    assert "thu thập biên lai" not in joined
    assert "bạn đã có" in joined
    assert "ubnd" in joined


def test_gap_recommendations_do_not_ask_for_present_documents():
    result = analyze_evidence_gap(
        "Tranh chấp đất đai. tôi đã có sổ đỏ, Biên lai hoặc chứng từ thanh toán tiền mua đất",
        domain="land",
    )

    joined = " ".join(result.recommendations).lower()
    assert "bổ sung sổ đỏ" not in joined
    assert "bổ sung biên lai" not in joined
    assert "bạn đã có sổ đỏ" in joined
