from __future__ import annotations

import uuid
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import require_user
from src.evidence.evidence_schemas import category_label
from src.services.evidence_gap_detector import EvidenceGapDetector, EvidenceItem
from src.services.situation_classifier import SituationClassifier
from src.services.timeline_tracker import TimelineTracker, DeadlineItem
from src.services.risk_analysis_service import RiskAnalysisService

analysis_router = APIRouter(prefix="/analysis", tags=["analysis"])

_gap_detector = EvidenceGapDetector()
_timeline_tracker = TimelineTracker()
_classifier = SituationClassifier()
_risk_service = RiskAnalysisService()


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
    evidence_id: str = ""
    title: str = ""
    status: str = ""
    matched_text: str = ""
    matched_alias: str = ""
    confidence: float = 0.0
    reason: str = ""
    category_label: str = ""


class EvidenceGapResponse(BaseModel):
    request_id: str
    feature: str = "evidence_gap"
    domain: str
    present_evidence: List[EvidenceItemOut] = []
    missing_evidence: List[EvidenceItemOut]
    uncertain_evidence: List[EvidenceItemOut] = []
    contradictions: List[EvidenceItemOut] = []
    strong_evidence: List[str]
    weak_evidence: List[str]
    coverage_score: float
    priority_items: List[EvidenceItemOut]
    advice: str
    summary: str
    confidence: float
    warnings: List[str]
    recommendations: List[str] = []
    debug: Dict[str, Any] = {}


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


# ── Classify models ──────────────────────────────────────────────────────────


class ClassifyRequest(BaseModel):
    situation: str
    facts: List[str] = []
    domain_hint: Optional[str] = None


class EntityOut(BaseModel):
    laws: List[str] = []
    parties: List[str] = []
    amounts: List[str] = []
    dates: List[str] = []
    locations: List[str] = []


class LawRefOut(BaseModel):
    title: str
    score: float


class ClassifyResponse(BaseModel):
    request_id: str
    feature: str = "situation_classifier"
    domain: str
    domain_confidence: float
    dispute_type: str
    stage: str
    stage_label: str
    stage_confidence: float
    intent: str
    intent_label: str
    entities: EntityOut
    extracted_facts: List[str]
    risk_level: str
    confidence: float
    law_references: List[LawRefOut]
    summary: str


# ── Timeline / evidence helpers ───────────────────────────────────────────────


def _item_out(item: EvidenceItem) -> EvidenceItemOut:
    return EvidenceItemOut(
        item=item.item,
        title=item.item,
        priority=item.priority,
        category=item.category,
        evidence_id=item.evidence_id,
        status=item.status,
        matched_text=item.matched_text,
        matched_alias=item.matched_alias,
        confidence=item.confidence,
        reason=item.reason,
        category_label=category_label(item.category),
    )


def _deadline_out(d: DeadlineItem) -> DeadlineItemOut:
    return DeadlineItemOut(label=d.label, days=d.days, unit=d.unit, note=d.note)


# ── Endpoints ────────────────────────────────────────────────────────────────


@analysis_router.post("/classify", response_model=ClassifyResponse)
def classify_situation(
    body: ClassifyRequest,
    user_id: str = Depends(require_user),
) -> ClassifyResponse:
    """
    Phân loại tình huống pháp lý: xác định lĩnh vực, loại tranh chấp,
    giai đoạn, ý định người dùng và trích xuất sự kiện chính.
    Dùng làm bước đầu tiên trước khi gọi /analysis/evidence-gap hoặc /journey/build.
    """
    result = _classifier.classify(
        situation=body.situation,
        facts=body.facts,
        domain_hint=body.domain_hint,
    )

    ent = result.entities
    domain_labels = {
        "dat_dai": "Đất đai", "hop_dong": "Hợp đồng", "lao_dong": "Lao động",
        "doanh_nghiep": "Doanh nghiệp", "dan_su": "Dân sự", "hinh_su": "Hình sự",
        "hanh_chinh": "Hành chính", "gia_dinh": "Gia đình & Hôn nhân",
        "general": "Chưa xác định",
    }
    risk_labels = {"low": "thấp", "medium": "trung bình", "high": "cao"}

    summary = (
        f"Tình huống thuộc lĩnh vực {domain_labels.get(result.domain, result.domain)} "
        f"(độ tin cậy {round(result.domain_confidence * 100)}%). "
        f"Giai đoạn: {result.stage_label}. "
        f"Mức rủi ro: {risk_labels.get(result.risk_level, result.risk_level).upper()}."
    )

    return ClassifyResponse(
        request_id="cls_" + str(uuid.uuid4())[:8],
        domain=result.domain,
        domain_confidence=result.domain_confidence,
        dispute_type=result.dispute_type,
        stage=result.stage,
        stage_label=result.stage_label,
        stage_confidence=result.stage_confidence,
        intent=result.intent,
        intent_label=result.intent_label,
        entities=EntityOut(
            laws=ent.get("laws", []),
            parties=ent.get("parties", []),
            amounts=ent.get("amounts", []),
            dates=ent.get("dates", []),
            locations=ent.get("locations", []),
        ),
        extracted_facts=result.extracted_facts,
        risk_level=result.risk_level,
        confidence=result.confidence,
        law_references=[LawRefOut(**r) for r in result.law_references],
        summary=summary,
    )


@analysis_router.post("/evidence-gap", response_model=EvidenceGapResponse)
def detect_evidence_gap(
    body: EvidenceGapRequest,
    debug: bool = False,
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

    priority_count = len(result.priority_items)

    warnings = []
    if result.contradictions:
        warnings.append("Có mâu thuẫn về tình trạng chứng cứ — cần xác minh trước khi kết luận thiếu.")
    if priority_count >= 3:
        warnings.append("Thiếu nhiều chứng cứ ưu tiên cao — khả năng bảo vệ yêu cầu có thể bị ảnh hưởng.")

    return EvidenceGapResponse(
        request_id="gap_" + str(uuid.uuid4())[:8],
        domain=result.domain,
        present_evidence=[_item_out(p) for p in result.present_evidence],
        missing_evidence=[_item_out(m) for m in result.missing_evidence],
        uncertain_evidence=[_item_out(u) for u in result.uncertain_evidence],
        contradictions=[_item_out(c) for c in result.contradictions],
        strong_evidence=result.strong_evidence,
        weak_evidence=result.weak_evidence,
        coverage_score=result.coverage_score,
        priority_items=[_item_out(p) for p in result.priority_items],
        advice=result.advice,
        summary=result.summary,
        confidence=result.coverage_score,
        warnings=warnings,
        recommendations=result.recommendations,
        debug=result.debug if debug else {},
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


# ── Risk Analysis ─────────────────────────────────────────────────────────────


class RiskRequest(BaseModel):
    situation: str
    facts: List[str] = []
    domain_hint: Optional[str] = None


class RiskResponse(BaseModel):
    request_id: str
    feature: str = "risk_analysis"
    domain: str
    risk_score: float
    risk_level: str
    stage: str
    stage_label: str
    strengths: List[str]
    weaknesses: List[str]
    missing_points: List[str]
    warnings: List[str]
    recommended_actions: List[str]
    evidence_coverage: float
    confidence: float
    summary: str


@analysis_router.post("/risk", response_model=RiskResponse)
def analyze_risk(
    body: RiskRequest,
    user_id: str = Depends(require_user),
) -> RiskResponse:
    """
    Đánh giá rủi ro pháp lý toàn diện: kết hợp phân loại tình huống và
    phân tích khoảng trống chứng cứ để sinh điểm rủi ro, điểm mạnh/yếu,
    và kế hoạch hành động ưu tiên.
    """
    result = _risk_service.analyze(
        situation=body.situation,
        facts=body.facts,
        domain_hint=body.domain_hint,
    )
    return RiskResponse(
        request_id="risk_" + str(uuid.uuid4())[:8],
        domain=result.domain,
        risk_score=result.risk_score,
        risk_level=result.risk_level,
        stage=result.stage,
        stage_label=result.stage_label,
        strengths=result.strengths,
        weaknesses=result.weaknesses,
        missing_points=result.missing_points,
        warnings=result.warnings,
        recommended_actions=result.recommended_actions,
        evidence_coverage=result.evidence_coverage,
        confidence=result.confidence,
        summary=result.summary,
    )
