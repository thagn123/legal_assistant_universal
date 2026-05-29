"""
Regression tests R01-R11 — Evidence status correctness and cross-module contradiction guards.
Run: pytest tests/regression/test_evidence_regression.py -v
"""
from __future__ import annotations

import pytest

from src.evidence.evidence_extractor import aggregate_evidence_facts, extract_evidence_facts
from src.evidence.evidence_gap_engine import analyze_evidence_gap
from src.evidence.evidence_schemas import CONTRADICTED, MISSING, PRESENT, UNCERTAIN


def _status(text: str, evidence_id: str, domain: str) -> str:
    facts = aggregate_evidence_facts(extract_evidence_facts(text, domain=domain))
    if evidence_id not in facts:
        return MISSING
    return facts[evidence_id].status


# ── R01: explicit "đã có sổ đỏ" → PRESENT ─────────────────────────────────────
def test_r01_so_do_present():
    assert _status("Tôi đã có sổ đỏ", "land_certificate", "dat_dai") == PRESENT


# ── R02: possessive phrase → PRESENT ──────────────────────────────────────────
def test_r02_possessive_so_do_present():
    assert _status("Sổ đỏ của tôi bị tranh chấp", "land_certificate", "dat_dai") == PRESENT


# ── R03: GCN QSDĐ alias → PRESENT ─────────────────────────────────────────────
def test_r03_gcn_qsdd_present():
    assert _status("Tôi có GCN QSDĐ", "land_certificate", "dat_dai") == PRESENT


# ── R04: GCN QSDD (no diacritics) → PRESENT ───────────────────────────────────
def test_r04_gcn_qsdd_no_diacritics():
    assert _status("Tôi có GCN QSDD", "land_certificate", "dat_dai") == PRESENT


# ── R05: "chưa có" negation → MISSING ─────────────────────────────────────────
def test_r05_chua_co_missing():
    assert _status("Tôi chưa có sổ đỏ", "land_certificate", "dat_dai") == MISSING


# ── R06: photo-only copy → CONTRADICTED or UNCERTAIN ──────────────────────────
def test_r06_photo_only():
    result = _status(
        "Tôi chỉ có bản photo sổ đỏ, bản gốc bị mất",
        "land_certificate",
        "dat_dai",
    )
    assert result in (CONTRADICTED, UNCERTAIN), f"Expected CONTRADICTED/UNCERTAIN, got {result}"


# ── R07: bên cho thuê — recs should not advise as if user is lessee ───────────
def test_r07_lessor_role_does_not_recommend_as_lessee():
    result = analyze_evidence_gap("Tôi là bên cho thuê, hợp đồng đã ký 2 năm", "hop_dong")
    recs_text = " ".join(result.recommendations).lower()
    # Must not exclusively recommend lessee-only actions
    assert "bên thuê" not in recs_text or "cho thuê" in recs_text


# ── R08: bên thuê role — correct structure, no lessor-only actions ────────────
def test_r08_lessee_role_no_crash():
    result = analyze_evidence_gap(
        "Tôi là bên thuê, chủ nhà đơn phương chấm dứt hợp đồng", "hop_dong"
    )
    assert result is not None
    assert isinstance(result.recommendations, list), "recommendations must be a list"
    recs_text = " ".join(result.recommendations).lower()
    # Lessor-only actions must not be recommended to the lessee
    LESSOR_ONLY = ["thu hồi nhà", "đòi lại nhà", "yêu cầu người thuê rời đi"]
    for bad in LESSOR_ONLY:
        assert bad not in recs_text, (
            f"R08 FAIL: lessee query got lessor action '{bad}': {recs_text[:300]}"
        )


# ── R09: đã hòa giải → analyze_evidence_gap không tự gợi ý lại hòa giải cấp xã
def test_r09_reconciled_no_initial_mediation():
    # analyze_evidence_gap() only assesses document completeness — it does not
    # generate procedural guidance (court steps come from the full orchestrator).
    # The invariant: it must not actively re-recommend "hòa giải tại ubnd xã"
    # as if the user has never tried mediation.
    result = analyze_evidence_gap("Tôi đã hòa giải ở xã nhưng không thành", "dat_dai")
    assert result is not None
    assert isinstance(result.recommendations, list)
    recs_lower = " ".join(result.recommendations).lower()
    assert "hòa giải tại ubnd xã" not in recs_lower or "không thành" in recs_lower, (
        "R09 FAIL: recommended re-starting mediation after user said it failed"
    )


# ── R10: no supplement recommendation when land_certificate is PRESENT ────────
@pytest.mark.parametrize("situation", [
    "Tôi đã có sổ đỏ, hàng xóm lấn 50cm",
    "Sổ đỏ của tôi bị hàng xóm tranh chấp",
    "GCN QSDĐ đứng tên tôi nhưng bị lấn chiếm",
])
def test_r10_no_supplement_for_present_land_cert(situation: str):
    BAD_PATTERNS = [
        "xin cấp sổ đỏ lần đầu",
        "thu thập sổ đỏ",
        "bổ sung sổ đỏ",
        "cần có sổ đỏ",
        "cần thu thập sổ đỏ",
        "chưa có sổ đỏ",
    ]
    result = analyze_evidence_gap(situation, "dat_dai")
    for rec in result.recommendations:
        rec_lower = rec.lower()
        for pat in BAD_PATTERNS:
            assert pat not in rec_lower, (
                f"Bad recommendation for '{situation}':\n  rec: '{rec}'\n  pattern: '{pat}'"
            )


# ── R11: OutputValidator.validate — removes contradictory actions ─────────────
def test_r11_output_validator_removes_bad_actions():
    from src.engine.output_validator import OutputValidator
    from src.evidence.evidence_schemas import EvidenceAssessment

    validator = OutputValidator()

    # Build a minimal evidence_context mock with PRESENT land_certificate
    class _MockContext:
        present_evidence = [EvidenceAssessment(
            evidence_id="land_certificate",
            title="Giấy chứng nhận quyền sử dụng đất (sổ đỏ/sổ hồng)",
            category="document",
            domain="dat_dai",
            priority="high",
            status=PRESENT,
            matched_text="sổ đỏ của tôi",
            matched_alias="sổ đỏ",
            confidence=0.9,
        )]

    actions = [
        "Thu thập sổ đỏ hoặc GCN QSDĐ",          # should be removed/rewritten
        "Liên hệ UBND xã để xác nhận ranh giới",  # should be kept
    ]
    result = validator.validate(actions, _MockContext())
    result_lower = " ".join(result).lower()
    assert "thu thập sổ đỏ" not in result_lower, f"Bad action survived: {result}"
    assert any("ubnd" in r.lower() or "ranh giới" in r.lower() for r in result), (
        "Good action was incorrectly removed"
    )
