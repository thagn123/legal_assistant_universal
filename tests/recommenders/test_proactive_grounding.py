"""
Regression tests for grounded proactive questions (next_best_action._next_questions).

Reported issue: when a user mentioned wanting custody ("dành quyền nuôi con") the
assistant asked "Hai con hiện đang sống với ai…" — presuming the user has TWO children
when no number was ever given. Proactive questions must:
  1. Never presume facts the user did not state.
  2. Skip a question the user already answered in the conversation.
"""
from __future__ import annotations

from src.recommenders.next_best_action import _next_questions


def test_child_custody_question_does_not_presume_two_children():
    qs = _next_questions(["child_custody"], "parent_seeking_custody", "")
    joined = " ".join(qs)
    assert "Hai con" not in joined           # no presumed quantity
    assert "mấy người con" in joined          # asks the count instead


def test_child_living_question_skipped_when_already_answered():
    # User already told us where the children live → don't re-ask.
    folded = "con dang song voi chung toi, chua ly hon"
    qs = _next_questions(["child_custody"], "parent_seeking_custody", folded)
    assert not any("đang sống với ai" in q for q in qs)


def test_land_evidence_question_skipped_when_user_has_so_do():
    folded = "toi co so do va co chung tu thanh toan"
    qs = _next_questions(["land_dispute"], "general_user", folded)
    assert not any("sổ đỏ, giấy viết tay" in q for q in qs)


def test_questions_present_when_nothing_answered_yet():
    qs = _next_questions(["land_dispute"], "general_user", "")
    assert any("sổ đỏ" in q for q in qs)


def test_fallback_questions_when_no_goal():
    qs = _next_questions([], "general_user", "")
    assert len(qs) >= 1
