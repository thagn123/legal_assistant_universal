from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.services.evidence_gap_detector import EvidenceGapDetector, EvidenceGapResult
from src.services.timeline_tracker import TimelineTracker, TimelineResult

logger = logging.getLogger(__name__)


@dataclass
class JourneyMilestone:
    key: str
    title: str
    status: str          # "done" | "in_progress" | "pending" | "warning"
    summary: str
    detail: str = ""
    action_url: str = ""


@dataclass
class JourneyResult:
    situation: str
    domain: str
    current_stage: str
    stage_label: str
    progress_percent: int
    stage_confidence: float
    milestones: List[JourneyMilestone]
    evidence_coverage: float
    evidence_missing_count: int
    evidence_priority_count: int
    risk_level: str            # "low" | "medium" | "high"
    risk_summary: str
    next_steps: List[str]
    alerts: List[str]
    law_references: List[Dict[str, Any]]  # {"title": str, "score": float}


def _classify_domain(situation: str) -> str:
    domain_keywords = {
        "dat_dai": ["đất", "sổ đỏ", "quyền sử dụng đất", "thu hồi đất", "bồi thường đất", "thửa đất"],
        "hop_dong": ["hợp đồng", "vi phạm hợp đồng", "đơn phương chấm dứt", "phạt hợp đồng"],
        "lao_dong": ["lao động", "sa thải", "lương", "bảo hiểm xã hội", "tai nạn lao động", "nhân viên"],
        "doanh_nghiep": ["công ty", "cổ đông", "phá sản", "vốn điều lệ", "hội đồng quản trị"],
        "dan_su": ["thừa kế", "di chúc", "tài sản chung", "bồi thường thiệt hại dân sự"],
        "hinh_su": ["hình sự", "tội phạm", "truy tố", "phạt tù", "công an", "khởi tố"],
        "hanh_chinh": ["khiếu nại", "quyết định hành chính", "ubnd", "cơ quan nhà nước"],
        "gia_dinh": ["hôn nhân", "ly hôn", "nuôi con", "cấp dưỡng", "bạo lực gia đình"],
    }
    s = situation.lower()
    scores = {d: sum(1 for kw in kws if kw in s) for d, kws in domain_keywords.items()}
    best = max(scores, key=lambda d: scores[d])
    return best if scores[best] > 0 else "general"


def _derive_risk(evidence_result: EvidenceGapResult, timeline_result: TimelineResult) -> tuple[str, str]:
    priority_missing = len(evidence_result.priority_items)
    coverage = evidence_result.coverage_score
    stage_idx = timeline_result.stage_index

    score = 0
    # Higher stage index (closer to litigation) = more risk
    score += stage_idx * 10
    # Missing high-priority evidence = risk
    score += priority_missing * 20
    # Low coverage = risk
    score += max(0, int((0.6 - coverage) * 50))

    if score >= 60:
        level = "high"
        summary = f"Rủi ro CAO: Thiếu {priority_missing} chứng cứ quan trọng, đang ở giai đoạn {timeline_result.stage_label.lower()}."
    elif score >= 30:
        level = "medium"
        summary = f"Rủi ro TRUNG BÌNH: Còn thiếu một số chứng cứ, cần bổ sung trước khi tiến hành bước tiếp theo."
    else:
        level = "low"
        summary = "Rủi ro THẤP: Bạn đã có khá đủ chứng cứ cho giai đoạn hiện tại."

    return level, summary


def _build_milestones(
    evidence: EvidenceGapResult,
    timeline: TimelineResult,
) -> List[JourneyMilestone]:
    milestones = []

    # Milestone 1: Evidence collection
    ev_status = "done" if evidence.coverage_score >= 0.7 else ("in_progress" if evidence.coverage_score >= 0.4 else "warning")
    milestones.append(JourneyMilestone(
        key="evidence",
        title="Thu thập chứng cứ",
        status=ev_status,
        summary=f"Đã có {round(evidence.coverage_score * 100)}% chứng cứ, còn thiếu {len(evidence.missing_evidence)} mục",
        detail=(
            "Chứng cứ ưu tiên cần bổ sung: " +
            "; ".join(m.item for m in evidence.priority_items[:3])
        ) if evidence.priority_items else "Chứng cứ cơ bản đã đầy đủ.",
        action_url="/analyze",
    ))

    # Milestone 2: Stage identification
    milestones.append(JourneyMilestone(
        key="stage",
        title="Xác định giai đoạn vụ việc",
        status="done",
        summary=timeline.stage_label,
        detail=f"Độ tin cậy: {round(timeline.stage_confidence * 100)}%. Giai đoạn tiếp theo: {timeline.next_stage_label}",
    ))

    # Milestone 3: Legal research
    milestones.append(JourneyMilestone(
        key="law_lookup",
        title="Tra cứu luật áp dụng",
        status="in_progress",
        summary="Xem các quy định pháp lý liên quan đến tình huống của bạn",
        action_url="/analyze",
    ))

    # Milestone 4: Risk assessment
    risk_level, risk_summary = _derive_risk(evidence, timeline)
    risk_status = "warning" if risk_level == "high" else ("in_progress" if risk_level == "medium" else "done")
    milestones.append(JourneyMilestone(
        key="risk",
        title="Đánh giá rủi ro pháp lý",
        status=risk_status,
        summary=risk_summary,
        action_url="/risks",
    ))

    # Milestone 5: Next action
    next_action_title = {
        "preparation": "Chuẩn bị tài liệu ký kết",
        "dispute_emerging": "Gửi thông báo vi phạm",
        "negotiation": "Tiến hành hoà giải",
        "violation_occurred": "Thu thập chứng cứ thiệt hại",
        "pre_litigation": "Nộp đơn khởi kiện",
        "in_litigation": "Chuẩn bị hồ sơ tố tụng",
        "awaiting_decision": "Theo dõi tiến trình xét xử",
        "post_decision": "Thi hành án hoặc kháng cáo",
    }.get(timeline.stage, "Bước tiếp theo")

    milestones.append(JourneyMilestone(
        key="next_action",
        title=next_action_title,
        status="pending",
        summary="Hành động được đề xuất cho giai đoạn hiện tại",
        detail="; ".join(timeline.alerts[:2]) if timeline.alerts else "",
    ))

    return milestones


def _build_next_steps(timeline: TimelineResult, evidence: EvidenceGapResult) -> List[str]:
    steps = []
    if evidence.priority_items:
        items = [m.item for m in evidence.priority_items[:2]]
        steps.append(f"Thu thập chứng cứ còn thiếu: {', '.join(items)}")
    steps.extend(timeline.alerts[:2])
    if timeline.typical_deadlines:
        d = timeline.typical_deadlines[0]
        steps.append(f"Lưu ý thời hạn: {d.label} — {d.days} {d.unit} ({d.note})")
    return steps[:5]


class LegalJourneyService:
    def __init__(self) -> None:
        self._gap_detector = EvidenceGapDetector()
        self._timeline_tracker = TimelineTracker()

    def build_journey(
        self,
        situation: str,
        facts: Optional[List[str]] = None,
        domain: Optional[str] = None,
    ) -> JourneyResult:
        if facts is None:
            facts = []

        resolved_domain = domain or _classify_domain(situation)

        evidence = self._gap_detector.detect_gaps(
            domain=resolved_domain,
            facts=facts,
            situation=situation,
        )
        timeline = self._timeline_tracker.track(
            situation=situation,
            domain=resolved_domain,
            facts=facts,
        )

        risk_level, risk_summary = _derive_risk(evidence, timeline)
        milestones = _build_milestones(evidence, timeline)
        next_steps = _build_next_steps(timeline, evidence)

        # Provide lightweight law reference hints (no vector search needed here)
        law_refs: List[Dict[str, Any]] = _DOMAIN_LAW_HINTS.get(resolved_domain, [])

        return JourneyResult(
            situation=situation,
            domain=resolved_domain,
            current_stage=timeline.stage,
            stage_label=timeline.stage_label,
            progress_percent=timeline.progress_percent,
            stage_confidence=timeline.stage_confidence,
            milestones=milestones,
            evidence_coverage=evidence.coverage_score,
            evidence_missing_count=len(evidence.missing_evidence),
            evidence_priority_count=len(evidence.priority_items),
            risk_level=risk_level,
            risk_summary=risk_summary,
            next_steps=next_steps,
            alerts=timeline.alerts,
            law_references=law_refs,
        )


_DOMAIN_LAW_HINTS: Dict[str, List[Dict[str, Any]]] = {
    "dat_dai": [
        {"title": "Luật Đất đai 2024 (Luật số 31/2024/QH15)", "score": 0.95},
        {"title": "Nghị định 43/2014/NĐ-CP — Thi hành Luật Đất đai", "score": 0.85},
        {"title": "Thông tư 24/2014/TT-BTNMT — Hồ sơ địa chính", "score": 0.75},
    ],
    "hop_dong": [
        {"title": "Bộ luật Dân sự 2015 — Phần III: Nghĩa vụ và Hợp đồng", "score": 0.95},
        {"title": "Luật Thương mại 2005 — Hợp đồng thương mại", "score": 0.85},
    ],
    "lao_dong": [
        {"title": "Bộ luật Lao động 2019 (Luật số 45/2019/QH14)", "score": 0.95},
        {"title": "Nghị định 145/2020/NĐ-CP — Thi hành Bộ luật Lao động", "score": 0.85},
        {"title": "Luật Bảo hiểm Xã hội 2014", "score": 0.75},
    ],
    "doanh_nghiep": [
        {"title": "Luật Doanh nghiệp 2020 (Luật số 59/2020/QH14)", "score": 0.95},
        {"title": "Luật Phá sản 2014", "score": 0.80},
    ],
    "dan_su": [
        {"title": "Bộ luật Dân sự 2015 (Luật số 91/2015/QH13)", "score": 0.95},
        {"title": "Bộ luật Tố tụng Dân sự 2015", "score": 0.85},
    ],
    "hinh_su": [
        {"title": "Bộ luật Hình sự 2015 (sửa đổi 2017)", "score": 0.95},
        {"title": "Bộ luật Tố tụng Hình sự 2015", "score": 0.90},
    ],
    "hanh_chinh": [
        {"title": "Luật Khiếu nại 2011", "score": 0.95},
        {"title": "Luật Tố cáo 2018", "score": 0.90},
        {"title": "Luật Tố tụng Hành chính 2015", "score": 0.85},
    ],
    "gia_dinh": [
        {"title": "Luật Hôn nhân và Gia đình 2014", "score": 0.95},
        {"title": "Bộ luật Tố tụng Dân sự 2015 — Phần về hôn nhân gia đình", "score": 0.80},
    ],
}
