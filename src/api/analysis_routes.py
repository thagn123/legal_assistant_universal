from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import require_user
from src.services.evidence_gap_detector import EvidenceGapDetector, EvidenceItem
from src.services.timeline_tracker import TimelineTracker, DeadlineItem

analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])

_gap_detector = EvidenceGapDetector()
_timeline_tracker = TimelineTracker()


# ── Pydantic models ──────────────────────────────────────────────────────────


class EvidenceGapRequest(BaseModel):
    situation: str = ""
    domain: str = "general"
    facts: List[str] = []
    session_id: str = ""


class EvidenceItemOut(BaseModel):
    item: str
    priority: str
    category: str


class EvidenceGapResponse(BaseModel):
    request_id: str
    feature: str = "evidence_gap"
    domain: str
    missing_evidence: List[EvidenceItemOut]
    strong_evidence: List[str]
    weak_evidence: List[str]
    coverage_score: float
    priority_items: List[EvidenceItemOut]
    advice: str
    summary: str
    confidence: float
    warnings: List[str]


class TimelineRequest(BaseModel):
    situation: str
    domain: str = "general"
    facts: List[str] = []


class DeadlineItemOut(BaseModel):
    label: str
    days: int
    unit: str
    note: str


class TimelineResponse(BaseModel):
    request_id: str
    feature: str = "timeline"
    stage: str
    stage_label: str
    stage_confidence: float
    progress_percent: int
    typical_deadlines: List[DeadlineItemOut]
    alerts: List[str]
    next_stage: str
    next_stage_label: str
    summary: str
    warnings: List[str]


def _item_out(item: EvidenceItem) -> EvidenceItemOut:
    return EvidenceItemOut(item=item.item, priority=item.priority, category=item.category)


def _deadline_out(d: DeadlineItem) -> DeadlineItemOut:
    return DeadlineItemOut(label=d.label, days=d.days, unit=d.unit, note=d.note)


# ── Endpoints ────────────────────────────────────────────────────────────────


@analysis_router.post("/evidence-gap", response_model=EvidenceGapResponse)
def detect_evidence_gap(
    body: EvidenceGapRequest,
    user_id: str = Depends(require_user),
) -> EvidenceGapResponse:
    """
    Phân tích khoảng trống chứng cứ: so sánh chứng cứ hiện có với
    danh sách cần thiết theo lĩnh vực pháp lý, trả về danh sách còn thiếu
    và mức độ ưu tiên.
    """
    result = _gap_detector.detect_gaps(
        domain=body.domain,
        facts=body.facts,
        situation=body.situation,
    )

    missing_count = len(result.missing_evidence)
    priority_count = len(result.priority_items)

    if result.coverage_score >= 0.8:
        summary = f"Chứng cứ khá đầy đủ ({round(result.coverage_score * 100)}%). Còn thiếu {missing_count} mục nhỏ."
    elif result.coverage_score >= 0.5:
        summary = f"Chứng cứ ở mức trung bình ({round(result.coverage_score * 100)}%). Cần bổ sung {priority_count} mục ưu tiên cao."
    else:
        summary = f"Chứng cứ còn thiếu nhiều ({round(result.coverage_score * 100)}%). Cần bổ sung gấp {priority_count} mục quan trọng."

    warnings = []
    if priority_count >= 3:
        warnings.append("Thiếu nhiều chứng cứ quan trọng — khả năng thắng kiện bị ảnh hưởng đáng kể.")

    return EvidenceGapResponse(
        request_id="gap_" + str(uuid.uuid4())[:8],
        domain=result.domain,
        missing_evidence=[_item_out(m) for m in result.missing_evidence],
        strong_evidence=result.strong_evidence,
        weak_evidence=result.weak_evidence,
        coverage_score=result.coverage_score,
        priority_items=[_item_out(p) for p in result.priority_items],
        advice=result.advice,
        summary=summary,
        confidence=result.coverage_score,
        warnings=warnings,
    )


@analysis_router.post("/timeline", response_model=TimelineResponse)
def track_timeline(
    body: TimelineRequest,
    user_id: str = Depends(require_user),
) -> TimelineResponse:
    """
    Xác định giai đoạn hiện tại của vụ việc pháp lý, thời hạn điển hình
    và cảnh báo quan trọng cần lưu ý.
    """
    result = _timeline_tracker.track(
        situation=body.situation,
        domain=body.domain,
        facts=body.facts,
    )

    summary = (
        f"Vụ việc đang ở giai đoạn: {result.stage_label}. "
        f"Tiến độ hành trình pháp lý: {result.progress_percent}%. "
        f"Bước tiếp theo: {result.next_stage_label}."
    )

    warnings = []
    if result.stage in ("pre_litigation", "in_litigation") and result.typical_deadlines:
        d = result.typical_deadlines[0]
        warnings.append(f"Chú ý thời hạn: {d.label} — {d.days} {d.unit}.")

    return TimelineResponse(
        request_id="tl_" + str(uuid.uuid4())[:8],
        stage=result.stage,
        stage_label=result.stage_label,
        stage_confidence=result.stage_confidence,
        progress_percent=result.progress_percent,
        typical_deadlines=[_deadline_out(d) for d in result.typical_deadlines],
        alerts=result.alerts,
        next_stage=result.next_stage,
        next_stage_label=result.next_stage_label,
        summary=summary,
        warnings=warnings,
    )
