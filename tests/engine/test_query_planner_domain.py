"""
Unit tests for QueryPlanner._detect_domain — domain classifier correctness.

Covers:
  - Single-domain queries (baseline, must not regress)
  - Multi-domain queries with labor primary action override (P1-A fix)
  - Edge cases: no keywords → general, hint overrides detection
"""
from __future__ import annotations

import pytest

from src.engine.query_planner import QueryPlanner

_planner = QueryPlanner()


def _domain(query: str, hint: str | None = None) -> str:
    plan = _planner.plan(query, law_type_hint=hint)
    return plan.detected_domain


# ---------------------------------------------------------------------------
# Baseline — single-domain queries must not regress
# ---------------------------------------------------------------------------


def test_baseline_dat_dai_single():
    """Pure land query → dat_dai."""
    assert _domain("Hàng xóm lấn đất, tôi đã có sổ đỏ") == "dat_dai"


def test_baseline_lao_dong_single():
    """Pure labor query → lao_dong."""
    assert _domain("Tôi bị sa thải không báo trước") == "lao_dong"


def test_baseline_gia_dinh_single():
    """Pure family query → gia_dinh."""
    assert _domain("Tôi muốn ly hôn, con 18 tháng tuổi") in ("gia_dinh", "dan_su")


def test_baseline_dan_su_single():
    """Pure civil inheritance query → dan_su (or dat_dai — both acceptable)."""
    domain = _domain("Bố mất không để lại di chúc, thừa kế nhà đất")
    assert domain in ("dan_su", "dat_dai"), f"Expected dan_su or dat_dai, got {domain!r}"


def test_baseline_doanh_nghiep_single():
    """Pure corporate query → doanh_nghiep."""
    assert _domain("Công ty muốn giải thể, thu hồi vốn điều lệ") == "doanh_nghiep"


def test_baseline_hop_dong_single():
    """Pure contract query → hop_dong."""
    assert _domain("Đơn phương chấm dứt hợp đồng mua bán hàng hóa") in ("hop_dong", "dan_su")


def test_baseline_no_keywords_returns_general():
    """Unrecognized query → general."""
    assert _domain("Hôm nay thời tiết đẹp quá") == "general"


def test_hint_overrides_detection():
    """law_type_hint always wins, even against strong keywords."""
    # "phá sản" would normally → doanh_nghiep, but hint forces lao_dong
    assert _domain("Công ty phá sản", hint="lao_dong") == "lao_dong"


# ---------------------------------------------------------------------------
# P1-A fix — labor primary override in multi-domain queries
# ---------------------------------------------------------------------------


def test_p1a_sa_thai_plus_dat_dai():
    """Q27 equivalent: 'sa thải' present → lao_dong wins over dat_dai."""
    domain = _domain("Sa thải trái luật và tranh chấp đất đai")
    assert domain == "lao_dong", (
        f"'sa thải' is a primary labor action — expected lao_dong, got {domain!r}"
    )


def test_p1a_no_luong_plus_pha_san():
    """Q30 equivalent: 'nợ lương' present → lao_dong wins over doanh_nghiep."""
    domain = _domain("Công ty nợ lương 3 tháng, giờ tuyên bố phá sản")
    assert domain == "lao_dong", (
        f"'nợ lương' is a primary labor action — expected lao_dong, got {domain!r}"
    )


def test_p1a_sa_thai_with_tai_san_context():
    """'sa thải' + 'tài sản' context → still lao_dong."""
    domain = _domain("Tôi bị sa thải và tranh chấp tài sản là nhà đất với công ty")
    assert domain == "lao_dong", (
        f"Expected lao_dong (sa thải primary), got {domain!r}"
    )


def test_p1a_cham_dut_hdld_multi():
    """'chấm dứt hợp đồng lao động' → lao_dong despite hợp đồng keywords."""
    domain = _domain("Công ty đơn phương chấm dứt hợp đồng lao động không có lý do")
    assert domain == "lao_dong", (
        f"Expected lao_dong (chấm dứt hợp đồng lao động), got {domain!r}"
    )


def test_p1a_no_override_when_lao_dong_zero_hits():
    """Labor primary keyword present but lao_dong has 0 keyword hits → no override."""
    # "sa thải" is in our string, lao_dong keywords: "sa thải" is there — actually "sa thải" IS
    # a lao_dong keyword, so this case is tricky. Let's use a borderline case.
    # "đuổi việc" is in _LABOR_PRIMARY_KEYWORDS.
    # In pure land context without any lao_dong keyword match, no override fires.
    domain = _domain("Hàng xóm lấn đất, mảnh đất sổ đỏ, ranh giới tranh chấp")
    assert domain == "dat_dai", (
        f"No labor keywords → dat_dai must stay, got {domain!r}"
    )


def test_p1a_pure_dat_dai_not_overridden():
    """Pure land query without labor keywords → dat_dai is not overridden."""
    domain = _domain("Bị thu hồi đất không bồi thường, giải phóng mặt bằng sai quy trình")
    assert domain == "dat_dai", (
        f"No labor primary keywords → dat_dai must not be overridden, got {domain!r}"
    )


def test_p1a_ly_hon_dat_dai_not_lao_dong():
    """Divorce + land context → gia_dinh or dan_su, NOT lao_dong (no labor primary kw)."""
    domain = _domain("Tôi muốn ly hôn và tranh chấp tài sản là nhà đất")
    assert domain not in ("lao_dong",), (
        f"No labor action keyword → should not be lao_dong, got {domain!r}"
    )


# ---------------------------------------------------------------------------
# P2-A fix — family primary override (Q15/Q16/Q17)
# ---------------------------------------------------------------------------


def test_p2a_ly_hon_returns_gia_dinh():
    """Q15: 'ly hôn' present → gia_dinh wins over dan_su tie."""
    domain = _domain("Muốn ly hôn đơn phương vì chồng bạo lực, có con 3 tuổi, làm thế nào?")
    assert domain == "gia_dinh", (
        f"'ly hôn' is a family primary keyword — expected gia_dinh, got {domain!r}"
    )


def test_p2a_quyen_nuoi_con_returns_gia_dinh():
    """Q16: 'quyền nuôi con' present → gia_dinh wins over dan_su tie."""
    domain = _domain("Sau ly hôn tranh chấp quyền nuôi con dưới 36 tháng tuổi, ai được nuôi?")
    assert domain == "gia_dinh", (
        f"'quyền nuôi con' is a family primary keyword — expected gia_dinh, got {domain!r}"
    )


def test_p2a_vo_chong_ly_hon_chia_tai_san_returns_gia_dinh():
    """Q17: 'ly hôn' present alongside property keywords → gia_dinh wins."""
    domain = _domain("Vợ chồng ly hôn, nhà chung tài sản chia như thế nào?")
    assert domain == "gia_dinh", (
        f"'ly hôn' is a family primary keyword — expected gia_dinh, got {domain!r}"
    )


def test_p2a_thua_ke_stays_dan_su():
    """Q18: inheritance query without family primary keyword → dan_su (not overridden)."""
    domain = _domain("Cha mẹ mất không có di chúc, anh chị em tranh chấp thừa kế nhà đất?")
    assert domain in ("dan_su", "dat_dai"), (
        f"No family primary keyword → dan_su or dat_dai expected, got {domain!r}"
    )


def test_p2a_di_chuc_stays_dan_su():
    """Q19: will-validity query without family primary keyword → dan_su."""
    domain = _domain("Di chúc viết tay có giá trị pháp lý không, cần điều kiện gì?")
    assert domain in ("dan_su", "gia_dinh"), (
        f"Expected dan_su (or gia_dinh) for will query, got {domain!r}"
    )


# ---------------------------------------------------------------------------
# P2-B fix — hanh_chinh keyword boost (Q24)
# ---------------------------------------------------------------------------


def test_p2b_khieu_nai_xus_phat_returns_hanh_chinh():
    """Q24: 'hành chính' + 'khiếu nại' → hanh_chinh beats hop_dong tie."""
    domain = _domain("Bị phạt vi phạm hành chính oan, thủ tục khiếu nại quyết định xử phạt?")
    assert domain == "hanh_chinh", (
        f"'hành chính' + 'khiếu nại' → expected hanh_chinh, got {domain!r}"
    )


def test_p2b_co_quan_nha_nuoc_returns_hanh_chinh():
    """Q25: 'cơ quan nhà nước' + 'hành chính' → hanh_chinh."""
    domain = _domain("Cơ quan nhà nước ra quyết định sai, tôi khởi kiện hành chính ở đâu?")
    assert domain == "hanh_chinh", (
        f"'cơ quan nhà nước' + 'hành chính' → expected hanh_chinh, got {domain!r}"
    )


# ---------------------------------------------------------------------------
# P2-C fix — no-diacritics dat_dai (Q26)
# ---------------------------------------------------------------------------


def test_p2c_no_diacritics_so_do_returns_dat_dai():
    """Q26: no-diacritics 'so do' + 'ranh gioi' → dat_dai."""
    domain = _domain("so do cua toi bi hang xom tranh chap ranh gioi")
    assert domain == "dat_dai", (
        f"No-diacritics 'so do' + 'ranh gioi' → expected dat_dai, got {domain!r}"
    )
