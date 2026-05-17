from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class DeadlineItem:
    label: str
    days: int
    unit: str = "ngày"
    note: str = ""


@dataclass
class TimelineResult:
    stage: str
    stage_label: str
    stage_confidence: float
    stage_index: int          # 0-based position in journey (for progress %)
    total_stages: int
    progress_percent: int
    typical_deadlines: List[DeadlineItem]
    alerts: List[str]
    next_stage: str
    next_stage_label: str
    advice: str = ""


# Ordered stages (index matters for progress calculation)
_STAGES: List[Tuple[str, str]] = [
    ("preparation", "Chuẩn bị — chưa phát sinh tranh chấp"),
    ("dispute_emerging", "Tranh chấp mới phát sinh"),
    ("negotiation", "Đang thương lượng, hoà giải"),
    ("violation_occurred", "Đã xác định có vi phạm"),
    ("pre_litigation", "Chuẩn bị khởi kiện / khiếu nại"),
    ("in_litigation", "Đang trong quá trình tố tụng"),
    ("awaiting_decision", "Chờ phán quyết / kết quả"),
    ("post_decision", "Sau phán quyết — kháng cáo hoặc thi hành"),
]

_STAGE_INDEX: Dict[str, int] = {s: i for i, (s, _) in enumerate(_STAGES)}

# Keywords that signal each stage (score +1 per keyword found)
_STAGE_KEYWORDS: Dict[str, List[str]] = {
    "preparation": [
        "chuẩn bị", "muốn ký", "sắp ký hợp đồng", "dự định", "tìm hiểu",
        "tra cứu", "chưa có tranh chấp", "tư vấn trước",
    ],
    "dispute_emerging": [
        "tranh chấp", "mâu thuẫn", "bất đồng", "không đồng ý", "phát sinh",
        "bên kia từ chối", "không trả", "vi phạm nhỏ", "khiếu nại đầu tiên",
    ],
    "negotiation": [
        "thương lượng", "hoà giải", "đàm phán", "họp bàn", "thoả thuận",
        "hai bên đang", "còn đang trao đổi", "chưa giải quyết được",
    ],
    "violation_occurred": [
        "đã vi phạm", "vi phạm rõ ràng", "không thực hiện hợp đồng",
        "đã sa thải", "đã thu hồi", "đã chiếm đoạt", "đã gây thiệt hại",
        "đã mất tiền", "bị lừa", "không trả lại", "đòi lại",
    ],
    "pre_litigation": [
        "chuẩn bị khởi kiện", "sắp kiện", "làm hồ sơ kiện",
        "thu thập chứng cứ để kiện", "cần khởi kiện", "muốn khởi kiện",
        "thuê luật sư", "nộp đơn", "gửi đơn",
    ],
    "in_litigation": [
        "đang kiện", "đã nộp đơn khởi kiện", "tòa đang xử", "phiên toà",
        "tố tụng", "điều tra", "xét xử", "khởi tố", "truy tố",
        "toà án đang", "cảnh sát đang điều tra",
    ],
    "awaiting_decision": [
        "chờ phán quyết", "chờ kết quả", "toà đang nghị án", "chờ quyết định",
        "chờ kháng cáo được xem xét", "chờ phúc thẩm",
    ],
    "post_decision": [
        "đã có phán quyết", "phán quyết rồi", "thua kiện", "thắng kiện",
        "kháng cáo", "phúc thẩm", "thi hành án", "thi hành bản án",
        "cưỡng chế", "chống thi hành",
    ],
}

_STAGE_DEADLINES: Dict[str, List[DeadlineItem]] = {
    "preparation": [
        DeadlineItem("Thời gian ký kết hợp đồng nên có công chứng", 0, "không giới hạn", "Nên làm sớm để đảm bảo tính pháp lý"),
    ],
    "dispute_emerging": [
        DeadlineItem("Gửi thông báo vi phạm bằng văn bản", 7, "ngày", "Kể từ khi phát hiện vi phạm"),
        DeadlineItem("Thời hiệu khởi kiện dân sự (tính từ khi biết quyền bị xâm phạm)", 1095, "ngày", "3 năm cho tranh chấp hợp đồng"),
    ],
    "negotiation": [
        DeadlineItem("Thời hạn hoà giải theo quy trình (nếu bắt buộc)", 30, "ngày", "Tuỳ lĩnh vực, có thể tới 60 ngày"),
        DeadlineItem("Lưu giữ biên bản họp, thư từ trao đổi", 0, "liên tục", "Quan trọng để làm chứng cứ"),
    ],
    "violation_occurred": [
        DeadlineItem("Ghi nhận thiệt hại ngay lập tức", 3, "ngày", "Càng sớm càng tốt"),
        DeadlineItem("Gửi thông báo vi phạm chính thức", 15, "ngày", "Bắt đầu tính thời gian phản hồi của bên vi phạm"),
        DeadlineItem("Thời hiệu khởi kiện hợp đồng", 1095, "ngày", "3 năm kể từ ngày vi phạm"),
    ],
    "pre_litigation": [
        DeadlineItem("Nộp đơn khởi kiện tại toà án có thẩm quyền", 30, "ngày", "Đảm bảo còn trong thời hiệu"),
        DeadlineItem("Nộp phí tạm ứng án phí", 15, "ngày", "Sau khi được thụ lý vụ án"),
        DeadlineItem("Chuẩn bị chứng cứ và danh sách nhân chứng", 30, "ngày", "Trước phiên xét xử đầu tiên"),
    ],
    "in_litigation": [
        DeadlineItem("Nộp văn bản, chứng cứ bổ sung theo yêu cầu toà", 15, "ngày", "Theo thông báo của toà"),
        DeadlineItem("Chuẩn bị tham dự phiên toà", 7, "ngày", "Trước ngày xét xử"),
        DeadlineItem("Phản hồi luận cứ của bên đối lập", 10, "ngày", "Theo lịch tố tụng"),
    ],
    "awaiting_decision": [
        DeadlineItem("Theo dõi thông báo từ toà", 3, "ngày", "Kiểm tra thường xuyên"),
        DeadlineItem("Chuẩn bị hồ sơ kháng cáo phòng trường hợp cần", 15, "ngày", "Trước khi có phán quyết"),
    ],
    "post_decision": [
        DeadlineItem("Thời hạn kháng cáo bản án dân sự", 15, "ngày", "Kể từ ngày tuyên án hoặc nhận bản án"),
        DeadlineItem("Thời hạn kháng cáo bản án hình sự (bị cáo)", 15, "ngày", "Kể từ ngày tuyên án"),
        DeadlineItem("Thời hạn yêu cầu thi hành án", 1825, "ngày", "5 năm kể từ ngày bản án có hiệu lực"),
    ],
}

_STAGE_ALERTS: Dict[str, List[str]] = {
    "preparation": [
        "Nên công chứng tất cả giao dịch quan trọng để tránh tranh chấp sau này.",
        "Đọc kỹ hợp đồng trước khi ký, đặc biệt các điều khoản phạt và chấm dứt.",
    ],
    "dispute_emerging": [
        "Ghi lại tất cả trao đổi với bên kia bằng văn bản từ thời điểm này.",
        "Bắt đầu thu thập và lưu giữ chứng cứ sớm — chứng cứ có thể biến mất theo thời gian.",
    ],
    "negotiation": [
        "Mọi thoả thuận trong quá trình thương lượng phải được ký xác nhận.",
        "Không giao thêm tài sản hoặc tiền cho bên kia trong khi đang tranh chấp.",
    ],
    "violation_occurred": [
        "Đây là giai đoạn quan trọng — cần tư vấn luật sư ngay nếu thiệt hại lớn.",
        "Kiểm tra thời hiệu khởi kiện — đừng để quá thời hạn.",
        "Thu thập chứng cứ về thiệt hại thực tế (hoá đơn, biên lai, ước tính).",
    ],
    "pre_litigation": [
        "Xác định đúng toà án có thẩm quyền (theo địa bàn và loại tranh chấp).",
        "Chuẩn bị đủ số lượng bản sao chứng cứ theo yêu cầu của toà.",
        "Tư vấn luật sư trước khi nộp đơn để tránh sai sót về hình thức.",
    ],
    "in_litigation": [
        "Tuân thủ nghiêm ngặt lịch tố tụng của toà — bỏ qua có thể bất lợi.",
        "Không tiếp xúc riêng với thẩm phán hoặc thư ký toà ngoài phòng xét xử.",
    ],
    "awaiting_decision": [
        "Chuẩn bị sẵn hồ sơ kháng cáo trong trường hợp kết quả không như mong đợi.",
        "Thời hạn kháng cáo thường rất ngắn — cần hành động ngay khi có phán quyết.",
    ],
    "post_decision": [
        "Thời hạn kháng cáo thường chỉ 15 ngày — hành động ngay.",
        "Nếu thắng kiện, yêu cầu cơ quan thi hành án hỗ trợ nếu bên thua không tự nguyện thi hành.",
    ],
}


def _detect_stage(situation: str, facts: List[str]) -> Tuple[str, float]:
    combined = (situation + " " + " ".join(facts)).lower()
    scores: Dict[str, int] = {s: 0 for s, _ in _STAGES}

    for stage, keywords in _STAGE_KEYWORDS.items():
        for kw in keywords:
            if kw in combined:
                scores[stage] += 1

    best_stage = max(scores, key=lambda s: scores[s])
    best_score = scores[best_stage]

    if best_score == 0:
        return "dispute_emerging", 0.4

    total_signals = sum(scores.values())
    confidence = round(min(0.95, best_score / max(total_signals, 1) + 0.3), 2)
    return best_stage, confidence


class TimelineTracker:
    def track(
        self,
        situation: str,
        domain: str = "general",
        facts: Optional[List[str]] = None,
    ) -> TimelineResult:
        if facts is None:
            facts = []

        stage, confidence = _detect_stage(situation, facts)
        idx = _STAGE_INDEX.get(stage, 1)
        total = len(_STAGES)
        progress = round((idx / (total - 1)) * 100)

        next_idx = min(idx + 1, total - 1)
        next_stage, next_label = _STAGES[next_idx]

        _, stage_label = _STAGES[idx]

        return TimelineResult(
            stage=stage,
            stage_label=stage_label,
            stage_confidence=confidence,
            stage_index=idx,
            total_stages=total,
            progress_percent=progress,
            typical_deadlines=_STAGE_DEADLINES.get(stage, []),
            alerts=_STAGE_ALERTS.get(stage, []),
            next_stage=next_stage,
            next_stage_label=next_label,
        )
