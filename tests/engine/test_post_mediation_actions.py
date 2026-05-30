"""
Regression tests for S-05 P0 fix — dat_dai post-mediation action suppression.

Bug: recommended_actions template for dat_dai always included "Nộp đơn yêu cầu hòa giải
tại UBND cấp xã" even when the user stated mediation was already completed / failed.

Fix: _is_post_mediation_failed() detects completion phrases → _generate_recommendations()
swaps to _DAT_DAI_POST_MEDIATION_ACTIONS, which never contains the mediation step.
"""
from __future__ import annotations

import pytest

from src.engine.orchestrator import (
    _DAT_DAI_POST_MEDIATION_ACTIONS,
    _DOMAIN_RECOMMENDED_ACTIONS,
    _generate_recommendations,
    _is_post_mediation_failed,
)
from src.engine.query_planner import QueryPlanner

_planner = QueryPlanner()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_MEDIATION_PHRASES = [
    "nộp đơn yêu cầu hòa giải",
    "hòa giải tại ubnd",
    "yêu cầu hòa giải tại ubnd",
    "thực hiện hòa giải",
]


def _contains_ubnd_mediation(actions: list[str]) -> bool:
    """True if any action re-suggests the UBND mediation step."""
    joined = " ".join(actions).lower()
    return any(phrase in joined for phrase in _MEDIATION_PHRASES)


def _contains_post_mediation_guidance(actions: list[str]) -> bool:
    """True if at least one action points toward court filing or preserving biên bản."""
    joined = " ".join(actions).lower()
    keywords = [
        "biên bản hòa giải không thành",
        "khởi kiện",
        "tòa án nhân dân",
        "hồ sơ khởi kiện",
    ]
    return any(kw in joined for kw in keywords)


# ---------------------------------------------------------------------------
# _is_post_mediation_failed — unit tests for the detector
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("situation", [
    "Tôi đã hòa giải ở xã nhưng không thành, hàng xóm vẫn lấn đất và không ký biên bản.",
    "Hòa giải không thành, tôi cần làm gì tiếp theo?",
    "Biên bản hòa giải không thành đã có, bước tiếp theo là gì?",
    "UBND xã hòa giải không thành, bên kia vẫn lấn chiếm.",
    "Đã hòa giải tại UBND rồi nhưng không đi đến kết quả.",
    "Hòa giải rồi nhưng hàng xóm không ký biên bản.",
    "Không ký biên bản hòa giải, bên kia cứ từ chối.",
    "Bên kia không ký biên bản, tôi phải làm gì?",
])
def test_detector_true_for_post_mediation(situation: str):
    assert _is_post_mediation_failed(situation), (
        f"Expected _is_post_mediation_failed=True for: {situation!r}"
    )


@pytest.mark.parametrize("situation", [
    "Hàng xóm lấn đất 50cm, tôi đã có sổ đỏ nhưng chưa làm việc với UBND xã.",
    "Tranh chấp ranh giới đất, tôi chưa biết phải làm gì.",
    "Hàng xóm lấn chiếm, tôi muốn khởi kiện nhưng chưa làm bước nào.",
    "Đất tranh chấp, sổ đỏ còn nguyên, chưa hòa giải.",
])
def test_detector_false_for_pre_mediation(situation: str):
    assert not _is_post_mediation_failed(situation), (
        f"Expected _is_post_mediation_failed=False for: {situation!r}"
    )


# ---------------------------------------------------------------------------
# Test 1 — S-05: Post-mediation situation must NOT re-suggest UBND mediation
# ---------------------------------------------------------------------------


def test_s05_no_ubnd_mediation_action_after_failed_mediation():
    """
    S-05 regression: when user states mediation failed, recommended_actions must not
    include 'nộp đơn yêu cầu hòa giải tại UBND' or any equivalent phrase.
    """
    situation = (
        "Tôi đã hòa giải ở xã nhưng không thành, "
        "hàng xóm vẫn lấn đất và không ký biên bản."
    )
    plan = _planner.plan(situation)
    assert plan.detected_domain == "dat_dai", (
        f"S-05 query should classify as dat_dai, got {plan.detected_domain!r}"
    )
    actions = _generate_recommendations(plan, "Trung bình", [], None, situation)

    assert not _contains_ubnd_mediation(actions), (
        f"B-S05-P0 regression: actions re-suggest UBND mediation after user stated it failed.\n"
        f"Actions: {actions}"
    )


def test_s05_post_mediation_actions_contain_court_guidance():
    """
    After failed mediation, actions must include court filing or biên bản preservation guidance.
    """
    situation = "Hòa giải không thành, hàng xóm không ký biên bản, đất tranh chấp vẫn bị lấn."
    plan = _planner.plan(situation)
    actions = _generate_recommendations(plan, "Trung bình", [], None, situation)

    assert _contains_post_mediation_guidance(actions), (
        f"Actions after failed mediation must mention court filing or biên bản.\n"
        f"Actions: {actions}"
    )


# ---------------------------------------------------------------------------
# Test 2 — Pre-mediation situation MUST suggest UBND mediation
# ---------------------------------------------------------------------------


def test_pre_mediation_includes_ubnd_step():
    """Standard dat_dai template for pre-mediation situation contains UBND mediation step."""
    situation = "Hàng xóm lấn đất 50cm, tôi đã có sổ đỏ nhưng chưa làm việc với UBND xã."
    plan = _planner.plan(situation)
    assert plan.detected_domain == "dat_dai", (
        f"Pre-mediation dat_dai query should classify as dat_dai, got {plan.detected_domain!r}"
    )
    actions = _generate_recommendations(plan, "Trung bình", [], None, situation)
    assert _contains_ubnd_mediation(actions), (
        f"Standard dat_dai actions must include UBND mediation step for pre-mediation case.\n"
        f"Actions: {actions}"
    )


def test_pre_mediation_uses_standard_dat_dai_actions():
    """Pre-mediation dat_dai situation gets standard action set (not post-mediation set)."""
    situation = "Tranh chấp ranh giới đất, sổ đỏ còn nguyên, chưa hòa giải."
    plan = _planner.plan(situation)
    actions = _generate_recommendations(plan, "Trung bình", [], None, situation)
    standard_actions = _DOMAIN_RECOMMENDED_ACTIONS["dat_dai"][:3]
    assert any(a in actions for a in standard_actions), (
        f"Pre-mediation: expected standard dat_dai actions in output, got {actions}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Post-mediation actions must themselves be free of mediation re-suggestion
# ---------------------------------------------------------------------------


def test_dat_dai_post_mediation_action_list_has_no_ubnd_mediation():
    """The _DAT_DAI_POST_MEDIATION_ACTIONS constant itself must not re-suggest UBND mediation."""
    assert not _contains_ubnd_mediation(_DAT_DAI_POST_MEDIATION_ACTIONS), (
        "The post-mediation action list constant must not contain UBND mediation phrases.\n"
        f"Actions: {_DAT_DAI_POST_MEDIATION_ACTIONS}"
    )


# ---------------------------------------------------------------------------
# Test 4 — No cross-domain bleed: other domains not affected
# ---------------------------------------------------------------------------


_DOMAIN_QUERIES = {
    "hop_dong": "Vi phạm hợp đồng mua bán, bên kia chưa thanh toán 3 tháng.",
    "lao_dong": "Tôi bị sa thải không có lý do, không nhận trợ cấp thôi việc.",
    "gia_dinh": "Tôi muốn ly hôn đơn phương, con 2 tuổi.",
    "dan_su": "Bố mất không có di chúc, anh chị em tranh chấp thừa kế nhà đất.",
    "hanh_chinh": "Bị phạt vi phạm hành chính oan, muốn khiếu nại quyết định xử phạt.",
}


@pytest.mark.parametrize("_domain,query", _DOMAIN_QUERIES.items())
def test_other_domains_not_affected_by_post_mediation_fix(_domain: str, query: str):
    """
    The post-mediation override applies ONLY to dat_dai domain.
    Other domains must continue using their standard action templates.
    """
    plan = _planner.plan(query)
    # Also inject a post-mediation phrase into the situation to confirm the branch is NOT taken
    situation_with_mediation_phrase = query + " Hòa giải không thành."
    actions = _generate_recommendations(plan, "Trung bình", [], None, situation_with_mediation_phrase)

    # Post-mediation swap must NOT fire for non-dat_dai domains — standard actions expected
    expected_standard = _DOMAIN_RECOMMENDED_ACTIONS.get(plan.detected_domain, [])[:3]
    if expected_standard:
        assert any(a in actions for a in expected_standard), (
            f"Domain {plan.detected_domain}: expected standard actions, got {actions}"
        )


# ---------------------------------------------------------------------------
# Test 5 — No-diacritics post-mediation phrases
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("no_diac_suffix", [
    "hoa giai khong thanh",
    "da hoa giai tai ubnd nhung khong thanh",
    "khong ky bien ban hoa giai",
])
def test_no_diacritics_post_mediation_detected(no_diac_suffix: str):
    """No-diacritics variants of post-mediation phrases must also trigger the fix."""
    # Combine with a dat_dai situation so the domain classifier returns dat_dai
    situation = f"hang xom lan dat so do toi co, {no_diac_suffix}"
    assert _is_post_mediation_failed(situation), (
        f"No-diacritics phrase must be detected by _is_post_mediation_failed.\n"
        f"Situation: {situation!r}"
    )
    plan = _planner.plan(situation)
    actions = _generate_recommendations(plan, "Trung bình", [], None, situation)
    assert not _contains_ubnd_mediation(actions), (
        f"No-diacritics post-mediation phrase must suppress UBND action.\n"
        f"Situation: {situation!r}\nActions: {actions}"
    )
