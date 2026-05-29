from __future__ import annotations

from src.evidence.evidence_gap_engine import analyze_evidence_gap
from src.evidence.evidence_schemas import CONTRADICTED, MISSING, PRESENT


def _by_id(items):
    return {item.evidence_id: item for item in items}


def test_present_items_do_not_appear_in_missing():
    result = analyze_evidence_gap("tôi đã có sổ đỏ và biên lai chuyển khoản", domain="land")

    present = _by_id(result.present_evidence)
    missing = _by_id(result.missing_evidence)

    assert present["land_certificate"].status == PRESENT
    assert present["payment_proof"].status == PRESENT
    assert "land_certificate" not in missing
    assert "payment_proof" not in missing


def test_missing_and_present_are_separated():
    result = analyze_evidence_gap("tôi chưa có sổ đỏ nhưng có giấy mua bán viết tay", domain="dat_dai")

    assert _by_id(result.missing_evidence)["land_certificate"].status == MISSING
    assert _by_id(result.present_evidence)["transfer_document"].status == PRESENT


def test_bug_image_case_expected_groups():
    text = (
        "Tranh chấp về tài sản thừa kế đất đai giữa các anh chị em ruột. "
        "tôi đã có sổ đỏ, Biên lai hoặc chứng từ thanh toán tiền mua đất"
    )
    result = analyze_evidence_gap(text, domain="land")

    present_titles = {item.title for item in result.present_evidence}
    missing_titles = {item.title for item in result.missing_evidence}
    uncertain_titles = {item.title for item in result.uncertain_evidence}

    assert "Sổ đỏ / Giấy chứng nhận quyền sử dụng đất" in present_titles
    assert "Biên lai hoặc chứng từ thanh toán tiền mua đất" in present_titles
    assert "Sổ đỏ / Giấy chứng nhận quyền sử dụng đất" not in missing_titles
    assert "Biên lai hoặc chứng từ thanh toán tiền mua đất" not in missing_titles
    assert "Giấy tờ chuyển nhượng quyền sử dụng đất" in missing_titles
    assert "Xác nhận của UBND xã/phường về quyền sử dụng đất" in missing_titles
    assert "Bản đồ địa chính / sơ đồ thửa đất" in uncertain_titles
    assert "Nhân chứng tham gia giao dịch" in uncertain_titles
    assert result.coverage_score > 0.33


def test_contradicted_evidence_not_classified_as_simple_missing():
    result = analyze_evidence_gap("tôi có sổ đỏ nhưng bản gốc bị mất", domain="dat_dai")

    assert _by_id(result.contradictions)["land_certificate"].status == CONTRADICTED
    assert "land_certificate" not in _by_id(result.missing_evidence)
