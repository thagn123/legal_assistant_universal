from __future__ import annotations

from src.evidence.evidence_extractor import aggregate_evidence_facts, extract_evidence_facts
from src.evidence.evidence_schemas import CONTRADICTED, MISSING, PRESENT


def _status(text: str, evidence_id: str, domain: str = "dat_dai") -> str:
    facts = aggregate_evidence_facts(extract_evidence_facts(text, domain=domain))
    return facts[evidence_id].status


def test_present_so_do_and_payment():
    text = "tôi đã có sổ đỏ và biên lai chuyển khoản"
    facts = aggregate_evidence_facts(extract_evidence_facts(text, domain="dat_dai"))

    assert facts["land_certificate"].status == PRESENT
    assert facts["payment_proof"].status == PRESENT


def test_missing_so_do_present_transfer_document():
    text = "tôi chưa có sổ đỏ nhưng có giấy mua bán viết tay"
    facts = aggregate_evidence_facts(extract_evidence_facts(text, domain="dat_dai"))

    assert facts["land_certificate"].status == MISSING
    assert facts["transfer_document"].status == PRESENT


def test_negation_not_matched_as_present():
    assert _status("không có giấy chứng nhận quyền sử dụng đất", "land_certificate") == MISSING


def test_alias_gcn_qsdd_matches_certificate():
    assert _status("tôi có GCN QSDĐ", "land_certificate") == PRESENT


def test_contradiction_when_original_is_lost():
    assert _status("tôi có sổ đỏ nhưng bản gốc bị mất", "land_certificate") == CONTRADICTED


# ── Possessive phrase golden cases (P0-1) ────────────────────────────────────

def test_possessive_so_do_cua_toi():
    """'sổ đỏ của tôi bị tranh chấp' → PRESENT (possessive cue after alias)."""
    assert _status("sổ đỏ của tôi bị tranh chấp", "land_certificate") == PRESENT


def test_possessive_so_do_gia_dinh():
    """'sổ đỏ của gia đình tôi' → PRESENT."""
    assert _status("sổ đỏ của gia đình tôi đang bị hàng xóm tranh chấp", "land_certificate") == PRESENT


def test_alias_bia_hong():
    """'bìa hồng' is a valid alias for land_certificate."""
    assert _status("bìa hồng đứng tên tôi", "land_certificate") == PRESENT


def test_alias_bia_hong_no_positive():
    """'bìa hồng' alone (no cue) → UNCERTAIN, not MISSING."""
    from src.evidence.evidence_schemas import UNCERTAIN
    result = _status("bìa hồng đang bị tranh chấp", "land_certificate")
    assert result in (PRESENT, UNCERTAIN)  # possessive "bị tranh chấp" not a possessive cue but not MISSING


def test_explicit_missing_so_do():
    """'chưa có sổ đỏ' → MISSING (no regression)."""
    assert _status("tôi chưa có sổ đỏ", "land_certificate") == MISSING


def test_no_diacritics_toi_co_so_do():
    """Folded: 'toi co so do' → PRESENT."""
    assert _status("toi co so do", "land_certificate") == PRESENT


def test_labor_possessive():
    """'hợp đồng lao động của tôi bị vi phạm' → labor_contract=PRESENT."""
    from src.evidence.evidence_extractor import aggregate_evidence_facts, extract_evidence_facts
    facts = aggregate_evidence_facts(
        extract_evidence_facts("hợp đồng lao động của tôi bị vi phạm", domain="lao_dong")
    )
    assert facts["labor_contract"].status == PRESENT
