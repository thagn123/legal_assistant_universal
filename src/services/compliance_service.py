"""
Compliance Radar Service — deterministic, <30ms, no LLM.

Generates a compliance checklist for a given business type / transaction type,
identifies missing compliance items from provided facts, and highlights deadlines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


# ── Data structures ───────────────────────────────────────────────────────────


@dataclass
class ComplianceItem:
    id: str
    category: str
    requirement: str
    law_basis: str
    priority: str          # critical / high / medium / low
    status: str            # required / recommended / optional
    deadline_note: str
    missing: bool = False  # True if not present in user's facts


@dataclass
class ComplianceResult:
    business_type: str
    business_type_label: str
    transaction_type: str
    transaction_type_label: str
    items: List[ComplianceItem]
    missing_count: int
    critical_count: int
    compliance_score: float   # 0–1
    alerts: List[str]
    summary: str


# ── Knowledge base ────────────────────────────────────────────────────────────

_BUSINESS_LABELS: Dict[str, str] = {
    "startup":           "Startup / Khởi nghiệp",
    "sme":               "Doanh nghiệp vừa và nhỏ",
    "hr":                "Bộ phận nhân sự / HR",
    "freelancer":        "Freelancer / Tự do",
    "individual":        "Cá nhân",
    "contract_reviewer": "Người soát hợp đồng",
    "legal_staff":       "Pháp chế nội bộ",
}

_TRANSACTION_LABELS: Dict[str, str] = {
    "thanh_lap":         "Thành lập công ty",
    "tuyen_dung":        "Tuyển dụng / Hợp đồng lao động",
    "hop_dong_thuong_mai":"Hợp đồng thương mại",
    "mua_ban_tai_san":   "Mua bán tài sản",
    "tham_gia_du_an":    "Tham gia dự án / Hợp tác",
    "giai_the":          "Giải thể / Thanh lý",
    "khieu_nai":         "Khiếu nại / Tranh chấp",
    "general":           "Tổng hợp",
}

# Checklist templates per (business_type, transaction_type)
# Each item: (id, category, requirement, law_basis, priority, status, deadline_note, keywords)
# keywords: if any keyword found in user facts → not missing
_TEMPLATES: Dict[str, List[tuple]] = {

    # ── Startup — thành lập ──────────────────────────────────────────────────
    "startup_thanh_lap": [
        ("s01", "Pháp nhân", "Đăng ký kinh doanh (Giấy ĐKDN)", "Luật Doanh nghiệp 2020 Điều 26", "critical", "required", "Trước khi hoạt động", ["đăng ký kinh doanh", "giấy phép", "mã số doanh nghiệp"]),
        ("s02", "Pháp nhân", "Con dấu doanh nghiệp", "Luật Doanh nghiệp 2020 Điều 43", "high", "required", "Sau khi được cấp ĐKDN", ["con dấu"]),
        ("s03", "Thuế", "Đăng ký mã số thuế", "Luật Quản lý thuế 2019 Điều 33", "critical", "required", "Trong 10 ngày sau ĐKDN", ["mã số thuế", "đăng ký thuế"]),
        ("s04", "Tài chính", "Mở tài khoản ngân hàng doanh nghiệp", "Luật Doanh nghiệp 2020", "high", "required", "Trong 30 ngày", ["tài khoản ngân hàng"]),
        ("s05", "Lao động", "Đăng ký nội quy lao động", "Bộ luật Lao động 2019 Điều 118", "medium", "required", "Khi có từ 10 lao động", ["nội quy lao động", "nội quy"]),
        ("s06", "BHXH", "Đăng ký bảo hiểm xã hội cho người lao động", "Luật BHXH 2014 Điều 98", "critical", "required", "Trong 30 ngày kể từ ký HĐLĐ", ["bảo hiểm", "bhxh", "bhyt"]),
        ("s07", "Kế toán", "Bổ nhiệm kế toán trưởng hoặc thuê dịch vụ kế toán", "Luật Kế toán 2015 Điều 53", "high", "required", "Ngay khi hoạt động", ["kế toán", "kế toán trưởng"]),
        ("s08", "Giấy phép", "Xem xét ngành nghề kinh doanh có điều kiện", "Luật Đầu tư 2020 Phụ lục IV", "high", "recommended", "Trước khi hoạt động ngành nghề đó", ["giấy phép con", "ngành nghề điều kiện"]),
        ("s09", "Sở hữu trí tuệ", "Đăng ký nhãn hiệu / bảo hộ thương hiệu", "Luật Sở hữu trí tuệ 2005", "medium", "recommended", "Sớm nhất có thể", ["nhãn hiệu", "thương hiệu", "sở hữu trí tuệ"]),
        ("s10", "Hợp đồng", "Mẫu hợp đồng nội bộ và khách hàng chuẩn", "Bộ luật Dân sự 2015", "medium", "recommended", "Trước khi giao dịch", ["hợp đồng mẫu", "template hợp đồng"]),
    ],

    # ── HR — tuyển dụng ──────────────────────────────────────────────────────
    "hr_tuyen_dung": [
        ("h01", "Hợp đồng", "Hợp đồng lao động bằng văn bản", "Bộ luật Lao động 2019 Điều 14", "critical", "required", "Trước khi bắt đầu làm việc", ["hợp đồng lao động", "hđlđ"]),
        ("h02", "Hợp đồng", "Xác định loại hợp đồng phù hợp (xác định/không xác định thời hạn)", "Bộ luật Lao động 2019 Điều 20", "high", "required", "Khi ký hợp đồng", ["hợp đồng xác định thời hạn", "hợp đồng không xác định"]),
        ("h03", "BHXH", "Đóng bảo hiểm xã hội, y tế, thất nghiệp", "Luật BHXH 2014", "critical", "required", "Trong 30 ngày từ ngày ký HĐLĐ", ["bhxh", "bảo hiểm xã hội", "bhyt", "bhtn"]),
        ("h04", "Lương", "Thỏa thuận lương không dưới mức lương tối thiểu vùng", "Nghị định 38/2022/NĐ-CP", "critical", "required", "Trong hợp đồng", ["lương", "tiền lương", "mức lương"]),
        ("h05", "Phụ lục", "Phụ lục mô tả công việc và KPI (nếu có)", "Bộ luật Lao động 2019 Điều 22", "medium", "recommended", "Cùng lúc ký HĐLĐ", ["phụ lục", "mô tả công việc", "kpi"]),
        ("h06", "NDA", "Thỏa thuận bảo mật thông tin (NDA)", "Bộ luật Lao động 2019 Điều 6", "medium", "recommended", "Trước khi bàn giao tài sản/thông tin", ["bảo mật", "nda", "thỏa thuận bảo mật"]),
        ("h07", "Nội quy", "Nội quy lao động đăng ký với cơ quan có thẩm quyền", "Bộ luật Lao động 2019 Điều 119", "high", "required", "Trước khi áp dụng", ["nội quy lao động"]),
        ("h08", "Thử việc", "Thỏa thuận thử việc đúng thời hạn và mức lương", "Bộ luật Lao động 2019 Điều 24-27", "medium", "required", "Ghi rõ trong hợp đồng", ["thử việc", "probation"]),
    ],

    # ── Individual — mua bán tài sản ─────────────────────────────────────────
    "individual_mua_ban_tai_san": [
        ("i01", "Pháp lý tài sản", "Kiểm tra pháp lý tài sản (sổ đỏ/sổ hồng hợp lệ)", "Luật Đất đai 2013 Điều 100", "critical", "required", "Trước khi đặt cọc", ["sổ đỏ", "sổ hồng", "giấy chứng nhận quyền sử dụng đất"]),
        ("i02", "Hợp đồng", "Hợp đồng mua bán công chứng tại văn phòng công chứng", "Luật Đất đai 2013 Điều 167", "critical", "required", "Khi ký hợp đồng chính thức", ["công chứng", "hợp đồng công chứng"]),
        ("i03", "Thuế", "Kê khai và nộp thuế thu nhập cá nhân từ chuyển nhượng BĐS", "Luật Thuế TNCN 2007 (sửa đổi)", "critical", "required", "Trong 10 ngày sau giao dịch", ["thuế thu nhập", "thuế tncn", "thuế chuyển nhượng"]),
        ("i04", "Thuế", "Lệ phí trước bạ khi sang tên", "Nghị định 10/2022/NĐ-CP", "high", "required", "Khi đăng ký sang tên", ["trước bạ", "lệ phí", "sang tên"]),
        ("i05", "Đặt cọc", "Hợp đồng đặt cọc bằng văn bản với điều khoản phạt rõ ràng", "Bộ luật Dân sự 2015 Điều 328", "high", "required", "Khi đặt cọc", ["đặt cọc", "hợp đồng đặt cọc"]),
        ("i06", "Thanh toán", "Thanh toán qua ngân hàng để có bằng chứng", "Thực tiễn pháp lý", "high", "recommended", "Mỗi lần thanh toán", ["chuyển khoản", "biên lai", "hóa đơn"]),
        ("i07", "Thế chấp", "Kiểm tra tình trạng thế chấp / phong tỏa tài sản", "Luật Đất đai 2013 Điều 168", "critical", "required", "Trước khi giao dịch", ["thế chấp", "phong tỏa", "kê biên"]),
    ],

    # ── SME — hợp đồng thương mại ────────────────────────────────────────────
    "sme_hop_dong_thuong_mai": [
        ("m01", "Hợp đồng", "Hợp đồng thương mại bằng văn bản với đầy đủ điều khoản", "Luật Thương mại 2005 Điều 24", "critical", "required", "Trước khi thực hiện", ["hợp đồng", "hợp đồng thương mại"]),
        ("m02", "Phạt vi phạm", "Điều khoản phạt vi phạm tối đa 8% giá trị phần vi phạm", "Luật Thương mại 2005 Điều 301", "high", "required", "Trong hợp đồng", ["phạt vi phạm", "phạt hợp đồng"]),
        ("m03", "Bồi thường", "Điều khoản bồi thường thiệt hại thực tế", "Luật Thương mại 2005 Điều 303", "high", "required", "Trong hợp đồng", ["bồi thường", "thiệt hại"]),
        ("m04", "Giải quyết tranh chấp", "Điều khoản giải quyết tranh chấp (Tòa án / Trọng tài)", "Luật Trọng tài thương mại 2010", "high", "required", "Trong hợp đồng", ["tranh chấp", "trọng tài", "tòa án"]),
        ("m05", "Bất khả kháng", "Điều khoản bất khả kháng (force majeure)", "Bộ luật Dân sự 2015 Điều 156", "medium", "required", "Trong hợp đồng", ["bất khả kháng", "force majeure"]),
        ("m06", "Hóa đơn", "Xuất hóa đơn đúng quy định VAT", "Nghị định 123/2020/NĐ-CP", "critical", "required", "Khi phát sinh doanh thu", ["hóa đơn", "vat", "thuế gtgt", "hóa đơn điện tử"]),
        ("m07", "Kiểm tra đối tác", "Xác minh tư cách pháp nhân của đối tác", "Luật Doanh nghiệp 2020", "high", "recommended", "Trước khi ký hợp đồng", ["giấy phép kinh doanh đối tác", "mã số doanh nghiệp đối tác"]),
        ("m08", "Bảo mật", "Thỏa thuận bảo mật thông tin thương mại", "Luật Thương mại 2005", "medium", "recommended", "Trong hoặc kèm theo hợp đồng", ["bảo mật", "nda"]),
    ],

    # ── Freelancer — tham gia dự án ──────────────────────────────────────────
    "freelancer_tham_gia_du_an": [
        ("f01", "Hợp đồng", "Hợp đồng cung cấp dịch vụ / hợp đồng khoán việc bằng văn bản", "Bộ luật Dân sự 2015 Điều 513", "critical", "required", "Trước khi bắt đầu", ["hợp đồng dịch vụ", "hợp đồng khoán việc", "hợp đồng"]),
        ("f02", "Thuế TNCN", "Kê khai thuế thu nhập cá nhân từ thù lao hợp đồng", "Luật Thuế TNCN (sửa đổi)", "critical", "required", "Tháng tiếp theo khi nhận thu nhập ≥ 2 triệu/lần", ["thuế thu nhập", "tncn", "thuế"]),
        ("f03", "Sở hữu trí tuệ", "Điều khoản quyền sở hữu sản phẩm / output sau dự án", "Luật Sở hữu trí tuệ 2005 Điều 39", "high", "required", "Trong hợp đồng", ["quyền sở hữu", "sở hữu trí tuệ", "bản quyền"]),
        ("f04", "Thanh toán", "Điều khoản thanh toán rõ ràng (milestone / deadline)", "Bộ luật Dân sự 2015", "high", "required", "Trong hợp đồng", ["thanh toán", "milestone", "phí"]),
        ("f05", "NDA", "Thỏa thuận bảo mật thông tin của khách hàng", "Luật Bảo vệ bí mật kinh doanh", "medium", "recommended", "Trước khi nhận thông tin", ["bảo mật", "nda"]),
        ("f06", "Nghiệm thu", "Biên bản nghiệm thu / bàn giao sản phẩm", "Bộ luật Dân sự 2015 Điều 542", "high", "required", "Khi hoàn thành", ["nghiệm thu", "bàn giao", "biên bản"]),
    ],

    # ── General fallback ─────────────────────────────────────────────────────
    "general_general": [
        ("g01", "Hợp đồng", "Giao dịch quan trọng phải lập bằng văn bản", "Bộ luật Dân sự 2015 Điều 119", "high", "required", "Trước khi thực hiện", ["hợp đồng", "văn bản", "thỏa thuận"]),
        ("g02", "Chứng cứ", "Lưu giữ đầy đủ chứng cứ giao dịch (biên lai, email, tin nhắn)", "Bộ luật Tố tụng dân sự 2015", "high", "required", "Liên tục", ["chứng cứ", "biên lai", "hóa đơn"]),
        ("g03", "Thời hiệu", "Nắm rõ thời hiệu khởi kiện / khiếu nại", "Bộ luật Dân sự 2015 Điều 149-162", "critical", "required", "Ngay khi phát sinh tranh chấp", ["thời hiệu", "hạn khởi kiện"]),
        ("g04", "Công chứng", "Công chứng / chứng thực khi luật yêu cầu", "Luật Công chứng 2014", "high", "recommended", "Theo từng giao dịch cụ thể", ["công chứng", "chứng thực"]),
    ],
}


def _get_template_key(business_type: str, transaction_type: str) -> str:
    key = f"{business_type}_{transaction_type}"
    if key in _TEMPLATES:
        return key
    # Try business_type with general
    fallback = f"{business_type}_general"
    if fallback in _TEMPLATES:
        return fallback
    return "general_general"


class ComplianceService:
    """
    Generates a compliance checklist based on business type and transaction type.
    Identifies missing items by checking user-provided facts.
    """

    def generate(
        self,
        business_type: str,
        transaction_type: str,
        facts: Optional[List[str]] = None,
        situation: str = "",
    ) -> ComplianceResult:
        facts = facts or []
        combined_text = " ".join(facts + [situation]).lower()

        key = _get_template_key(business_type, transaction_type)
        template = _TEMPLATES.get(key, _TEMPLATES["general_general"])

        items: list[ComplianceItem] = []
        for row in template:
            cid, cat, req, law, priority, status, deadline, keywords = row
            # Check if user already has this covered (keywords found in facts/situation)
            covered = any(kw.lower() in combined_text for kw in keywords)
            items.append(
                ComplianceItem(
                    id=cid,
                    category=cat,
                    requirement=req,
                    law_basis=law,
                    priority=priority,
                    status=status,
                    deadline_note=deadline,
                    missing=not covered,
                )
            )

        missing_count = sum(1 for it in items if it.missing)
        critical_count = sum(1 for it in items if it.missing and it.priority == "critical")
        total = len(items)
        compliance_score = round(1.0 - (missing_count / total), 2) if total > 0 else 1.0

        alerts: list[str] = []
        if critical_count > 0:
            alerts.append(f"Có {critical_count} mục tuân thủ bắt buộc quan trọng chưa được đáp ứng.")
        if compliance_score < 0.5:
            alerts.append("Mức độ tuân thủ thấp — cần bổ sung khẩn cấp trước khi giao dịch.")

        bt_label = _BUSINESS_LABELS.get(business_type, business_type)
        tt_label = _TRANSACTION_LABELS.get(transaction_type, transaction_type)

        if compliance_score >= 0.9:
            summary = f"Tuân thủ tốt ({round(compliance_score * 100)}%). Còn {missing_count} mục nhỏ cần bổ sung."
        elif compliance_score >= 0.6:
            summary = f"Tuân thủ trung bình ({round(compliance_score * 100)}%). Cần bổ sung {missing_count} mục, trong đó {critical_count} mục bắt buộc."
        else:
            summary = f"Tuân thủ chưa đạt ({round(compliance_score * 100)}%). Thiếu {missing_count}/{total} mục — rủi ro pháp lý cao."

        return ComplianceResult(
            business_type=business_type,
            business_type_label=bt_label,
            transaction_type=transaction_type,
            transaction_type_label=tt_label,
            items=items,
            missing_count=missing_count,
            critical_count=critical_count,
            compliance_score=compliance_score,
            alerts=alerts,
            summary=summary,
        )
