from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PersonaRecommendResult:
    role: str
    persona_label: str
    pack_explanation: str
    recommended_topics: List[str]
    recommended_templates: List[str]
    recommended_checklists: List[str]
    quick_links: List[Dict[str, str]]  # {"label": str, "url": str}


_PERSONA_PACKS: Dict[str, Dict] = {
    "individual": {
        "label": "Cá nhân",
        "explanation": (
            "Gói dành cho cá nhân: tập trung vào bảo vệ quyền lợi trong giao dịch "
            "dân sự, đất đai, hôn nhân gia đình và giải quyết tranh chấp nhỏ."
        ),
        "topics": ["dat_dai", "hop_dong", "gia_dinh", "dan_su", "hanh_chinh"],
        "templates": [
            "Hợp đồng mua bán tài sản cá nhân",
            "Hợp đồng cho vay tiền",
            "Biên bản thoả thuận giải quyết tranh chấp",
            "Đơn khiếu nại hành chính",
            "Di chúc hợp pháp",
        ],
        "checklists": [
            "Mua bán đất an toàn (cá nhân)",
            "Thủ tục ly hôn",
            "Khiếu nại quyết định hành chính",
            "Xử lý tranh chấp hợp đồng dân sự",
        ],
        "quick_links": [
            {"label": "Tra cứu luật đất đai", "url": "/analyze?topic=dat_dai"},
            {"label": "Mẫu hợp đồng cá nhân", "url": "/templates"},
            {"label": "Checklist khiếu nại", "url": "/checklists"},
        ],
    },
    "hr": {
        "label": "Nhân sự (HR)",
        "explanation": (
            "Gói dành cho nhân viên nhân sự: tập trung vào luật lao động, "
            "quản lý hợp đồng lao động, kỷ luật nhân viên và bảo hiểm xã hội."
        ),
        "topics": ["lao_dong", "hop_dong", "doanh_nghiep"],
        "templates": [
            "Hợp đồng lao động có thời hạn",
            "Hợp đồng lao động không xác định thời hạn",
            "Phụ lục hợp đồng lao động",
            "Quyết định kỷ luật lao động",
            "Quyết định chấm dứt hợp đồng lao động",
            "Nội quy lao động",
        ],
        "checklists": [
            "Onboarding nhân viên mới",
            "Offboarding nhân viên nghỉ việc",
            "Thủ tục kỷ luật sa thải đúng luật",
            "Đăng ký bảo hiểm xã hội cho nhân viên",
            "Kiểm tra tuân thủ luật lao động hàng năm",
        ],
        "quick_links": [
            {"label": "Bộ luật lao động 2019", "url": "/analyze?topic=lao_dong"},
            {"label": "Mẫu hợp đồng lao động", "url": "/templates"},
            {"label": "Checklist onboarding", "url": "/checklists"},
        ],
    },
    "startup": {
        "label": "Startup",
        "explanation": (
            "Gói dành cho công ty khởi nghiệp: tập trung vào thành lập doanh nghiệp, "
            "huy động vốn, hợp đồng với nhà đầu tư và bảo vệ sở hữu trí tuệ."
        ),
        "topics": ["doanh_nghiep", "hop_dong", "lao_dong"],
        "templates": [
            "Điều lệ công ty TNHH hai thành viên",
            "Hợp đồng góp vốn đầu tư",
            "Term Sheet đầu tư mạo hiểm",
            "Hợp đồng bảo mật thông tin (NDA)",
            "Hợp đồng dịch vụ công nghệ thông tin",
            "Hợp đồng nhượng quyền thương mại",
        ],
        "checklists": [
            "Thành lập công ty TNHH / CP",
            "Huy động vốn đúng pháp luật",
            "Bảo vệ sở hữu trí tuệ (tên thương hiệu, phần mềm)",
            "Tuân thủ pháp luật dữ liệu cá nhân (PDPA)",
        ],
        "quick_links": [
            {"label": "Luật doanh nghiệp 2020", "url": "/analyze?topic=doanh_nghiep"},
            {"label": "Mẫu điều lệ công ty", "url": "/templates"},
            {"label": "Checklist thành lập công ty", "url": "/checklists"},
        ],
    },
    "sme": {
        "label": "Doanh nghiệp vừa và nhỏ (SME)",
        "explanation": (
            "Gói dành cho doanh nghiệp vừa và nhỏ: tập trung vào quản trị nội bộ, "
            "hợp đồng thương mại, giải quyết tranh chấp kinh doanh và tuân thủ thuế."
        ),
        "topics": ["doanh_nghiep", "hop_dong", "lao_dong", "hanh_chinh"],
        "templates": [
            "Hợp đồng mua bán hàng hoá thương mại",
            "Hợp đồng đại lý / phân phối",
            "Hợp đồng dịch vụ B2B",
            "Biên bản họp Hội đồng quản trị",
            "Quy chế tài chính nội bộ",
        ],
        "checklists": [
            "Kiểm tra tuân thủ pháp lý hàng năm (SME)",
            "Xử lý tranh chấp hợp đồng thương mại",
            "Thủ tục giải thể doanh nghiệp",
            "Kiểm tra nghĩa vụ thuế định kỳ",
        ],
        "quick_links": [
            {"label": "Luật thương mại", "url": "/analyze?topic=hop_dong"},
            {"label": "Mẫu hợp đồng B2B", "url": "/templates"},
            {"label": "Checklist tuân thủ SME", "url": "/checklists"},
        ],
    },
    "legal_staff": {
        "label": "Nhân viên pháp chế",
        "explanation": (
            "Gói dành cho nhân viên pháp chế và luật sư nội bộ: tập trung vào "
            "soạn thảo hợp đồng phức tạp, phân tích rủi ro pháp lý toàn diện và "
            "tra cứu pháp luật chuyên sâu."
        ),
        "topics": ["hop_dong", "doanh_nghiep", "lao_dong", "dat_dai", "dan_su"],
        "templates": [
            "Hợp đồng M&A (mua bán và sáp nhập)",
            "Hợp đồng tín dụng / bảo lãnh ngân hàng",
            "Hợp đồng thuê văn phòng thương mại",
            "Bản ghi nhớ hợp tác (MOU)",
            "Hợp đồng tư vấn pháp lý",
        ],
        "checklists": [
            "Due diligence pháp lý doanh nghiệp",
            "Kiểm tra hợp đồng trước khi ký",
            "Đánh giá rủi ro pháp lý toàn diện",
            "Rà soát tuân thủ pháp luật hàng quý",
        ],
        "quick_links": [
            {"label": "Phân tích rủi ro pháp lý", "url": "/risks"},
            {"label": "Tra cứu văn bản pháp luật", "url": "/analyze"},
            {"label": "Bộ mẫu hợp đồng chuyên nghiệp", "url": "/templates"},
        ],
    },
}


class PersonaRecommender:
    SUPPORTED_ROLES = list(_PERSONA_PACKS.keys())

    def recommend_by_role(
        self,
        role: str,
        user_id: Optional[str] = None,
    ) -> PersonaRecommendResult:
        if role not in _PERSONA_PACKS:
            role = "individual"

        pack = _PERSONA_PACKS[role]
        return PersonaRecommendResult(
            role=role,
            persona_label=pack["label"],
            pack_explanation=pack["explanation"],
            recommended_topics=pack["topics"],
            recommended_templates=pack["templates"],
            recommended_checklists=pack["checklists"],
            quick_links=pack["quick_links"],
        )
