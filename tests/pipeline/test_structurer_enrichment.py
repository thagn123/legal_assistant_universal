"""
Unit tests for Phase 24 Task 3.1 — document family/type auto-detection in structurer.
Tests _detect_document_family_and_type() with various Vietnamese/English legal texts.
"""

from __future__ import annotations

from src.pipeline.structurer import _detect_document_family_and_type


# ---------------------------------------------------------------------------
# Vietnamese legal document types
# ---------------------------------------------------------------------------

def test_detect_nghi_dinh():
    text = (
        "NGHỊ ĐỊNH\n"
        "Số 15/2024/NĐ-CP ngày 01/01/2024\n"
        "QUY ĐỊNH VỀ QUẢN LÝ ĐẤT ĐAI\n"
        "CHÍNH PHỦ\nCăn cứ Luật Tổ chức Chính phủ"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type == "nghi_dinh"


def test_detect_thong_tu():
    # Use "Bộ trưởng ban hành" — the unique thong_tu structural identifier.
    # Do NOT reference Nghị định or Bộ luật in the body (those rules fire first).
    text = (
        "THÔNG TƯ\nSố 05/2024/TT-BLĐTBXH ngày 10/03/2024\n"
        "Hướng dẫn thi hành một số điều về tiền lương và BHXH\n"
        "Bộ trưởng ban hành\nCăn cứ Luật Lao động và các văn bản liên quan"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type == "thong_tu"


def test_detect_quyet_dinh():
    text = (
        "QUYẾT ĐỊNH\nSố 123/QĐ-UBND ngày 15/02/2024\n"
        "Về việc phê duyệt kế hoạch sử dụng đất năm 2024\n"
        "ỦY BAN NHÂN DÂN TỈNH"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type == "quyet_dinh"


def test_detect_bo_luat():
    text = (
        "BỘ LUẬT LAO ĐỘNG\n"
        "Căn cứ Hiến pháp nước Cộng hòa xã hội chủ nghĩa Việt Nam;\n"
        "Quốc hội ban hành Bộ luật Lao động."
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type == "bo_luat"


def test_detect_luat():
    text = (
        "LUẬT HÔN NHÂN VÀ GIA ĐÌNH\n"
        "Quốc hội ban hành;\n"
        "Luật này quy định về hôn nhân và gia đình.\n"
        "Căn cứ Hiến pháp 2013"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type in ("luat", "bo_luat")  # "căn cứ hiến pháp" triggers bo_luat first


def test_detect_bieu_mau():
    text = (
        "BIỂU MẪU SỐ 01/ĐKLV\n"
        "ĐƠN XIN VIỆC LÀM\n"
        "Kính gửi: Ban Giám đốc Công ty..."
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "bieu_mau"
    assert doc_type == "bieu_mau"


def test_detect_phu_luc():
    text = (
        "PHỤ LỤC I\n"
        "DANH SÁCH CÁC VĂN BẢN PHÁP LUẬT LIÊN QUAN\n"
        "Ban hành kèm theo Thông tư số 05/2024"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "bieu_mau"
    assert doc_type == "bieu_mau"


def test_detect_hop_dong():
    text = (
        "HỢP ĐỒNG LAO ĐỘNG\n"
        "Số: 001/2024/HĐLĐ\n"
        "Bên A: Công ty TNHH ABC\n"
        "Bên B: Nguyễn Văn An"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "hop_dong"
    assert doc_type == "hop_dong"


# ---------------------------------------------------------------------------
# English legal document types
# ---------------------------------------------------------------------------

def test_detect_en_labor_code():
    text = (
        "LABOR CODE OF VIETNAM\n"
        "Pursuant to the Constitution of the Socialist Republic of Vietnam;\n"
        "The National Assembly hereby promulgates the Labor Code."
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type == "bo_luat"


def test_detect_en_contract():
    text = (
        "SERVICE AGREEMENT\nThis Agreement is entered into between:\n"
        "Party A: ABC Company Ltd.\n"
        "Party B: XYZ Services Co.\n"
        "The parties agree as follows:"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "hop_dong"
    assert doc_type == "hop_dong"


def test_detect_en_decree():
    text = (
        "DECREE NO. 15/2024/ND-CP\n"
        "Government Decree on Land Management\n"
        "THE GOVERNMENT\nPursuant to the Law on Organization of the Government"
    )
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type == "nghi_dinh"


# ---------------------------------------------------------------------------
# Fallback / edge cases
# ---------------------------------------------------------------------------

def test_detect_unknown_fallback():
    text = "Đây là một văn bản ngẫu nhiên không có từ khóa đặc biệt."
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "general"
    assert doc_type == "general"


def test_detect_empty_string():
    family, doc_type = _detect_document_family_and_type("")
    assert family == "general"
    assert doc_type == "general"


def test_detect_only_scans_first_8000_chars():
    # Keywords appear only after 8000 chars — should fall back to general
    padding = "a" * 8001
    text = padding + "\nNGHỊ ĐỊNH số 15"
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "general"
    assert doc_type == "general"


def test_detect_keywords_within_8000_chars():
    # Keywords within first 8000 chars — should be detected
    padding = "x " * 100  # ~200 chars
    text = padding + "\nNGHỊ ĐỊNH số 99/2024"
    family, doc_type = _detect_document_family_and_type(text)
    assert family == "luat_phap"
    assert doc_type == "nghi_dinh"
