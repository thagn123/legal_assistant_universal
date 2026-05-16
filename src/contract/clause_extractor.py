"""
Contract Clause Extractor — identifies and classifies legal clauses in Vietnamese contracts.

Extracts:
  - Clause type (payment, termination, liability, dispute resolution, etc.)
  - Risk level (cao / trung_binh / thap)
  - Content of each clause
  - Vietnamese legal compliance notes
  - Specific improvement recommendations

This module is used by:
  - LegalAgent._deterministic_contract_analyze() (no-LLM fallback)
  - ContractRiskAnalyzer for pre-LLM clause segmentation
  - POST /contracts/analyze endpoint
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

_CLAUSE_TYPE_PATTERNS: dict[str, list[str]] = {
    "payment": [
        r"thanh toán",
        r"tiền thuê",
        r"giá trị hợp đồng",
        r"chi phí",
        r"phương thức thanh toán",
        r"tài khoản ngân hàng",
    ],
    "termination": [
        r"chấm dứt",
        r"đơn phương",
        r"hủy hợp đồng",
        r"giải chấm dứt",
        r"thanh lý hợp đồng",
    ],
    "liability": [
        r"trách nhiệm",
        r"bồi thường",
        r"thiệt hại",
        r"phạt vi phạm",
        r"bồi hoàn",
    ],
    "dispute": [
        r"tranh chấp",
        r"giải quyết",
        r"tòa án",
        r"trọng tài",
        r"hòa giải",
        r"TAND",
        r"VIAC",
    ],
    "confidentiality": [
        r"bảo mật",
        r"bí mật",
        r"không tiết lộ",
        r"thông tin mật",
    ],
    "intellectual_property": [
        r"sở hữu trí tuệ",
        r"bản quyền",
        r"thương hiệu",
        r"nhãn hiệu",
        r"sáng chế",
    ],
    "force_majeure": [
        r"bất khả kháng",
        r"thiên tai",
        r"dịch bệnh",
        r"chiến tranh",
        r"sự kiện bất khả kháng",
    ],
    "delivery": [
        r"giao hàng",
        r"bàn giao",
        r"thời gian giao",
        r"địa điểm giao",
        r"tiến độ",
    ],
    "warranty": [
        r"bảo hành",
        r"bảo đảm chất lượng",
        r"khuyết tật",
        r"lỗi sản phẩm",
    ],
    "governing_law": [
        r"luật áp dụng",
        r"pháp luật điều chỉnh",
        r"pháp luật Việt Nam",
    ],
    "general_provisions": [
        r"điều khoản chung",
        r"ngôn ngữ hợp đồng",
        r"hiệu lực",
        r"số bản",
    ],
}

# High-risk patterns — Vietnamese contract red flags
_HIGH_RISK_PATTERNS: list[Tuple[str, str]] = [
    (r"phạt\s+\d{2,}\s*%", "Mức phạt vi phạm quá cao (>= 10%)"),
    (r"đơn phương\s+chấm dứt\s+(?:mà\s+)?không\s+cần", "Chấm dứt đơn phương không điều kiện"),
    (r"không\s+bồi\s+thường", "Miễn bồi thường — có thể vi phạm BLDS 2015"),
    (r"miễn\s+(?:toàn bộ\s+)?trách\s+nhiệm", "Điều khoản miễn trách nhiệm toàn bộ"),
    (r"vô\s+thời\s+hạn", "Hợp đồng vô thời hạn — rủi ro không chấm dứt được"),
    (r"toàn\s+bộ\s+rủi\s+ro.*(?:bên|party)", "Chuyển toàn bộ rủi ro cho một bên"),
    (r"không\s+hoàn\s+trả", "Không hoàn trả tiền trong mọi trường hợp"),
    (
        r"tự\s+động\s+gia\s+hạn\s+(?:mà\s+)?không\s+(?:cần\s+)?thông\s+báo",
        "Gia hạn tự động không thông báo — bẫy tự động",
    ),
    (r"từ\s+bỏ\s+quyền\s+khởi\s+kiện", "Từ bỏ quyền khởi kiện — vi phạm quyền tố tụng"),
]

# Medium-risk patterns
_MEDIUM_RISK_PATTERNS: list[Tuple[str, str]] = [
    (r"phạt\s+\d+\s*%", "Điều khoản phạt — kiểm tra mức phạt hợp lý"),
    (r"tự\s+động\s+gia\s+hạn", "Gia hạn tự động — cần cơ chế thông báo rõ ràng"),
    (r"đặt\s+cọc\s+không\s+hoàn\s+lại", "Đặt cọc không hoàn lại — xem xét điều kiện"),
    (r"độc\s+quyền", "Điều khoản độc quyền — hạn chế cạnh tranh"),
    (r"theo\s+quyết\s+định\s+của\s+(?:bên|party)", "Quyết định một chiều — thiếu cân bằng"),
]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ExtractedClause:
    """A single extracted and classified clause from a contract."""

    clause_id: str
    clause_type: str  # payment | termination | liability | dispute | etc.
    title: str
    content: str
    risk_level: str  # "cao" | "trung_binh" | "thap"
    risk_reason: Optional[str]
    article_number: Optional[str]  # e.g. "Điều 5"
    page_hint: Optional[int]  # estimated page number
    recommendations: List[str] = field(default_factory=list)


@dataclass
class ClauseExtractionResult:
    """Aggregate result for the full contract."""

    clauses: List[ExtractedClause]
    total_clauses: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    contract_type_detected: Optional[str]
    compliance_score: int  # 0-100 heuristic


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def extract_clauses(
    contract_text: str,
    contract_type: Optional[str] = None,
) -> List[ExtractedClause]:
    """
    Extract and classify clauses from raw contract text.

    Args:
        contract_text: Full or partial contract text content.
        contract_type: Optional hint (e.g. "thue_nha", "lao_dong").

    Returns:
        List of ExtractedClause sorted by clause appearance order.
    """
    blocks = _split_into_articles(contract_text)
    clauses: List[ExtractedClause] = []

    for i, block in enumerate(blocks):
        if len(block.strip()) < 20:
            continue

        clause_type = _classify_clause(block)
        risk_level, risk_reason = _assess_risk(block)
        article_num = _extract_article_number(block)
        title = _extract_title(block) or article_num or f"Điều {i + 1}"

        clauses.append(
            ExtractedClause(
                clause_id=f"clause_{i + 1:03d}",
                clause_type=clause_type,
                title=title,
                content=block[:600].strip(),
                risk_level=risk_level,
                risk_reason=risk_reason,
                article_number=article_num,
                page_hint=None,
                recommendations=_get_recommendations(clause_type, risk_level),
            )
        )

    return clauses


def full_extraction(
    contract_text: str,
    contract_type: Optional[str] = None,
) -> ClauseExtractionResult:
    """
    Full extraction including aggregate statistics and compliance score.
    """
    clauses = extract_clauses(contract_text, contract_type)

    high = sum(1 for c in clauses if c.risk_level == "cao")
    medium = sum(1 for c in clauses if c.risk_level == "trung_binh")
    low = sum(1 for c in clauses if c.risk_level == "thap")

    # Heuristic compliance score: starts at 100, deducted for risks
    score = max(0, 100 - (high * 15) - (medium * 5))

    # Try to detect contract type from content if not provided
    detected_type = contract_type or _detect_contract_type(contract_text)

    return ClauseExtractionResult(
        clauses=clauses,
        total_clauses=len(clauses),
        high_risk_count=high,
        medium_risk_count=medium,
        low_risk_count=low,
        contract_type_detected=detected_type,
        compliance_score=score,
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _split_into_articles(text: str) -> List[str]:
    """Split contract text into article-level blocks."""
    # Vietnamese article markers: Điều 1, ĐIỀU 1, Chương I
    pattern = r"(?=(?:Điều|ĐIỀU|Chương|CHƯƠNG)\s+\d+)"
    blocks = re.split(pattern, text)

    if len(blocks) <= 1:
        # Fallback: split by double newlines
        blocks = [b.strip() for b in re.split(r"\n{2,}", text) if b.strip()]

    return [b for b in blocks if len(b.strip()) >= 30]


def _classify_clause(text: str) -> str:
    """Match text against known clause type patterns; return best match."""
    text_lower = text.lower()
    best_type = "general_provisions"
    best_count = 0

    for clause_type, patterns in _CLAUSE_TYPE_PATTERNS.items():
        count = sum(1 for p in patterns if re.search(p, text_lower))
        if count > best_count:
            best_count = count
            best_type = clause_type

    return best_type


def _assess_risk(text: str) -> Tuple[str, Optional[str]]:
    """Assess risk level of a clause; returns (level, reason)."""
    text_lower = text.lower()

    for pattern, reason in _HIGH_RISK_PATTERNS:
        if re.search(pattern, text_lower):
            return "cao", reason

    for pattern, reason in _MEDIUM_RISK_PATTERNS:
        if re.search(pattern, text_lower):
            return "trung_binh", reason

    return "thap", None


def _extract_article_number(text: str) -> Optional[str]:
    """Extract the first article number from text, e.g. 'Điều 5'."""
    m = re.search(r"(Điều|ĐIỀU)\s+(\d+)", text)
    return f"Điều {m.group(2)}" if m else None


def _extract_title(text: str) -> Optional[str]:
    """Extract a short title from the first non-empty line."""
    for line in text.strip().split("\n"):
        stripped = line.strip()
        if 5 < len(stripped) < 120:
            return stripped
    return None


def _detect_contract_type(text: str) -> Optional[str]:
    """Heuristic detection of contract type from content keywords."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["tiền thuê", "bên thuê", "bên cho thuê", "hợp đồng thuê"]):
        return "thue_nha"
    if any(w in text_lower for w in ["mua bán đất", "chuyển nhượng quyền sử dụng đất", "sổ đỏ"]):
        return "mua_ban_dat"
    if any(w in text_lower for w in ["người lao động", "người sử dụng lao động", "hợp đồng lao động"]):
        return "lao_dong"
    if any(w in text_lower for w in ["dịch vụ", "bên cung cấp", "bên sử dụng dịch vụ"]):
        return "dich_vu"
    if any(w in text_lower for w in ["mua bán hàng hóa", "bên mua", "bên bán", "hàng hóa"]):
        return "mua_ban_hang_hoa"
    return None


def _get_recommendations(clause_type: str, risk_level: str) -> List[str]:
    """Return domain-specific recommendations for a clause type + risk level."""
    recs_by_type: dict[str, List[str]] = {
        "payment": [
            "Xác định rõ đồng tiền thanh toán (VND hay ngoại tệ).",
            "Ghi rõ phương thức thanh toán và số tài khoản ngân hàng.",
            "Thêm điều khoản phạt chậm thanh toán (lãi suất theo BLDS 2015 Điều 357).",
            "Quy định thời hạn thanh toán rõ ràng (ngày cụ thể hoặc sự kiện kích hoạt).",
        ],
        "termination": [
            "Yêu cầu thông báo trước bằng văn bản (tối thiểu 30 ngày theo thông lệ).",
            "Xác định rõ hậu quả pháp lý khi chấm dứt (hoàn trả, bồi thường, nghĩa vụ còn lại).",
            "Phân biệt chấm dứt có lỗi (vi phạm) và không có lỗi (thay đổi nhu cầu).",
            "Quy định cơ chế bàn giao khi chấm dứt.",
        ],
        "liability": [
            "Giới hạn trách nhiệm ở mức hợp lý (thường bằng giá trị hợp đồng).",
            "Liệt kê rõ các trường hợp miễn trách nhiệm.",
            "Tuân thủ Điều 360-364 BLDS 2015 về bồi thường thiệt hại.",
            "Quy định thời hạn thông báo thiệt hại.",
        ],
        "dispute": [
            "Chỉ định rõ phương thức: Tòa án TAND hay Trọng tài thương mại.",
            "Nếu dùng trọng tài: ghi tên trung tâm trọng tài (VIAC, HCMAC, v.v.).",
            "Xác định luật áp dụng (pháp luật Việt Nam — Luật Trọng tài thương mại 2010).",
            "Quy định ngôn ngữ tố tụng.",
        ],
        "confidentiality": [
            "Xác định rõ phạm vi thông tin bảo mật.",
            "Quy định thời hạn bảo mật (thường 2-5 năm sau khi chấm dứt HĐ).",
            "Liệt kê các ngoại lệ (thông tin đã công bố, theo lệnh tòa án).",
            "Quy định biện pháp bảo vệ thông tin mật.",
        ],
        "force_majeure": [
            "Định nghĩa rõ sự kiện bất khả kháng (theo Điều 156 BLDS 2015).",
            "Quy định thủ tục thông báo (trong bao nhiêu ngày).",
            "Xác định nghĩa vụ của các bên khi có sự kiện bất khả kháng.",
            "Quy định thời gian tối đa chịu đựng trước khi chấm dứt.",
        ],
        "warranty": [
            "Xác định rõ phạm vi và thời hạn bảo hành.",
            "Quy định thủ tục khiếu nại bảo hành.",
            "Tuân thủ Luật Bảo vệ quyền lợi người tiêu dùng 2023.",
        ],
    }

    default_recs = ["Xem xét kỹ điều khoản này với luật sư trước khi ký."]
    clause_recs = recs_by_type.get(clause_type, default_recs)

    if risk_level == "cao":
        clause_recs = [
            "⚠️ KHẨN: Điều khoản này có rủi ro cao — cần sửa đổi TRƯỚC KHI KÝ!"
        ] + clause_recs

    return clause_recs
