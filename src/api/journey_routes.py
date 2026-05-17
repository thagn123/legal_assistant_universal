from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import require_user
from src.services.legal_journey_service import JourneyMilestone, LegalJourneyService

journey_router = APIRouter(prefix="/journey", tags=["journey"])

_journey_service = LegalJourneyService()


# ── Pydantic models ──────────────────────────────────────────────────────────


class JourneyRequest(BaseModel):
    situation: str
    session_id: str = ""
    facts: List[str] = []
    domain: Optional[str] = None


class MilestoneOut(BaseModel):
    key: str
    title: str
    status: str
    summary: str
    detail: str = ""
    action_url: str = ""


class LawRefOut(BaseModel):
    title: str
    score: float


class JourneyResponse(BaseModel):
    request_id: str
    feature: str = "legal_journey"
    situation: str
    domain: str
    current_stage: str
    stage_label: str
    progress_percent: int
    stage_confidence: float
    milestones: List[MilestoneOut]
    evidence_coverage: float
    evidence_missing_count: int
    evidence_priority_count: int
    risk_level: str
    risk_summary: str
    next_steps: List[str]
    alerts: List[str]
    law_references: List[LawRefOut]
    summary: str
    confidence: float
    warnings: List[str]


# ── Endpoint ─────────────────────────────────────────────────────────────────


@journey_router.post("/build", response_model=JourneyResponse)
def build_journey(
    body: JourneyRequest,
    user_id: str = Depends(require_user),
) -> JourneyResponse:
    """
    Xây dựng hành trình pháp lý toàn diện từ mô tả tình huống:
    xác định giai đoạn, phân tích chứng cứ, đánh giá rủi ro và
    đề xuất bước tiếp theo.
    """
    result = _journey_service.build_journey(
        situation=body.situation,
        facts=body.facts,
        domain=body.domain,
    )

    summary = (
        f"Vụ việc {result.domain} đang ở giai đoạn '{result.stage_label}' "
        f"({result.progress_percent}% hành trình). "
        f"Mức rủi ro: {result.risk_level.upper()}. "
        f"Chứng cứ đạt {round(result.evidence_coverage * 100)}%."
    )

    warnings = []
    if result.risk_level == "high":
        warnings.append("Mức độ rủi ro cao — nên tư vấn luật sư trước khi hành động tiếp theo.")
    if result.evidence_priority_count >= 3:
        warnings.append(f"Còn thiếu {result.evidence_priority_count} loại chứng cứ quan trọng cần bổ sung gấp.")

    return JourneyResponse(
        request_id="jrn_" + str(uuid.uuid4())[:8],
        situation=result.situation,
        domain=result.domain,
        current_stage=result.current_stage,
        stage_label=result.stage_label,
        progress_percent=result.progress_percent,
        stage_confidence=result.stage_confidence,
        milestones=[
            MilestoneOut(
                key=m.key,
                title=m.title,
                status=m.status,
                summary=m.summary,
                detail=m.detail,
                action_url=m.action_url,
            )
            for m in result.milestones
        ],
        evidence_coverage=result.evidence_coverage,
        evidence_missing_count=result.evidence_missing_count,
        evidence_priority_count=result.evidence_priority_count,
        risk_level=result.risk_level,
        risk_summary=result.risk_summary,
        next_steps=result.next_steps,
        alerts=result.alerts,
        law_references=[LawRefOut(**ref) for ref in result.law_references],
        summary=summary,
        confidence=result.stage_confidence,
        warnings=warnings,
    )
