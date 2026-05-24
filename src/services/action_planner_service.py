from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from src.services.situation_classifier import SituationClassifier
from src.services.evidence_gap_detector import EvidenceGapDetector


@dataclass
class ActionItem:
    step: str
    priority: str     # "immediate" | "important" | "optional"
    reason: str
    deadline: str     # e.g. "Trong 7 ngày", "Trong 1 tháng", ""
    category: str     # "evidence" | "legal" | "communication" | "procedure" | "prevention"


@dataclass
class ActionPlanResult:
    domain: str
    stage: str
    stage_label: str
    immediate_actions: List[ActionItem]
    important_actions: List[ActionItem]
    optional_actions: List[ActionItem]
    total_actions: int
    urgency: str      # "critical" | "high" | "medium" | "low"
    summary: str


# ---------------------------------------------------------------------------
# Stage-based action templates
# Each entry: (step, priority, reason, deadline, category)
# ---------------------------------------------------------------------------

_STAGE_ACTIONS: Dict[str, List[tuple]] = {
    "preparation": [
        ("Tra cứu quy định pháp luật áp dụng cho giao dịch", "important", "Hiểu rõ quyền và nghĩa vụ trước khi ký kết", "Trước khi ký", "legal"),
        ("Yêu cầu công chứng/chứng thực tất cả văn bản quan trọng", "important", "Đảm bảo giá trị pháp lý cao nhất cho tài liệu", "Khi ký kết", "procedure"),
        ("Kiểm tra tình trạng pháp lý của đối tượng giao dịch", "important", "Phát hiện tranh chấp hoặc hạn chế tiềm ẩn", "Trước khi ký", "evidence"),
        ("Tư vấn luật sư trước khi ký hợp đồng lớn", "optional", "Giảm thiểu rủi ro điều khoản bất lợi", "Trước khi ký", "legal"),
    ],
    "dispute_emerging": [
        ("Ghi nhận toàn bộ diễn biến bất đồng bằng văn bản", "immediate", "Tạo cơ sở chứng cứ từ thời điểm sớm nhất", "Trong 3 ngày", "evidence"),
        ("Gửi thông báo chính thức bằng văn bản đến bên kia", "immediate", "Xác lập mốc thời gian pháp lý rõ ràng", "Trong 7 ngày", "communication"),
        ("Thu thập ảnh chụp, video, tin nhắn, email liên quan", "immediate", "Bảo toàn chứng cứ trước khi bị xóa/mất", "Ngay lập tức", "evidence"),
        ("Tham vấn luật sư về phương án đàm phán", "important", "Đánh giá khả năng giải quyết thương lượng", "Trong 14 ngày", "legal"),
        ("Liên hệ nhân chứng, yêu cầu xác nhận bằng văn bản", "important", "Đảm bảo nhân chứng sẵn sàng hợp tác", "Trong 7 ngày", "evidence"),
    ],
    "negotiation": [
        ("Xác định điểm mấu chốt cần nhượng bộ và giới hạn đỏ", "immediate", "Vào đàm phán với lập trường rõ ràng", "Trước khi đàm phán", "legal"),
        ("Chuẩn bị dự thảo thỏa thuận giải quyết tranh chấp", "important", "Sẵn sàng đề xuất giải pháp cụ thể", "Trong 7 ngày", "procedure"),
        ("Ghi lại biên bản mọi buổi họp/đàm phán", "immediate", "Tránh tranh cãi về nội dung thỏa thuận miệng", "Mỗi buổi họp", "communication"),
        ("Cân nhắc phương án hòa giải qua trung gian", "optional", "Tiết kiệm chi phí và thời gian so với khởi kiện", "Trong 30 ngày", "procedure"),
    ],
    "violation_occurred": [
        ("Lập biên bản vi phạm có chữ ký của các bên hoặc nhân chứng", "immediate", "Xác lập bằng chứng về hành vi vi phạm", "Trong 24 giờ", "evidence"),
        ("Tính toán thiệt hại thực tế và thiệt hại tiếp theo", "immediate", "Cơ sở đòi bồi thường chính xác", "Trong 7 ngày", "legal"),
        ("Gửi yêu cầu bồi thường chính thức bằng văn bản có đóng dấu/công chứng", "immediate", "Bắt đầu thủ tục đòi quyền lợi", "Trong 7 ngày", "communication"),
        ("Kiểm tra thời hiệu khởi kiện còn lại", "important", "Tránh mất quyền khởi kiện vì quá thời hạn", "Ngay lập tức", "legal"),
        ("Thu thập chứng từ thiệt hại: hóa đơn, biên bản, ảnh", "important", "Hỗ trợ yêu cầu bồi thường", "Trong 14 ngày", "evidence"),
    ],
    "pre_litigation": [
        ("Nộp đơn khởi kiện tại tòa án có thẩm quyền", "immediate", "Khởi động quy trình tư pháp chính thức", "Trong 7 ngày", "procedure"),
        ("Chuẩn bị và sao chứng toàn bộ hồ sơ chứng cứ", "immediate", "Đảm bảo đủ tài liệu nộp kèm đơn kiện", "Trước khi nộp đơn", "evidence"),
        ("Thuê luật sư đại diện tại tòa", "immediate", "Tăng khả năng thắng kiện đáng kể", "Ngay lập tức", "legal"),
        ("Xác nhận thẩm quyền xét xử và nơi nộp đơn", "important", "Tránh bị đình chỉ vì sai thẩm quyền", "Trước khi nộp đơn", "procedure"),
        ("Chuẩn bị tài chính cho án phí và chi phí luật sư", "important", "Đảm bảo nguồn lực duy trì vụ kiện", "Trong 14 ngày", "prevention"),
    ],
    "in_litigation": [
        ("Phối hợp chặt chẽ với luật sư chuẩn bị lập luận", "immediate", "Xây dựng lý lẽ thuyết phục tòa", "Theo lịch xét xử", "legal"),
        ("Nộp đúng hạn mọi tài liệu, văn bản tòa yêu cầu", "immediate", "Tránh bị xử vắng mặt hoặc bất lợi thủ tục", "Theo từng yêu cầu", "procedure"),
        ("Chuẩn bị nhân chứng, giám định viên (nếu cần)", "important", "Tăng tính thuyết phục của chứng cứ", "Trước phiên tòa", "evidence"),
        ("Theo dõi lịch xét xử, không vắng mặt không lý do", "immediate", "Tránh hậu quả pháp lý bất lợi", "Liên tục", "procedure"),
    ],
    "awaiting_decision": [
        ("Chuẩn bị hồ sơ kháng cáo trong trường hợp thua kiện", "important", "Sẵn sàng cho giai đoạn phúc thẩm", "Trong 15 ngày", "legal"),
        ("Theo dõi và lưu trữ toàn bộ tài liệu vụ kiện", "optional", "Đảm bảo hồ sơ đầy đủ cho mọi tình huống", "Liên tục", "evidence"),
        ("Tư vấn luật sư về khả năng hòa giải cuối phiên", "optional", "Cân nhắc giải pháp thương lượng trước khi có bản án", "Trước khi tòa tuyên", "legal"),
    ],
    "post_decision": [
        ("Theo dõi thi hành án nếu thắng kiện", "important", "Đảm bảo bản án được thực hiện thực tế", "Trong 30 ngày", "procedure"),
        ("Nộp đơn kháng cáo nếu chưa đồng ý với bản án", "immediate", "Thời hạn kháng cáo thường rất ngắn", "Trong 15 ngày", "legal"),
        ("Lưu trữ toàn bộ hồ sơ vụ kiện để tham chiếu sau này", "optional", "Phòng ngừa tranh chấp tương tự", "", "prevention"),
    ],
}

# Domain-specific additional actions
_DOMAIN_EXTRA_ACTIONS: Dict[str, List[tuple]] = {
    "dat_dai": [
        ("Kiểm tra sổ đỏ/sổ hồng tại văn phòng đăng ký đất đai", "important", "Xác minh tình trạng pháp lý thửa đất", "Trong 7 ngày", "evidence"),
        ("Liên hệ UBND xã/phường để xác nhận quyền sử dụng đất", "important", "Lấy xác nhận cơ quan có thẩm quyền", "Trong 14 ngày", "procedure"),
    ],
    "lao_dong": [
        ("Báo cáo tranh chấp lên phòng lao động quận/huyện", "important", "Kích hoạt cơ chế hòa giải lao động bắt buộc", "Trong 7 ngày", "procedure"),
        ("Kiểm tra quyền hưởng trợ cấp thất nghiệp (nếu bị sa thải)", "optional", "Bảo vệ thu nhập trong thời gian chờ giải quyết", "Trong 30 ngày", "legal"),
    ],
    "hop_dong": [
        ("Rà soát điều khoản phạt vi phạm và bồi thường", "important", "Xác định mức bồi thường có thể yêu cầu", "Trong 7 ngày", "legal"),
    ],
    "hinh_su": [
        ("Trình báo cơ quan công an ngay lập tức", "immediate", "Kích hoạt điều tra hình sự", "Trong 24 giờ", "procedure"),
        ("Bảo toàn hiện trường và chứng cứ, không tự ý xử lý", "immediate", "Tránh làm mất chứng cứ quan trọng", "Ngay lập tức", "evidence"),
    ],
}

# Urgency mapping from risk_level
_URGENCY_MAP = {
    "critical": "critical",
    "high":     "high",
    "medium":   "medium",
    "low":      "low",
}


def _make_action(t: tuple) -> ActionItem:
    return ActionItem(step=t[0], priority=t[1], reason=t[2], deadline=t[3], category=t[4])


class ActionPlannerService:
    """
    Sinh kế hoạch hành động pháp lý theo giai đoạn + lĩnh vực + khoảng trống chứng cứ.
    Deterministic, <25ms, không gọi LLM.
    """

    def __init__(self) -> None:
        self._classifier   = SituationClassifier()
        self._gap_detector = EvidenceGapDetector()

    def plan(
        self,
        situation: str,
        facts: Optional[List[str]] = None,
        domain_hint: Optional[str] = None,
    ) -> ActionPlanResult:
        if facts is None:
            facts = []

        profile = self._classifier.classify(situation, facts=facts, domain_hint=domain_hint)
        gap     = self._gap_detector.detect_gaps(domain=profile.domain, facts=facts, situation=situation)

        # Base actions from stage
        raw_actions: List[tuple] = list(_STAGE_ACTIONS.get(profile.stage, []))

        # Domain-specific extras
        raw_actions += _DOMAIN_EXTRA_ACTIONS.get(profile.domain, [])

        # Evidence gap actions (high-priority missing evidence)
        for item in gap.priority_items[:3]:
            raw_actions.append((
                f"Thu thập chứng cứ: {item.item}",
                "immediate" if item.priority == "high" else "important",
                "Chứng cứ quan trọng còn thiếu theo yêu cầu pháp lý",
                "Trong 7 ngày",
                "evidence",
            ))

        # Sort into buckets
        immediate: List[ActionItem] = []
        important: List[ActionItem] = []
        optional:  List[ActionItem] = []
        seen: set[str] = set()

        for t in raw_actions:
            step = t[0]
            if step in seen:
                continue
            seen.add(step)
            item = _make_action(t)
            if item.priority == "immediate":
                immediate.append(item)
            elif item.priority == "important":
                important.append(item)
            else:
                optional.append(item)

        # Derive urgency from risk_level
        urgency = _URGENCY_MAP.get(profile.risk_level, "medium")

        total = len(immediate) + len(important) + len(optional)

        urgency_labels = {
            "critical": "CỰC KỲ KHẨN CẤP",
            "high":     "Khẩn cấp",
            "medium":   "Nên thực hiện sớm",
            "low":      "Có thể lên kế hoạch",
        }

        summary = (
            f"Có {total} hành động cần thực hiện ({len(immediate)} khẩn cấp, "
            f"{len(important)} quan trọng, {len(optional)} tùy chọn). "
            f"Mức độ ưu tiên tổng thể: {urgency_labels.get(urgency, urgency)}. "
            f"Giai đoạn pháp lý: {profile.stage_label}."
        )

        return ActionPlanResult(
            domain=profile.domain,
            stage=profile.stage,
            stage_label=profile.stage_label,
            immediate_actions=immediate,
            important_actions=important,
            optional_actions=optional,
            total_actions=total,
            urgency=urgency,
            summary=summary,
        )
