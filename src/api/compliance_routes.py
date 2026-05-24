from __future__ import annotations

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.api.deps import require_user
from src.services.compliance_service import ComplianceService

compliance_router = APIRouter(prefix="/compliance", tags=["compliance"])

_compliance_service = ComplianceService()


# ── Pydantic models ───────────────────────────────────────────────────────────


class ComplianceRequest(BaseModel):
    business_type: str = "general"
    transaction_type: str = "general"
    facts: List[str] = []
    situation: str = ""


class ComplianceItemOut(BaseModel):
    id: str
    category: str
    requirement: str
    law_basis: str
    priority: str
    status: str
    deadline_note: str
    missing: bool


class ComplianceResponse(BaseModel):
    request_id: str
    feature: str = "compliance_radar"
    business_type: str
    business_type_label: str
    transaction_type: str
    transaction_type_label: str
    items: List[ComplianceItemOut]
    missing_count: int
    critical_count: int
    compliance_score: float
    alerts: List[str]
    summary: str


# ── Endpoint ──────────────────────────────────────────────────────────────────


@compliance_router.post("/checklist", response_model=ComplianceResponse)
def get_compliance_checklist(
    body: ComplianceRequest,
    user_id: str = Depends(require_user),
) -> ComplianceResponse:
    """
    Sinh danh sách tuân thủ pháp lý theo loại hình doanh nghiệp và giao dịch.
    Tự động xác định các mục còn thiếu dựa trên sự kiện người dùng cung cấp.
    Trả về điểm tuân thủ, cảnh báo và danh sách ưu tiên.
    """
    result = _compliance_service.generate(
        business_type=body.business_type,
        transaction_type=body.transaction_type,
        facts=body.facts,
        situation=body.situation,
    )

    return ComplianceResponse(
        request_id="cmp_" + str(uuid.uuid4())[:8],
        business_type=result.business_type,
        business_type_label=result.business_type_label,
        transaction_type=result.transaction_type,
        transaction_type_label=result.transaction_type_label,
        items=[
            ComplianceItemOut(
                id=it.id,
                category=it.category,
                requirement=it.requirement,
                law_basis=it.law_basis,
                priority=it.priority,
                status=it.status,
                deadline_note=it.deadline_note,
                missing=it.missing,
            )
            for it in result.items
        ],
        missing_count=result.missing_count,
        critical_count=result.critical_count,
        compliance_score=result.compliance_score,
        alerts=result.alerts,
        summary=result.summary,
    )
