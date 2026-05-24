from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.services.situation_classifier import SituationClassifier
from src.services.evidence_gap_detector import EvidenceGapDetector


@dataclass
class RiskAnalysisResult:
    domain: str
    risk_score: float          # 0–100
    risk_level: str            # "low" | "medium" | "high" | "critical"
    stage: str
    stage_label: str
    strengths: List[str]
    weaknesses: List[str]
    missing_points: List[str]
    warnings: List[str]
    recommended_actions: List[str]
    evidence_coverage: float   # 0–1
    confidence: float
    summary: str


# ---------------------------------------------------------------------------
# Domain-specific strength indicators (keyword → strength statement)
# ---------------------------------------------------------------------------

_STRENGTH_INDICATORS: Dict[str, List[tuple[str, str]]] = {
    "dat_dai": [
        (["sổ đỏ", "giấy chứng nhận", "gcn"],        "Có giấy chứng nhận quyền sử dụng đất hợp lệ"),
        (["công chứng", "chứng thực"],                "Giao dịch đã được công chứng/chứng thực"),
        (["thanh toán", "biên lai", "chuyển khoản"],  "Có chứng từ thanh toán rõ ràng"),
        (["hợp đồng", "giấy tay"],                    "Có văn bản giao dịch bằng chữ viết"),
        (["ubnd", "địa chính"],                       "Có xác nhận của cơ quan nhà nước"),
    ],
    "hop_dong": [
        (["hợp đồng ký", "hợp đồng có chữ ký"],      "Có hợp đồng ký kết đầy đủ"),
        (["công chứng"],                               "Hợp đồng đã công chứng"),
        (["thanh toán", "biên lai"],                   "Có bằng chứng thanh toán"),
        (["bàn giao", "biên bản"],                     "Có biên bản bàn giao"),
        (["thông báo", "gửi thư"],                     "Đã thực hiện thông báo vi phạm"),
    ],
    "lao_dong": [
        (["hợp đồng lao động"],                        "Có hợp đồng lao động bằng văn bản"),
        (["bảng lương", "phiếu lương"],                "Có tài liệu lương thưởng"),
        (["bảo hiểm xã hội", "bhxh"],                  "Có sổ BHXH làm bằng chứng"),
        (["quyết định", "sa thải"],                    "Có văn bản quyết định chính thức"),
    ],
    "dan_su": [
        (["di chúc", "công chứng"],                    "Có di chúc hợp lệ"),
        (["biên bản", "thỏa thuận"],                   "Có thỏa thuận bằng văn bản"),
        (["nhân chứng"],                               "Có nhân chứng xác nhận"),
    ],
}

_WEAKNESS_INDICATORS: Dict[str, List[tuple[str, str]]] = {
    "dat_dai": [
        (["giấy tay", "không công chứng"],  "Giao dịch chưa qua công chứng, dễ bị tranh cãi"),
        (["mượn", "nhờ đứng tên"],          "Đứng tên hộ tạo rủi ro pháp lý cao"),
        (["không có biên lai"],             "Thiếu chứng từ thanh toán chính thức"),
    ],
    "hop_dong": [
        (["miệng", "nói miệng", "không ký"], "Giao dịch bằng miệng thiếu giá trị pháp lý"),
        (["thiếu điều khoản"],               "Hợp đồng thiếu điều khoản quan trọng"),
        (["quá hạn", "hết hạn"],             "Hợp đồng đã quá thời hạn hiệu lực"),
    ],
    "lao_dong": [
        (["không có hợp đồng", "thỏa thuận miệng"], "Không có hợp đồng lao động bằng văn bản"),
        (["thử việc"],                               "Hợp đồng thử việc có nhiều hạn chế pháp lý"),
    ],
}

# Stage-based action recommendations
_STAGE_ACTIONS: Dict[str, List[str]] = {
    "preparation":      ["Thu thập đầy đủ giấy tờ liên quan", "Tham khảo ý kiến luật sư trước khi ký"],
    "dispute_emerging": ["Ghi nhận sự việc bằng văn bản", "Gửi thông báo chính thức đến bên kia"],
    "negotiation":      ["Chuẩn bị phương án đàm phán", "Tham vấn luật sư về điều khoản thỏa thuận"],
    "violation_occurred": ["Lập biên bản vi phạm", "Thu thập thêm chứng cứ về thiệt hại"],
    "pre_litigation":   ["Chuẩn bị hồ sơ khởi kiện", "Kiểm tra thời hiệu khởi kiện"],
    "in_litigation":    ["Phối hợp với luật sư xây dựng lập luận", "Theo dõi lịch xét xử"],
    "awaiting_decision": ["Chuẩn bị kháng cáo nếu cần", "Tổng kết hồ sơ chứng cứ"],
    "post_decision":    ["Thực hiện bản án/quyết định", "Theo dõi quá trình thi hành án"],
}

_GENERAL_ACTIONS = [
    "Tư vấn luật sư chuyên ngành về tình huống cụ thể",
    "Bổ sung chứng cứ còn thiếu theo danh sách ưu tiên",
    "Lưu trữ tất cả tài liệu liên quan ở nơi an toàn",
]


class RiskAnalysisService:
    """
    Tổng hợp SituationClassifier + EvidenceGapDetector thành đánh giá rủi ro pháp lý toàn diện.
    Deterministic, <30ms, không gọi LLM.
    """

    def __init__(self) -> None:
        self._classifier   = SituationClassifier()
        self._gap_detector = EvidenceGapDetector()

    def analyze(
        self,
        situation: str,
        facts: Optional[List[str]] = None,
        domain_hint: Optional[str] = None,
    ) -> RiskAnalysisResult:
        if facts is None:
            facts = []

        # Stage 1 — classify situation
        profile = self._classifier.classify(situation, facts=facts, domain_hint=domain_hint)

        # Stage 2 — detect evidence gaps
        gap = self._gap_detector.detect_gaps(
            domain=profile.domain,
            facts=facts,
            situation=situation,
        )

        # Stage 3 — compute risk score (0–100)
        stage_risk = {
            "preparation": 10, "dispute_emerging": 35, "negotiation": 45,
            "violation_occurred": 65, "pre_litigation": 75, "in_litigation": 80,
            "awaiting_decision": 70, "post_decision": 30,
        }
        base_score = stage_risk.get(profile.stage, 40)
        evidence_penalty = (1 - gap.coverage_score) * 25      # max +25 if 0% coverage
        priority_gap_penalty = len(gap.priority_items) * 4    # +4 per high-priority gap
        risk_score = min(100, base_score + evidence_penalty + priority_gap_penalty)

        risk_level = (
            "critical" if risk_score >= 80 else
            "high"     if risk_score >= 60 else
            "medium"   if risk_score >= 35 else
            "low"
        )

        # Stage 4 — derive strengths from situation text
        q = (situation + " ".join(facts)).lower()
        strengths: List[str] = []
        for kw_list, label in _STRENGTH_INDICATORS.get(profile.domain, []):
            if any(kw in q for kw in kw_list):
                strengths.append(label)
        if gap.strong_evidence:
            strengths += [f"Chứng cứ mạnh: {e}" for e in gap.strong_evidence[:2]]

        # Stage 5 — derive weaknesses
        weaknesses: List[str] = []
        for kw_list, label in _WEAKNESS_INDICATORS.get(profile.domain, []):
            if any(kw in q for kw in kw_list):
                weaknesses.append(label)
        if gap.weak_evidence:
            weaknesses += [f"Chứng cứ yếu: {e}" for e in gap.weak_evidence[:2]]
        if not weaknesses and risk_score >= 50:
            weaknesses.append("Thiếu nhiều chứng cứ quan trọng theo tiêu chuẩn pháp lý")

        # Stage 6 — missing points (from gap detector)
        missing_points = [m.item for m in gap.missing_evidence[:6]]

        # Stage 7 — warnings
        warnings: List[str] = []
        if risk_level in ("high", "critical"):
            warnings.append("Tình huống có rủi ro pháp lý cao — cần hành động khẩn cấp.")
        if gap.coverage_score < 0.4:
            warnings.append("Chứng cứ hiện có chưa đủ để bảo vệ lập luận trước toà.")
        if profile.stage in ("pre_litigation", "in_litigation"):
            warnings.append("Đang trong hoặc chuẩn bị khởi kiện — cần hỗ trợ luật sư.")
        if len(gap.priority_items) >= 3:
            warnings.append(f"Có {len(gap.priority_items)} mục chứng cứ ưu tiên cao còn thiếu.")

        # Stage 8 — recommended actions
        stage_acts = _STAGE_ACTIONS.get(profile.stage, [])
        gap_acts = [f"Bổ sung chứng cứ: {m.item}" for m in gap.priority_items[:2]]
        actions = (stage_acts + gap_acts + _GENERAL_ACTIONS)[:6]

        # Stage 9 — summary
        risk_labels = {"low": "thấp", "medium": "trung bình", "high": "cao", "critical": "rất cao"}
        summary = (
            f"Mức rủi ro pháp lý: {risk_labels.get(risk_level, risk_level).upper()} "
            f"(điểm {round(risk_score)}/100). "
            f"Độ phủ chứng cứ: {round(gap.coverage_score * 100)}%. "
            f"Giai đoạn: {profile.stage_label}."
        )

        return RiskAnalysisResult(
            domain=profile.domain,
            risk_score=round(risk_score, 1),
            risk_level=risk_level,
            stage=profile.stage,
            stage_label=profile.stage_label,
            strengths=strengths or ["Chưa xác định điểm mạnh từ thông tin cung cấp"],
            weaknesses=weaknesses or ["Chưa xác định điểm yếu từ thông tin cung cấp"],
            missing_points=missing_points,
            warnings=warnings,
            recommended_actions=actions,
            evidence_coverage=round(gap.coverage_score, 2),
            confidence=round(profile.confidence, 2),
            summary=summary,
        )
