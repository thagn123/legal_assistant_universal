"""
Regression tests for reflection name extraction.

Reported issue: the system stored a user's age (23) but dropped their name because
`_extract_name` required at least two words — so single-word Vietnamese names like
"Thắng" were never saved. It also let two-word occupations ("giáo viên") through as
names. These tests lock in the corrected behaviour.
"""
from __future__ import annotations

import pytest

from src.memory.reflection_agent import _extract_name


@pytest.mark.parametrize("text,expected", [
    # Single-word name via generic "tôi là" — now captured (the reported case)
    ("tôi là thắng, năm nay 23 tuổi, tốt nghiệp cử nhân ngành robot", "thắng"),
    ("mình là Hùng", "Hùng"),
    # Explicit declarations — single or multi word
    ("tên tôi là Nguyễn Văn A", "Nguyễn Văn A"),
    ("tôi tên là Lan", "Lan"),
    ("gọi tôi là Minh", "Minh"),
])
def test_names_are_extracted(text, expected):
    assert _extract_name(text) == expected


@pytest.mark.parametrize("text", [
    "tôi là giáo viên cấp 2",            # occupation, not a name
    "tôi là nạn nhân của vụ lừa đảo",    # role, not a name
    "tôi là chủ doanh nghiệp nhỏ",       # role, not a name
    "tôi muốn ly hôn và dành quyền nuôi con",  # no self-intro at all
    "tôi là người bị hại trong vụ án",   # role, not a name
])
def test_non_names_are_rejected(text):
    assert _extract_name(text) is None
