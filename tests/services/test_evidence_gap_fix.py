# -*- coding: utf-8 -*-
"""Regression tests for evidence gap hallucination fix.

Bug: user writes 'tôi đã có sổ đỏ' in the situation box but the system still
reports 'Sổ đỏ' as missing evidence.

Root causes fixed:
  1. _keywords_match filtered words <= 3 chars, dropping 'sổ'(2) and 'đỏ'(2).
  2. No phrase-level aliases for short Vietnamese legal terms.
  3. No extraction of 'I already have X' claims from the situation narrative.
"""
from __future__ import annotations

from src.services.evidence_gap_detector import (
    EvidenceGapDetector,
    _extract_claimed_evidence,
    _keywords_match,
    _CHECKLISTS,
)

det = EvidenceGapDetector()


# ---------------------------------------------------------------------------
# _extract_claimed_evidence
# ---------------------------------------------------------------------------

def test_extract_so_do_from_situation():
    sit = "Tranh chấp đất đai. Tôi đã có sổ đỏ, biên lai thanh toán tiền mua đất."
    claimed = _extract_claimed_evidence(sit)
    joined = " ".join(claimed).lower()
    assert "sổ đỏ" in joined or "sổ" in joined, f"Expected 'sổ đỏ' in claimed: {claimed}"


def test_extract_hien_co():
    sit = "Hiện có sổ bảo hiểm xã hội và hợp đồng lao động."
    claimed = _extract_claimed_evidence(sit)
    joined = " ".join(claimed).lower()
    assert "sổ bảo hiểm" in joined or "hợp đồng" in joined, claimed


def test_extract_no_false_positive():
    sit = "Tôi cần tư vấn về tranh chấp đất đai."
    claimed = _extract_claimed_evidence(sit)
    assert claimed == []


# ---------------------------------------------------------------------------
# _keywords_match  — phrase-level aliases
# ---------------------------------------------------------------------------

def test_keywords_match_so_do():
    cert = next(i for i in _CHECKLISTS["dat_dai"] if i.category == "certificate")
    assert _keywords_match("sổ đỏ", cert), "Short phrase 'sổ đỏ' must match certificate item"


def test_keywords_match_so_hong():
    cert = next(i for i in _CHECKLISTS["dat_dai"] if i.category == "certificate")
    assert _keywords_match("sổ hồng", cert), "'sổ hồng' must match certificate item"


def test_keywords_match_bien_lai():
    pay = next(i for i in _CHECKLISTS["dat_dai"] if i.category == "payment")
    assert _keywords_match("biên lai", pay), "'biên lai' must match payment item"
    assert _keywords_match("chứng từ thanh toán", pay)


def test_keywords_match_bhxh():
    ins = next(i for i in _CHECKLISTS["lao_dong"] if i.category == "insurance")
    assert _keywords_match("sổ bhxh", ins), "'sổ bhxh' must match insurance item"
    assert _keywords_match("bhxh", ins)
    assert _keywords_match("bảo hiểm xã hội", ins)


def test_keywords_match_di_chuc():
    will = next(i for i in _CHECKLISTS["dan_su"] if i.category == "will")
    assert _keywords_match("di chúc", will), "'di chúc' must match will item"


def test_keywords_match_sa_thai():
    term = next(i for i in _CHECKLISTS["lao_dong"] if i.category == "termination")
    assert _keywords_match("quyết định sa thải", term)
    assert _keywords_match("thông báo sa thải", term)


# ---------------------------------------------------------------------------
# Full detect_gaps — the hallucination scenario
# ---------------------------------------------------------------------------

def test_so_do_in_situation_not_reported_missing():
    """Core regression: 'tôi đã có sổ đỏ' in situation must not appear in missing."""
    result = det.detect_gaps(
        domain="dat_dai",
        facts=[],
        situation="Tranh chấp về tài sản thừa kế đất đai giữa các anh chị em ruột. "
                  "Tôi đã có sổ đỏ, biên lai hoặc chứng từ thanh toán tiền mua đất.",
    )
    missing_cats = {m.category for m in result.missing_evidence}
    assert "certificate" not in missing_cats, (
        f"'Sổ đỏ' was reported missing despite user stating they have it. "
        f"Missing: {missing_cats}"
    )
    assert "payment" not in missing_cats, (
        f"'Biên lai' was reported missing despite user stating they have it. "
        f"Missing: {missing_cats}"
    )


def test_coverage_improves_when_user_states_evidence():
    result_no = det.detect_gaps(domain="dat_dai", facts=[], situation="Tranh chấp đất đai.")
    result_yes = det.detect_gaps(
        domain="dat_dai",
        facts=[],
        situation="Tranh chấp đất đai. Tôi đã có sổ đỏ và biên lai thanh toán.",
    )
    assert result_yes.coverage_score > result_no.coverage_score, (
        "Coverage should increase when user states they have evidence"
    )


def test_facts_box_path_still_works():
    """Explicit facts still matched correctly."""
    result = det.detect_gaps(
        domain="lao_dong",
        facts=["hợp đồng lao động", "bảng lương tháng 3", "sổ bảo hiểm xã hội"],
        situation="Bị sa thải không có lý do.",
    )
    missing_cats = {m.category for m in result.missing_evidence}
    assert "contract" not in missing_cats
    assert "salary" not in missing_cats
    assert "insurance" not in missing_cats


def test_cccd_matches_identity():
    result = det.detect_gaps(
        domain="dan_su",
        facts=["cccd của tôi"],
        situation="Tranh chấp thừa kế.",
    )
    missing_cats = {m.category for m in result.missing_evidence}
    assert "identity" not in missing_cats


def test_empty_situation_shows_all_missing():
    result = det.detect_gaps(domain="dat_dai", facts=[], situation="")
    assert len(result.missing_evidence) == len(_CHECKLISTS["dat_dai"])
    assert result.coverage_score == 0.0
