"""
Regression tests for multi-turn conversation context (Bug-3) and citation
reconciliation (Bug-1).

Bug-3: A follow-up turn (e.g. "tôi có sổ đỏ và chứng từ thanh toán") must stay in
the SAME legal domain as the established case and be interpreted as a continuation —
not re-classified as a brand-new standalone matter.

Bug-1: The law(s) named in the assessment prose must be extractable so they can be
surfaced in the displayed law list / citations.

All functions under test are deterministic and need no MongoDB / LLM.
"""
from __future__ import annotations

from types import SimpleNamespace

from src.engine.query_planner import QueryPlanner
from src.engine.orchestrator import (
    _build_conversation_history_block,
    _extract_cited_law_refs,
    _law_ref_represented,
    _filter_relevant_laws,
    _is_off_domain,
)


def _law(ref, score, law_type="", cited=False):
    d = {"law_reference": ref, "relevance_score": score, "law_type": law_type}
    if cited:
        d["cited"] = True
    return d

_planner = QueryPlanner()


def _ctx(prefs, history=None):
    """Minimal stand-in for SessionContext (planner only reads law_type_preferences)."""
    return SimpleNamespace(law_type_preferences=prefs, history=history or [])


def _domain(query: str, prefs=None) -> str:
    ctx = _ctx(prefs) if prefs is not None else None
    return _planner.plan(query, session_context=ctx).detected_domain


# ---------------------------------------------------------------------------
# Bug-3 — multi-turn domain continuity
# ---------------------------------------------------------------------------


def test_repro_so_do_followup_stays_dat_dai():
    """The exact reported scenario: land case → 'có sổ đỏ + chứng từ' stays dat_dai."""
    assert _domain(
        "tôi đang có sổ đỏ do chính quyền UBND cấp và có chứng từ thanh toán",
        prefs=["dat_dai"],
    ) == "dat_dai"


def test_short_followup_stray_keyword_inherits_domain():
    """A short follow-up with only a stray off-domain keyword inherits the case domain."""
    # "thanh toán" alone would lean hop_dong, but in an established land case it must not switch.
    assert _domain("tôi có chứng từ thanh toán", prefs=["dat_dai"]) == "dat_dai"


def test_general_followup_inherits_established_domain():
    """A follow-up with no domain signal inherits the established domain."""
    assert _domain("vâng đúng vậy, tôi đồng ý", prefs=["lao_dong"]) == "lao_dong"


def test_strong_switch_primary_keyword_respected():
    """A short follow-up that introduces a primary action keyword switches domain."""
    # Established land case, but user now clearly raises a labor dispute.
    assert _domain("vậy còn việc tôi bị sa thải thì sao", prefs=["dat_dai"]) == "lao_dong"


def test_long_new_question_not_overridden():
    """A long, clearly-new question is never force-inherited."""
    new_q = (
        "Công ty tôi muốn giải thể, cổ đông tranh chấp vốn điều lệ và quyền biểu quyết "
        "trong hội đồng quản trị, thủ tục phá sản doanh nghiệp như thế nào"
    )
    assert _domain(new_q, prefs=["dat_dai"]) == "doanh_nghiep"


def test_no_session_context_behaves_normally():
    """Without a session, detection is unchanged (baseline must not regress)."""
    assert _domain("tôi có chứng từ thanh toán") in ("hop_dong", "general")


# ---------------------------------------------------------------------------
# Bug-3 — conversation history block
# ---------------------------------------------------------------------------


def test_history_block_empty_when_no_history():
    assert _build_conversation_history_block(_ctx(["dat_dai"], history=[])) == ""


def test_history_block_includes_prior_query_and_continuity_note():
    ctx = _ctx(
        ["dat_dai"],
        history=[{"query": "Đất nhà tôi bị thu hồi để làm đường, hòa giải không thành.",
                  "law_type": "dat_dai"}],
    )
    block = _build_conversation_history_block(ctx)
    assert "thu hồi" in block            # prior context carried
    assert "LỊCH SỬ VỤ VIỆC" in block    # delimiter present
    assert "TIẾP NỐI" in block           # continuity instruction present
    assert "đất đai" in block            # domain label rendered


# ---------------------------------------------------------------------------
# Bug-1 — citation extraction & reconciliation helpers
# ---------------------------------------------------------------------------


def test_extract_cited_article_with_named_law_and_year():
    refs = _extract_cited_law_refs("Căn cứ Điều 428 Bộ luật Dân sự 2015, đây là vi phạm.")
    assert "Điều 428 Bộ luật Dân sự 2015" in refs


def test_extract_cited_yearless_named_law():
    refs = _extract_cited_law_refs("Nộp đơn hòa giải theo Điều 202 Luật Đất đai trước khi kiện.")
    assert any("Điều 202 Luật Đất đai" in r for r in refs)


def test_extract_cited_decree_number_form():
    refs = _extract_cited_law_refs("Xem thêm Nghị định 43/2014/NĐ-CP về thi hành Luật Đất đai.")
    assert any("Nghị định 43/2014/NĐ-CP" in r for r in refs)


def test_extract_cited_none_when_no_law():
    assert _extract_cited_law_refs("Không có điều luật nào được nhắc tới ở đây.") == []


def test_law_ref_represented_by_same_article():
    assert _law_ref_represented("Điều 202 Luật Đất đai 2024", ["Điều 202"]) is True


def test_law_ref_not_represented_when_unrelated():
    assert _law_ref_represented("Bộ luật Dân sự 2015", ["Điều 62"]) is False


# ---------------------------------------------------------------------------
# Bug-1 — relevance / off-domain filtering of the displayed law list
# ---------------------------------------------------------------------------


def test_filter_drops_low_relevance_junk_keeps_cited():
    """Divorce: 15%-match traffic decrees are dropped; the cited law is kept."""
    laws = [
        _law("Điều 81 Luật Hôn nhân và Gia đình 2014", 0.9, "gia_dinh", cited=True),
        _law("Điều 1", 0.15, ""), _law("Điều 51", 0.15, ""), _law("Điều 34", 0.15, ""),
    ]
    kept = _filter_relevant_laws(laws, "gia_dinh")
    assert [l["law_reference"] for l in kept] == ["Điều 81 Luật Hôn nhân và Gia đình 2014"]


def test_filter_keeps_related_domain_drops_unrelated():
    """dan_su is related to gia_dinh (kept); hinh_su is unrelated (dropped)."""
    laws = [_law("Điều 59 BLDS", 0.5, "dan_su"), _law("Điều 12 BLHS", 0.5, "hinh_su")]
    kept = _filter_relevant_laws(laws, "gia_dinh")
    assert [l["law_reference"] for l in kept] == ["Điều 59 BLDS"]


def test_filter_never_returns_empty_keeps_best():
    """When every law is weak and none cited, keep the single highest-scoring one."""
    laws = [_law("A", 0.2), _law("B", 0.3), _law("C", 0.1)]
    kept = _filter_relevant_laws(laws, "gia_dinh")
    assert [l["law_reference"] for l in kept] == ["B"]


def test_is_off_domain_rules():
    assert _is_off_domain("hinh_su", "gia_dinh") is True
    assert _is_off_domain("dan_su", "gia_dinh") is False     # related
    assert _is_off_domain("", "gia_dinh") is False           # unknown metadata
    assert _is_off_domain("hinh_su", "general") is False     # no domain to judge against
